import os
import json
import time
import re
import codecs
import arrow
from contextlib import contextmanager
from distutils.version import LooseVersion

import peewee
from six.moves.urllib_parse import parse_qsl
from kodi_six import xbmc, xbmcgui, xbmcaddon

from slyguy import database, gui, settings, plugin, inputstream
from slyguy.exceptions import Error
from slyguy.util import hash_6, get_addon, kodi_rpc, run_plugin
from slyguy.constants import KODI_VERSION, IA_ADDON_ID
from slyguy.log import log

from .constants import *
from .language import _

ATTRIBUTELISTPATTERN = re.compile(r'''([\w\-]+)=([^,"' ]+|"[^"]*"|'[^']*')''')

def strip_quotes(string):
    quotes = ('"', "'")
    if string.startswith(quotes) and string.endswith(quotes):
        string = string[1:-1]
    return string

def parse_attribs(line):
    attribs = {}
    match = None
    for match in ATTRIBUTELISTPATTERN.finditer(line):
        attribs[match.group(1).lower().strip()] = strip_quotes(match.group(2).strip())
    if match:
        # return the remainder of line after the last match
        line = line[match.end():]
    return attribs, line

@plugin.route()
def play_channel(slug, **kwargs):
    channel = Channel.get_by_id(slug)
    split = channel.url.split('|')

    if settings.getBool('iptv_merge_proxy', True):
        headers = {
            'seekable': '0',
            'referer': '%20',
            'user-agent': DEFAULT_USERAGENT,
        }
    else:
        headers = {}

    def get_header_dict(header_str):
        headers = {}
        _headers = dict(parse_qsl(u'{}'.format(header_str), keep_blank_values=True))
        for key in _headers:
            if _headers[key].startswith(' '):
                _headers[key] = u'%20{}'.format(_headers[key][1:])

            headers[key.lower()] = _headers[key]
        return headers

    if len(split) > 1:
        headers.update(get_header_dict(split[1]))

    manifest_type = channel.properties.pop('inputstream.adaptive.manifest_type', '')
    license_type = channel.properties.pop('inputstream.adaptive.license_type', '')
    license_key = channel.properties.pop('inputstream.adaptive.license_key', '')
    channel.properties.pop('inputstream', None)
    channel.properties.pop('inputstreamaddon', None)

    item = plugin.Item(
        label = channel.name,
        art = {'thumb': channel.logo},
        path = split[0],
        properties = channel.properties,
        headers = headers,
        use_proxy = settings.getBool('iptv_merge_proxy', True),
    )

    ## To do: support other IA Add-ons here (eg. ffmpeg.direct)
    if license_type.lower() == 'com.widevine.alpha':
        kwargs = {'license_key': license_key, 'manifest_type': manifest_type}
        if '|' in license_key:
            license_key, license_headers, challenge, response = license_key.split('|')
            kwargs.update({
                'license_key': license_key,
                'license_headers': get_header_dict(license_headers) or None,
                'challenge': challenge,
                'response': response,
            })
        item.inputstream = inputstream.Widevine(**kwargs)

    elif manifest_type.lower() == 'hls':
        item.inputstream = inputstream.HLS(force=True, live=True)

    elif manifest_type.lower() == 'ism':
        item.inputstream = inputstream.Playready()

    elif manifest_type.lower() == 'mpd':
        item.inputstream = inputstream.MPD()

    elif not channel.radio and '.m3u8' in split[0].lower() and settings.getBool('use_ia_hls_live'):
        item.inputstream = inputstream.HLS(live=True)

    return item

class Source(database.Model):
    ERROR = 0
    OK = 1

    TYPE_URL = 0
    TYPE_FILE = 1
    TYPE_ADDON = 2
    TYPE_CUSTOM = 3

    ARCHIVE_AUTO = 0
    ARCHIVE_GZIP = 1
    ARCHIVE_XZ = 2
    ARCHIVE_NONE = 3

    source_type = peewee.IntegerField()
    archive_type = peewee.IntegerField(default=ARCHIVE_AUTO)

    path = peewee.CharField()
    enabled = peewee.BooleanField(default=True)

    results = database.JSONField(default=list)

    TYPES = [TYPE_URL, TYPE_FILE, TYPE_ADDON, TYPE_CUSTOM]
    TYPE_LABELS = {
        TYPE_URL: _.URL,
        TYPE_FILE: _.FILE,
        TYPE_ADDON: _.ADDON,
        TYPE_CUSTOM: 'Custom',
    }

    def save(self, *args, **kwargs):
        try:
            super(Source, self).save(*args, **kwargs)
        except peewee.IntegrityError as e:
            raise Error(_.SOURCE_EXISTS)

    @property
    def plot(self):
        plot = u''

        if not self.enabled:
            plot = _.DISABLED_MERGE
        elif not self.results:
            plot = _.PENDING_MERGE
        else:
            for result in self.results:
                _time = arrow.get(result[0]).to('local').format('DD/MM/YY h:mm:ss a')
                _result = u'{}'.format(_(result[2], _color='lightgreen' if result[1] == self.OK else 'red'))
                plot += _(u'{}\n{}\n\n'.format(_time, _result))

        return plot

    @property
    def thumb(self):
        if self.source_type == self.TYPE_ADDON:
            try:
                return xbmcaddon.Addon(self.path).getAddonInfo('icon')
            except:
                return None
        else:
            return None

    @property
    def label(self):
        if self.source_type == self.TYPE_ADDON:
            try:
                label = xbmcaddon.Addon(self.path).getAddonInfo('name')
            except:
                label = '{} (Unknown)'.format(self.path)
        else:
            label = self.path

        return label

    @property
    def name(self):
        if not self.enabled:
            name = _(_.DISABLED, label=self.label, _color='gray')
        elif not self.results:
            name = _(self.label, _color='orange')
        elif self.results[0][1] == self.OK:
            name = _(self.label, _color='lightgreen')
        else:
            name = _(self.label, _color='red', _bold=True)

        return name

    @classmethod
    def user_create(cls):
        obj = cls()

        if obj.select_path(creating=True):
            return obj

        return None

    def select_path(self, creating=False):
        try:
            default = self.TYPES.index(self.source_type)
        except:
            default = -1

        index = gui.select(_.SELECT_SOURCE_TYPE, [self.TYPE_LABELS[x] for x in self.TYPES], preselect=default)
        if index < 0:
            return False

        orig_source_type = self.source_type
        self.source_type = self.TYPES[index]

        if self.source_type == self.TYPE_ADDON:
            addons  = self.get_addon_sources()
            if not addons:
                raise Error(_.NO_SOURCE_ADDONS)

            options = []
            default = -1
            addons.sort(key=lambda x: x[0].getAddonInfo('name').lower())

            for idx, row in enumerate(addons):
                options.append(plugin.Item(label=row[0].getAddonInfo('name'), art={'thumb': row[0].getAddonInfo('icon')}))
                if orig_source_type == self.TYPE_ADDON and row[0].getAddonInfo('id') == self.path:
                    default = idx

            index = gui.select(_.SELECT_SOURCE_ADDON, options, preselect=default, useDetails=True)
            if index < 0:
                return False

            addon, data = addons[index]
            self.path = addon.getAddonInfo('id')
        elif self.source_type == self.TYPE_URL:
            self.path = gui.input(_.ENTER_SOURCE_URL, default=self.path if orig_source_type == self.TYPE_URL else '').strip()
        elif self.source_type == self.TYPE_FILE:
            self.path = xbmcgui.Dialog().browseSingle(1, _.SELECT_SOURCE_FILE, '', '', defaultt=self.path if orig_source_type == self.TYPE_FILE else '')
        elif self.source_type == self.TYPE_CUSTOM:
            self.path = gui.input('Custom Name', default=self.path if orig_source_type == self.TYPE_CUSTOM else '').strip()

        if not self.path:
            return False

        self.save()

        if self.source_type == self.TYPE_ADDON:
            if creating:
                if self.__class__ == Playlist and METHOD_EPG in data:
                    epg = EPG(source_type=EPG.TYPE_ADDON, path=self.path)
                    try: epg.save()
                    except: pass

                elif self.__class__ == EPG and METHOD_PLAYLIST in data:
                    playlist = Playlist(source_type=Playlist.TYPE_ADDON, path=self.path)
                    try: playlist.save()
                    except: pass

            for key in data.get('settings', {}):
                value = data['settings'][key].replace('$ID', self.path)
                log.debug('Set setting {}={} for addon {}'.format(key, value, self.path))
                addon.setSetting(key, value)

            if 'configure' in data:
                path = data['configure'].replace('$ID', self.path)
                run_plugin(path, wait=True)

        return True

    def select_archive_type(self):
        values = [self.ARCHIVE_AUTO, self.ARCHIVE_GZIP, self.ARCHIVE_XZ, self.ARCHIVE_NONE]
        labels = [_.ARCHIVE_AUTO, _.GZIP, _.XZ, _.ARCHIVE_NONE]

        try:
            default = values.index(self.archive_type)
        except:
            default = 0

        index = gui.select(_.SELECT_ARCHIVE_TYPE, labels, preselect=default)
        if index < 0:
            return False

        self.archive_type = values[index]
        return True

    @property
    def archive_type_name(self):
        if self.archive_type == self.ARCHIVE_AUTO:
            return _.ARCHIVE_AUTO
        elif self.archive_type == self.ARCHIVE_GZIP:
            return _.GZIP
        elif self.archive_type == self.ARCHIVE_XZ:
            return _.XZ
        else:
            return _.ARCHIVE_NONE

    def toggle_enabled(self):
        self.enabled = not self.enabled
        return True

    @classmethod
    def has_sources(cls):
        return cls.select().where(cls.enabled == True).exists()

    @classmethod
    def wizard(cls):
        source = cls()
        if not source.select_path():
            return

        return source

    @classmethod
    def get_addon_sources(cls):
        data      = kodi_rpc('Addons.GetAddons', {'installed': True, 'enabled': True, 'type': 'xbmc.python.pluginsource'}, raise_on_error=True)
        installed = [x.path for x in cls.select(cls.path).where(cls.source_type==cls.TYPE_ADDON)]

        addons = []
        for row in data['addons']:
            if row['addonid'] in installed:
                continue

            addon, data = merge_info(row['addonid'])
            if not addon or not data:
                continue

            if cls == Playlist and METHOD_PLAYLIST not in data:
                continue
            elif cls == EPG and METHOD_EPG not in data:
                continue

            addons.append([addon, data])

        return addons

    class Meta:
        indexes = (
            (('path',), True),
        )

def merge_info(addon_id, merging=False):
    addon = get_addon(addon_id, required=True, install=False)
    addon_path = xbmc.translatePath(addon.getAddonInfo('path'))
    merge_path = os.path.join(addon_path, MERGE_SETTING_FILE)

    data = {}
    if os.path.exists(merge_path):
        try:
            with codecs.open(merge_path, 'r', encoding='utf8') as f:
                data = json.load(f)
                data['type'] = TYPE_IPTV_MERGE
        except Exception as e:
            log.exception(e)
            log.debug('failed to parse merge file: {}'.format(merge_path))
            return addon, {}

    elif addon.getSetting('iptv.enabled'):
        data = {
            'type': TYPE_IPTV_MANAGER,
            'playlist': addon.getSetting('iptv.channels_uri'),
            'epg': addon.getSetting('iptv.epg_uri'),
        }

    elif addon_id.lower() in INTEGRATIONS:
        data = INTEGRATIONS[addon_id.lower()]
        data['type'] = TYPE_INTEGRATION

    elif merging:
        raise Error('No integration found for this source')

    min_version = data.get('min_version')
    max_version = data.get('max_version')
    current_version = LooseVersion(addon.getAddonInfo('version'))

    if min_version and current_version < LooseVersion(min_version):
        if merging:
            raise Error('Min version {} required'.format(min_version))
        else:
            data = {}

    if max_version and current_version > LooseVersion(max_version):
        if merging:
            raise Error('Max version {} exceeded'.format(max_version))
        else:
            data = {}

    return addon, data

class EPG(Source):
    TYPES = [Source.TYPE_URL, Source.TYPE_FILE, Source.TYPE_ADDON]

    start_index = peewee.IntegerField(default=0)
    end_index = peewee.IntegerField(default=0)

class Playlist(Source):
    skip_playlist_chno = peewee.BooleanField(default=False)
    use_start_chno = peewee.BooleanField(default=False)
    start_chno = peewee.IntegerField(default=1)
    default_visible = peewee.BooleanField(default=True)
    skip_playlist_groups = peewee.BooleanField(default=False)
    group_name = peewee.CharField(null=True)
    order = peewee.IntegerField()
    #ignore_playlist_epg = peewee.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.order:
            self.order = Playlist.select(peewee.fn.MAX(Playlist.order)+1).scalar() or 1

        if not self.id and self.source_type == Source.TYPE_ADDON and not self.group_name:
            try: self.group_name = xbmcaddon.Addon(self.path).getAddonInfo('name')
            except: pass

        super(Playlist, self).save(*args, **kwargs)

    def get_epg(self):
        try:
            return self.epgs.get()
        except EPG.DoesNotExist:
            return None

    def select_start_chno(self):
        start_chno = gui.numeric(_.ENTER_START_CHNO, default=self.start_chno)
        if start_chno is None:
            return False

        self.start_chno = start_chno
        return True

    def select_group_name(self):
        self.group_name = gui.input(_.ENTER_GROUP_NAME, default=self.group_name) or None
        return True

    def toggle_use_start_chno(self):
        self.use_start_chno = not self.use_start_chno
        return True

    def toggle_skip_playlist_chno(self):
        self.skip_playlist_chno = not self.skip_playlist_chno
        return True

    def toggle_default_visible(self):
        self.default_visible = not self.default_visible
        return True

    def toggle_skip_playlist_groups(self):
        self.skip_playlist_groups = not self.skip_playlist_groups
        return True

    @classmethod
    def after_merge(cls):
        Override.clean()

class Channel(database.Model):
    slug = peewee.CharField(primary_key=True)
    playlist = peewee.ForeignKeyField(Playlist, backref="channels", on_delete='cascade')
    url = peewee.CharField()
    order = peewee.IntegerField()
    chno = peewee.IntegerField(null=True)
    name = peewee.CharField(null=True)
    custom = peewee.BooleanField(default=False)

    groups = database.JSONField(default=list)
    radio = peewee.BooleanField(default=False)
    epg_id = peewee.CharField(null=True)
    logo = peewee.CharField(null=True)
    attribs = database.JSONField(default=dict)
    properties = database.JSONField(default=dict)
    visible = peewee.IntegerField(default=True)
    is_live = peewee.BooleanField(default=True)

    modified = peewee.BooleanField(default=False)

    @property
    def label(self):
        label = ''
        if self.chno is not None:
            label = '{} - '.format(self.chno)

        label += self.name or _.NO_NAME

        return label

    @property
    def plot(self):
        plot = u'{}\n{}'.format(_.URL, self.url)

        if self.groups:
            plot += u'\n\n{}\n{}'.format('Groups', ';'.join(self.groups))

        if self.playlist_id:
            plot += u'\n\n{}\n{}'.format(_.PLAYLIST, self.playlist.path)

        if self.epg_id:
            plot += u'\n\n{}\n{}'.format('EPG ID', self.epg_id)

        return plot

    def get_play_path(self, force_proxy=False):
        if force_proxy or (not self.radio and self.url.lower().startswith('http') and settings.getBool('iptv_merge_proxy', True)):
            return plugin.url_for(play_channel, slug=self.slug)
        else:
            return self.url

    def get_lines(self):
        lines = u'#EXTINF:-1'

        attribs = self.attribs.copy()
        attribs.update({
            'tvg-id': self.epg_id,
            'group-title': ';'.join([x for x in self.groups if x.strip()]) if self.groups else None,
            'tvg-chno': self.chno,
            'tvg-logo': self.logo,
            'radio': 'true' if self.radio else None,
        })

        for key in sorted(attribs.keys()):
            value = attribs[key]
            if value is not None:
                lines += u' {}="{}"'.format(key, value)

        lines += u' , {}\n'.format(self.name if self.name else '')

        if not self.is_live:
            lines += u'#EXT-X-PLAYLIST-TYPE:VOD\n'

        if self.radio or not self.url.lower().startswith('http') or not settings.getBool('iptv_merge_proxy', True):
            for key in self.properties:
                lines += u'#KODIPROP:{}={}\n'.format(key, self.properties[key])

        lines += u'{}'.format(self.get_play_path())

        return lines

    @classmethod
    def epg_ids(cls):
        query = cls.select(cls.epg_id).where(cls.visible == True).distinct()
        with cls.merged():
            return [x[0] for x in query.tuples()]

    @classmethod
    def playlist_list(cls, radio=None):
        query = cls.select(cls).join(Playlist).where(cls.visible == True).order_by(cls.chno.asc(nulls='LAST'), cls.playlist.order, cls.order)

        if radio is not None:
            query = query.where(cls.radio == radio)

        with cls.merged():
            for channel in query:
                yield(channel)

    @classmethod
    def channel_list(cls, radio=None, playlist_id=0, page=1, page_size=0, search=None):
        query = cls.select(cls).join(Playlist).order_by(cls.chno.asc(nulls='LAST'), cls.playlist.order, cls.order)

        if radio is not None:
            query = query.where(cls.radio == radio)

        if playlist_id is None:
            query = query.where(cls.playlist_id.is_null())
        elif playlist_id:
            query = query.where(cls.playlist_id == playlist_id)

        if search:
            query = query.where(cls.name.concat(' ').concat(cls.url) ** '%{}%'.format(search))

        if page_size > 0:
            query = query.paginate(page, page_size)

        with cls.merged():
            for channel in query.prefetch(Playlist):
                yield(channel)

    @classmethod
    @contextmanager
    def merged(cls):
        channel_updates = set()

        for override in Override.select(Override, Channel).join(Channel, on=(Channel.slug == Override.slug), attr='channel'):
            channel = override.channel

            for key in override.fields:
                if hasattr(channel, key):
                    setattr(channel, key, override.fields[key])
                else:
                    log.debug('Skipping unknown override key: {}'.format(key))

            channel.modified = True if not channel.custom else False
            channel.attribs.update(override.attribs)
            channel.properties.update(override.properties)
            channel_updates.add(channel)

        if not channel_updates:
            yield
            return

        with database.db.atomic() as transaction:
            try:
                Channel.bulk_update(channel_updates, fields=Channel._meta.fields)
                yield
                transaction.rollback()
            except Exception as e:
                transaction.rollback()
                raise

    @classmethod
    def from_url(cls, playlist, url):
        order = Channel.select(peewee.fn.MAX(Channel.order)+1).where(Channel.playlist == playlist).scalar() or 1

        return Channel(
            playlist = playlist,
            slug     = '{}.{}'.format(playlist.id, hash_6(time.time(), url.lower().strip())),
            url      = url,
            name     = url,
            order    = order,
            custom   = True,
        )

    def load_extinf(self, extinf):
        attribs, extinf = parse_attribs(extinf)
        chunks = extinf.split(',', 1)
        if len(chunks) == 2:
            name = chunks[1].strip()
            if name:
                self.name = name

        self.radio = attribs.pop('radio', 'false').lower() == 'true'

        try:
            self.chno = int(attribs.pop('tvg-chno'))
        except:
            self.chno = None

        groups = attribs.pop('group-title', '').strip()
        if groups:
            self.groups = groups.split(';')

        self.epg_id = attribs.pop('tvg-id', None) or attribs.get('tvg-name') or self.name
        self.logo = attribs.pop('tvg-logo', None)
        self.attribs = attribs

class Override(database.Model):
    playlist = peewee.ForeignKeyField(Playlist, backref="overrides", on_delete='cascade')
    slug = peewee.CharField(primary_key=True)
    fields = database.JSONField(default=dict)
    attribs = database.JSONField(default=dict)
    properties = database.JSONField(default=dict)
    headers = database.JSONField(default=dict)

    def edit_logo(self, channel):
        self.fields['logo'] = self.fields.get('logo', channel.logo)
        new_value = gui.input('Channel Logo', default=self.fields['logo'])

        if new_value == channel.logo:
            self.fields.pop('logo')
        elif new_value:
            self.fields['logo'] = new_value
        else:
            return False

        return True

    def edit_name(self, channel):
        self.fields['name'] = self.fields.get('name', channel.name)
        new_value = gui.input('Channel Name', default=self.fields['name'])

        if new_value == channel.name:
            self.fields.pop('name')
        elif new_value:
            self.fields['name'] = new_value
        else:
            return False

        return True

    def edit_chno(self, channel):
        self.fields['chno'] = self.fields.get('chno', channel.chno)
        new_chno = gui.numeric('Channel Number', default=self.fields['chno'] if self.fields['chno'] != None else '')

        try: new_chno = int(new_chno)
        except: new_chno = None

        if new_chno == channel.chno:
            self.fields.pop('chno')
        elif new_chno:
            self.fields['chno'] = new_chno
        else:
            return False

        return True

    def edit_groups(self, channel):
        self.fields['groups'] = self.fields.get('groups', channel.groups)
        new_groups = gui.input('Channel Groups', default=';'.join(self.fields['groups']) if self.fields['groups'] else '').split(';')

        if new_groups == channel.groups:
            self.fields.pop('groups')
        elif new_groups:
            self.fields['groups'] = new_groups
        else:
            return False

        return True

    def edit_epg_id(self, channel):
        self.fields['epg_id'] = self.fields.get('epg_id', channel.epg_id)
        new_id = gui.input('EPG ID', default=self.fields['epg_id'])

        if new_id == channel.epg_id:
            self.fields.pop('epg_id')
        elif new_id:
            self.fields['epg_id'] = new_id
        else:
            return False

        return True

    def toggle_visible(self, channel):
        self.fields['visible'] = not self.fields.get('visible', channel.visible)

        if self.fields['visible'] == channel.visible:
            self.fields.pop('visible', None)

        return True

    def save(self, *args, **kwargs):
        if not self.fields and not self.attribs and not self.properties:
            self.delete_instance()
        else:
            super(Override, self).save(*args, **kwargs)

    @classmethod
    def clean(cls):
        cls.delete().where((cls.fields=={}) & (cls.attribs=={}) & (cls.properties=={}) & (cls.headers=={})).execute()

database.tables.extend([Playlist, EPG, Channel, Override])
