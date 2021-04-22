import os
import shutil
import time
import json
import codecs
import xml.parsers.expat
from xml.sax.saxutils import escape

import peewee
from kodi_six import xbmc, xbmcvfs
from six.moves.urllib.parse import unquote

from slyguy import settings, database, gui, router
from slyguy.log import log
from slyguy.util import remove_file, hash_6, FileIO, gzip_extract, xz_extract
from slyguy.session import Session
from slyguy.constants import ADDON_PROFILE, CHUNK_SIZE
from slyguy.exceptions import Error

from .constants import *
from .models import Source, Playlist, EPG, Channel, merge_info, get_integrations
from .language import _

def copy_partial_data(file_path, _out, start_index, end_index):
    if start_index < 1 or end_index < start_index:
        return

    try:
        with FileIO(file_path, 'rb', CHUNK_SIZE) as _in:
            _seek_file(_in, start_index, truncate=False)

            while True:
                size = min(CHUNK_SIZE, end_index - _in.tell())
                chunk = _in.read(size)
                if not chunk:
                    break

                _out.write(chunk)

            return _in.tell() == end_index
    except:
        return

def _seek_file(f, index, truncate=True):
    cur_index = f.tell()
    if cur_index != index:
        log.debug('{} seeking from {} to {}'.format(f.name, cur_index, index))
        f.seek(index, os.SEEK_SET)
        if truncate:
            f.truncate()

class AddonError(Error):
    pass

class XMLParser(object):
    def __init__(self, out):
        self._out = out
        self.channel_count   = 0
        self.programme_count = 0

        self._parser = xml.parsers.expat.ParserCreate()
        self._parser.buffer_text = True
        self._parser.StartElementHandler = self._start_element
        self._parser.EndElementHandler = self._end_element

        self._reset_buffer = False
        self._start_index = None
        self._end_index = None

    def _start_element(self, name, attrs):
        if self._start_index == 'next':
            self._start_index = self._parser.CurrentByteIndex

        if name == 'tv' and self._start_index is None:
            self._start_index = 'next'

        if name == 'channel':
            self.channel_count += 1

        elif name == 'programme':
            self.programme_count += 1

    def _end_element(self, name):
        self._reset_buffer = True
        if name == 'tv':
            self._end_index = self._parser.CurrentByteIndex

    def parse(self, _in, epg):
        epg.start_index = self._out.tell()

        buffer = b''
        start_pos = 0
        while True:
            chunk = _in.read(CHUNK_SIZE)
            if not chunk:
                break

            buffer += chunk
            self._parser.Parse(chunk)

            if self._start_index in (None, 'next'):
                continue

            if self._start_index:
                buffer = buffer[self._start_index-start_pos:]
                self._start_index = False

            if self._end_index:
                buffer = buffer[:-(self._parser.CurrentByteIndex - self._end_index)]

            if self._reset_buffer:
                self._out.write(buffer)
                buffer = b''
                self._reset_buffer = False
                start_pos = self._parser.CurrentByteIndex

            if self._end_index:
                break

        self._out.flush()
        epg.end_index = self._out.tell()

class Merger(object):
    def __init__(self, output_path=None, forced=False):
        self.output_path = output_path or xbmc.translatePath(settings.get('output_dir', '').strip() or ADDON_PROFILE)
        if not os.path.exists(self.output_path):
            os.makedirs(self.output_path)

        self.forced = forced
        self.tmp_file = os.path.join(self.output_path, 'iptv_merge_tmp')
        self.integrations = get_integrations()

    def _call_addon_method(self, plugin_url):
        dirs, files = xbmcvfs.listdir(plugin_url)
        msg = unquote(files[0])
        if msg != 'ok':
            raise AddonError(msg)

    def _process_source(self, source, method_name, file_path):
        remove_file(file_path)

        path         = source.path.strip()
        source_type  = source.source_type
        archive_type = source.archive_type

        if source_type == Source.TYPE_ADDON:
            addon_id = path
            addon, data = merge_info(addon_id, self.integrations, merging=True)

            if method_name not in data:
                raise Error('{} could not be found for {}'.format(method_name, addon_id))

            template_tags = {
                '$ID': addon_id,
                '$FILE': file_path,
                '$IP': xbmc.getIPAddress(),
            }

            path = data[method_name]
            for tag in template_tags:
                path = path.replace(tag, template_tags[tag])

            path = path.strip()
            if path.lower().startswith('plugin'):
                self._call_addon_method(path)
                return

            if path.lower().startswith('http'):
                source_type = Source.TYPE_URL
            else:
                source_type = Source.TYPE_FILE

            archive_extensions = {
                '.gz': Source.ARCHIVE_GZIP,
                '.xz': Source.ARCHIVE_XZ,
            }

            name, ext = os.path.splitext(path.lower())
            archive_type = archive_extensions.get(ext, Source.ARCHIVE_NONE)

        if source_type == Source.TYPE_URL and path.lower().startswith('http'):
            log.debug('Downloading: {} > {}'.format(path, file_path))
            Session().chunked_dl(path, file_path)
        elif not xbmcvfs.exists(path):
            raise Error(_(_.LOCAL_PATH_MISSING, path=path))
        else:
            log.debug('Copying local file: {} > {}'.format(path, file_path))
            xbmcvfs.copy(path, file_path)

        if archive_type == Source.ARCHIVE_GZIP:
            gzip_extract(file_path)
        elif archive_type == Source.ARCHIVE_XZ:
            xz_extract(file_path)

    def _process_playlist(self, playlist, file_path):
        channel     = None
        to_create   = set()
        slugs       = set()
        added_count = 0

        Channel.delete().where(Channel.playlist == playlist).execute()

        if playlist.use_start_chno:
            chnos = {'tv': playlist.start_chno, 'radio': playlist.start_chno}

        free_iptv = False
        with codecs.open(file_path, 'r', encoding='utf8', errors='replace') as infile:
            for idx, line in enumerate(infile):
                line = line.strip()

                if 'free-iptv' in line.lower():
                    free_iptv = True

                if idx == 0 and '#EXTM3U' not in line:
                    raise Error('Invalid playlist - Does not start with #EXTM3U')

                if line.startswith('#EXTINF'):
                    channel = Channel.from_playlist(line)
                elif not channel:
                    continue

                if line.startswith('#EXTGRP'):
                    value = line.split(':',1)[1].strip()
                    if value:
                        channel.groups.extend(value.split(';'))

                elif line.startswith('#KODIPROP') or line.startswith('#EXTVLCOPT'):
                    value = line.split(':',1)[1].strip()
                    if value and '=' in value:
                        key, value = value.split('=', 1)
                        channel.properties[key] = value

                elif line.startswith('#EXT-X-PLAYLIST-TYPE'):
                    value = line.split(':',1)[1].strip()
                    if value and value.upper() == 'VOD':
                        channel.is_live = False

                elif not line.startswith('#'):
                    channel.url = line
                    if not channel.url:
                        channel = None
                        continue

                    channel.playlist = playlist

                    if playlist.skip_playlist_groups:
                        channel.groups = []

                    if playlist.group_name:
                        channel.groups.extend(playlist.group_name.split(';'))

                    if playlist.skip_playlist_chno:
                        channel.chno = None

                    if playlist.use_start_chno:
                        if channel.radio:
                            if channel.chno is None:
                                channel.chno = chnos['radio']

                            chnos['radio'] = channel.chno + 1
                        else:
                            if channel.chno is None:
                                channel.chno = chnos['tv']

                            chnos['tv'] = channel.chno + 1

                    if free_iptv:
                        channel.url = 'https://archive.org/download/Rick_Astley_Never_Gonna_Give_You_Up/Rick_Astley_Never_Gonna_Give_You_Up.mp4'
                        # channel.name = _.NO_FREE_IPTV
                        # channel.epg_id = None
                        # channel.logo = None

                    channel.groups = [x for x in channel.groups if x.strip()]
                    channel.visible = playlist.default_visible
                    channel.slug = slug = '{}.{}'.format(playlist.id, hash_6(channel.epg_id or channel.url.lower().strip()))
                    channel.order = added_count + 1

                    count = 1
                    while channel.slug in slugs:
                        channel.slug = '{}.{}'.format(slug, count)
                        count += 1

                    slugs.add(channel.slug)
                    to_create.add(channel)

                    if Channel.bulk_create_lazy(to_create):
                        to_create.clear()

                    channel = None
                    added_count += 1

        Channel.bulk_create_lazy(to_create, force=True)
        to_create.clear()
        slugs.clear()

        return added_count

    def playlists(self):
        start_time = time.time()
        playlist_path = os.path.join(self.output_path, PLAYLIST_FILE_NAME)
        database.connect()

        try:
            progress = gui.progressbg() if self.forced else None

            playlists = list(Playlist.select().where(Playlist.enabled == True).order_by(Playlist.order))
            Playlist.update({Playlist.results: []}).where(Playlist.enabled == False).execute()
            Channel.delete().where(Channel.custom == False, Channel.playlist.not_in(playlists)).execute()

            for count, playlist in enumerate(playlists):
                count += 1

                if progress: progress.update(int(count*(100/len(playlists))), 'Merging Playlist ({}/{})'.format(count, len(playlists)), _(playlist.label, _bold=True))

                playlist_start = time.time()

                error = None
                try:
                    log.debug('Processing: {}'.format(playlist.path))

                    if playlist.source_type != Playlist.TYPE_CUSTOM:
                        self._process_source(playlist, METHOD_PLAYLIST, self.tmp_file)

                        with database.db.atomic() as transaction:
                            try:
                                added = self._process_playlist(playlist, self.tmp_file)
                            except:
                                transaction.rollback()
                                raise
                    else:
                        added = len(playlist.channels)
                except AddonError as e:
                    error = e
                except Error as e:
                    error = e
                    log.exception(e)
                except Exception as e:
                    error = e
                    log.exception(e)
                else:
                    playlist.results.insert(0, [int(time.time()), Playlist.OK, '{} Channels ({:.2f}s)'.format(added, time.time() - playlist_start)])
                    error = None

                if error:
                    result = [int(time.time()), Playlist.ERROR, str(error)]
                    if playlist.results and playlist.results[0][1] == Playlist.ERROR:
                        playlist.results[0] = result
                    else:
                        playlist.results.insert(0, result)

                remove_file(self.tmp_file)

                playlist.results = playlist.results[:3]
                playlist.save()

            count = 0
            starting_ch_no = settings.getInt('start_ch_no', 1)

            with codecs.open(playlist_path, 'w', encoding='utf8') as outfile:
                outfile.write(u'#EXTM3U')

                group_order = settings.get('group_order')
                if group_order:
                    outfile.write(u'\n\n#EXTGRP:{}'.format(group_order))

                chno = starting_ch_no
                tv_groups = []
                for channel in Channel.playlist_list(radio=False):
                    if channel.chno is None:
                        channel.chno = chno
                    chno = channel.chno + 1

                    tv_groups.extend(channel.groups)

                    outfile.write(u'\n\n')
                    outfile.write(channel.get_lines())
                    count += 1

                chno = starting_ch_no
                for channel in Channel.playlist_list(radio=True):
                    if channel.chno is None:
                        channel.chno = chno
                    chno = channel.chno + 1

                    new_groups = []
                    for group in channel.groups:
                        count = 1
                        while group in tv_groups:
                            group = _(_.RADIO_GROUP, group=group)
                            if count > 1:
                                group = u'{} #{}'.format(group, count)
                            count += 1
                        new_groups.append(group)

                    channel.groups = new_groups

                    outfile.write(u'\n\n')
                    outfile.write(channel.get_lines())
                    count += 1

            log.debug('Wrote {} Channels'.format(count))
            Playlist.after_merge()
        finally:
            if progress: progress.close()
            database.close()

        log.debug('Playlist Merge Time: {0:.2f}'.format(time.time() - start_time))

        return playlist_path

    def epgs(self):
        start_time = time.time()
        epg_path   = os.path.join(self.output_path, EPG_FILE_NAME)
        epg_path_tmp = os.path.join(self.output_path, EPG_FILE_NAME+'_tmp')
        database.connect()

        try:
            progress = gui.progressbg() if self.forced else None

            epgs = list(EPG.select().where(EPG.enabled == True).order_by(EPG.id))
            EPG.update({EPG.start_index: 0, EPG.end_index: 0, EPG.results: []}).where(EPG.enabled == False).execute()

            with FileIO(epg_path_tmp, 'wb') as _out:
                _out.write(b'<?xml version="1.0" encoding="UTF-8"?><tv>')

                for count, epg in enumerate(epgs):
                    count += 1

                    if progress: progress.update(int(count*(100/len(epgs))), 'Merging EPG ({}/{})'.format(count, len(epgs)), _(epg.label, _bold=True))

                    file_index = _out.tell()

                    epg_start = time.time()
                    try:
                        log.debug('Processing: {}'.format(epg.path))
                        self._process_source(epg, METHOD_EPG, self.tmp_file)
                        with FileIO(self.tmp_file, 'rb') as _in:
                            parser = XMLParser(_out)
                            parser.parse(_in, epg)
                    except Exception as e:
                        log.exception(e)
                        result = [int(time.time()), EPG.ERROR, str(e)]
                    else:
                        result = [int(time.time()), EPG.OK, '{} Programmes ({:.2f}s)'.format(parser.programme_count, time.time() - epg_start)]
                        epg.results.insert(0, result)

                    if result[1] == EPG.ERROR:
                        _seek_file(_out, file_index)

                        if epg.start_index > 0:
                            if copy_partial_data(epg_path, _out, epg.start_index, epg.end_index):
                                log.debug('Last used XML data loaded successfully')
                                epg.start_index = file_index
                                epg.end_index = _out.tell()
                            else:
                                log.debug('Failed to load last XML data')
                                epg.start_index = 0
                                epg.end_index = 0
                                _seek_file(_out, file_index)

                        if epg.results and epg.results[0][1] == EPG.ERROR:
                            epg.results[0] = result
                        else:
                            epg.results.insert(0, result)

                    epg.results = epg.results[:3]
                    epg.save()
                    remove_file(self.tmp_file)

                _out.write(b'</tv>')

            remove_file(epg_path)
            shutil.move(epg_path_tmp, epg_path)
        finally:
            if progress: progress.close()

            remove_file(self.tmp_file)
            remove_file(epg_path_tmp)
            database.close()

        log.debug('EPG Merge Time: {0:.2f}'.format(time.time() - start_time))

        return epg_path