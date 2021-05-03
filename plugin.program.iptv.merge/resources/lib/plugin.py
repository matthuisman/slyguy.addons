import os
import json
import time
from difflib import SequenceMatcher

from kodi_six import xbmc, xbmcaddon, xbmcgui

from slyguy import plugin, settings, gui, userdata
from slyguy.util import set_kodi_setting, kodi_rpc, set_kodi_string, get_kodi_string, get_addon
from slyguy.constants import ADDON_PROFILE, KODI_VERSION, ADDON_ICON
from slyguy.exceptions import PluginError

from .language import _
from .models import Playlist, Source, EPG, Channel, Override, play_channel, merge_info
from .constants import *
from .merger import Merger, _read_only

@plugin.route('')
def home(**kwargs):
    folder = plugin.Folder(cacheToDisc=False)

    if not iptv_is_setup():
        folder.add_item(
            label = _(_.SETUP_IPTV_SIMPLE, _bold=True),
            path  = plugin.url_for(setup),
        )

    folder.add_item(
        label = _.PLAYLISTS,
        path  = plugin.url_for(playlists),
    )

    folder.add_item(
        label = _.EPGS,
        path  = plugin.url_for(epgs),
    )

    folder.add_item(
        label = _.MANAGE_TV,
        path  = plugin.url_for(manager, radio=0),
    )

    folder.add_item(
        label = _.MANAGE_RADIO,
        path  = plugin.url_for(manager, radio=1),
    )

    folder.add_item(
        label = _.RUN_MERGE,
        path  = plugin.url_for(merge),
    )

    if settings.getBool('bookmarks', True):
        folder.add_item(label=_.BOOKMARKS, path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False)

    return folder

@plugin.route()
def shift_playlist(playlist_id, shift, **kwargs):
    shift  = int(shift)
    playlist = Playlist.get_by_id(int(playlist_id))

    Playlist.update(order = Playlist.order - shift).where(Playlist.order == playlist.order + shift).execute()
    playlist.order += shift
    playlist.save()

    gui.refresh()

@plugin.route()
def playlists(**kwargs):
    folder = plugin.Folder(_.PLAYLISTS)

    playlists = Playlist.select().order_by(Playlist.order)

    for playlist in playlists:
        context = [
            ('Disable Playlist' if playlist.enabled else 'Enable Playlist', "RunPlugin({})".format(plugin.url_for(edit_playlist_value, playlist_id=playlist.id, method=Playlist.toggle_enabled.__name__))),
            (_.DELETE_PLAYLIST, "RunPlugin({})".format(plugin.url_for(delete_playlist, playlist_id=playlist.id))),
            (_.INSERT_PLAYLIST, "RunPlugin({})".format(plugin.url_for(new_playlist, position=playlist.order))),
        ]

        if playlist.source_type == Playlist.TYPE_ADDON:
            context.append((_.ADDON_SETTINGS, "Addon.OpenSettings({})".format(playlist.path)))

        if playlist.order > 1:
            context.append(('Move Up', 'RunPlugin({})'.format(plugin.url_for(shift_playlist, playlist_id=playlist.id, shift=-1))))

        if playlist.order < len(playlists)+1:
            context.append(('Move Down', 'RunPlugin({})'.format(plugin.url_for(shift_playlist, playlist_id=playlist.id, shift=1))))

        folder.add_item(
            label   = playlist.name,
            info    = {'plot': playlist.plot},
            art     = {'thumb': playlist.thumb},
            path    = plugin.url_for(edit_playlist, playlist_id=playlist.id),
            context = context,
        )

    folder.add_item(
        label = _(_.ADD_PLAYLIST, _bold=True),
        path  = plugin.url_for(new_playlist),
    )

    return folder

@plugin.route()
def epgs(**kwargs):
    folder = plugin.Folder(_.EPGS)

    for epg in EPG.select().order_by(EPG.id):
        context = [
            ('Disable EPG' if epg.enabled else 'Enable EPG', "RunPlugin({})".format(plugin.url_for(edit_epg_value, epg_id=epg.id, method=EPG.toggle_enabled.__name__))),
            (_.DELETE_EPG, "RunPlugin({})".format(plugin.url_for(delete_epg, epg_id=epg.id))),
        ]

        if epg.source_type == EPG.TYPE_ADDON:
            context.append(('Add-on Settings', "Addon.OpenSettings({})".format(epg.path)))

        folder.add_item(
            label   = epg.name,
            info    = {'plot': epg.plot},
            art     = {'thumb': epg.thumb},
            path    = plugin.url_for(edit_epg, epg_id=epg.id),
            context = context,
        )

    folder.add_item(
        label = _(_.ADD_EPG, _bold=True),
        path  = plugin.url_for(new_epg),
    )

    return folder

@plugin.route()
def delete_playlist(playlist_id, **kwargs):
    if not gui.yes_no('Are you sure you want to delete this playlist?'):
        return

    playlist_id = int(playlist_id)
    playlist = Playlist.get_by_id(playlist_id)
    playlist.delete_instance()
    Playlist.update(order = Playlist.order - 1).where(Playlist.order >= playlist.order).execute()

    gui.refresh()

@plugin.route()
def delete_epg(epg_id, **kwargs):
    if not gui.yes_no('Are you sure you want to delete this EPG?'):
        return

    epg_id = int(epg_id)
    epg = EPG.get_by_id(epg_id)
    epg.delete_instance()

    gui.refresh()

@plugin.route()
def new_playlist(position=None, **kwargs):
    playlist = Playlist.user_create()
    if not playlist:
        return

    if position:
        position = int(position)
        Playlist.update(order = Playlist.order + 1).where(Playlist.order >= position).execute()
        playlist.order = position
        playlist.save()

    if settings.getBool('ask_to_add', True) and playlist.source_type != Playlist.TYPE_ADDON and gui.yes_no(_.ADD_EPG):
        EPG.user_create()

    gui.refresh()

@plugin.route()
def new_epg(**kwargs):
    epg = EPG.user_create()
    if not epg:
        return

    if settings.getBool('ask_to_add', True) and epg.source_type != EPG.TYPE_ADDON and gui.yes_no(_.ADD_PLAYLIST):
        Playlist.user_create()

    gui.refresh()

@plugin.route()
def open_settings(addon_id, **kwargs):
    get_addon(addon_id, required=True).openSettings()

@plugin.route()
def edit_playlist(playlist_id, **kwargs):
    playlist_id = int(playlist_id)
    playlist    = Playlist.get_by_id(playlist_id)

    folder = plugin.Folder(playlist.label, thumb=playlist.thumb)

    folder.add_item(
        label = _(_.SOURCE_LABEL, value=playlist.label),
        path  = plugin.url_for(edit_playlist_value, playlist_id=playlist.id, method=Playlist.select_path.__name__),
    )

    folder.add_item(
        label = _(_.ENABLED_LABEL, value=playlist.enabled),
        path  = plugin.url_for(edit_playlist_value, playlist_id=playlist.id, method=Playlist.toggle_enabled.__name__),
    )

    if playlist.source_type == Playlist.TYPE_CUSTOM:
        return folder

    if playlist.source_type == Playlist.TYPE_ADDON:
        folder.add_item(
            label = _.ADDON_SETTINGS,
            path  = plugin.url_for(open_settings, addon_id=playlist.path),
        )
    else:
        folder.add_item(
            label = _(_.ARCHIVE_TYPE_LABEL, value=playlist.archive_type_name),
            path  = plugin.url_for(edit_playlist_value, playlist_id=playlist.id, method=Playlist.select_archive_type.__name__),
        )

    folder.add_item(
        label = _(_.SKIP_PLIST_CHNO_LABEL, value=playlist.skip_playlist_chno),
        path  = plugin.url_for(edit_playlist_value, playlist_id=playlist.id, method=Playlist.toggle_skip_playlist_chno.__name__),
    )

    folder.add_item(
        label = _('Use Starting Channel Number: {value}', value=playlist.use_start_chno),
        path  = plugin.url_for(edit_playlist_value, playlist_id=playlist.id, method=Playlist.toggle_use_start_chno.__name__),
    )

    if playlist.use_start_chno:
        folder.add_item(
            label =  _(_.START_CHNO_LABEL, value=playlist.start_chno),
            path  = plugin.url_for(edit_playlist_value, playlist_id=playlist.id, method=Playlist.select_start_chno.__name__),
        )

    folder.add_item(
        label = _(_.DEFAULT_VISIBILE_LABEL, value=playlist.default_visible),
        path  = plugin.url_for(edit_playlist_value, playlist_id=playlist.id, method=Playlist.toggle_default_visible.__name__),
    )

    folder.add_item(
        label = _(_.SKIP_PLIST_GROUP_NAMES, value=playlist.skip_playlist_groups),
        path  = plugin.url_for(edit_playlist_value, playlist_id=playlist.id, method=Playlist.toggle_skip_playlist_groups.__name__),
    )

    folder.add_item(
        label =  _(_.GROUP_LABEL, value=playlist.group_name),
        path  = plugin.url_for(edit_playlist_value, playlist_id=playlist.id, method=Playlist.select_group_name.__name__),
    )

    return folder

@plugin.route()
def edit_playlist_value(playlist_id, method, **kwargs):
    playlist_id = int(playlist_id)
    playlist    = Playlist.get_by_id(playlist_id)

    method = getattr(playlist, method)
    if method():
        playlist.save()
        gui.refresh()

@plugin.route()
def edit_epg(epg_id, **kwargs):
    epg_id = int(epg_id)
    epg    = EPG.get_by_id(epg_id)

    folder = plugin.Folder(epg.label, thumb=epg.thumb)

    folder.add_item(
        label = _(_.SOURCE_LABEL, value=epg.label),
        path  = plugin.url_for(edit_epg_value, epg_id=epg.id, method=EPG.select_path.__name__),
    )

    folder.add_item(
        label = _(_.ENABLED_LABEL, value=epg.enabled),
        path  = plugin.url_for(edit_epg_value, epg_id=epg.id, method=EPG.toggle_enabled.__name__),
    )

    if epg.source_type == EPG.TYPE_ADDON:
        folder.add_item(
            label = _.ADDON_SETTINGS,
            path  = plugin.url_for(open_settings, addon_id=epg.path),
        )
    else:
        folder.add_item(
            label = _(_.ARCHIVE_TYPE_LABEL, value=epg.archive_type_name),
            path  = plugin.url_for(edit_epg_value, epg_id=epg.id, method=EPG.select_archive_type.__name__),
        )

    return folder

@plugin.route()
def edit_epg_value(epg_id, method, **kwargs):
    epg_id = int(epg_id)
    epg    = EPG.get_by_id(epg_id)

    method = getattr(epg, method)
    if method():
        epg.save()
        gui.refresh()

@plugin.route()
def manager(radio=0, **kwargs):
    radio  = int(radio)

    if radio:
        folder = plugin.Folder(_.MANAGE_RADIO)
    else:
        folder = plugin.Folder(_.MANAGE_TV)

    for playlist in Playlist.select().where(Playlist.enabled == True).order_by(Playlist.order):
        folder.add_item(
            label   = playlist.label,
            art     = {'thumb': playlist.thumb},
            path    = plugin.url_for(playlist_channels, playlist_id=playlist.id, radio=radio),
        )

    folder.add_item(
        label = _(_.ALL_CHANNELS, _bold=True),
        path  = plugin.url_for(channels, radio=radio),
    )

    folder.add_item(
        label = _(_.SEARCH, _bold=True),
        path  = plugin.url_for(search_channel, radio=radio),
    )

    # folder.add_item(
    #     label = 'Groups',
    #     path  = plugin.url_for(group_manager, radio=radio),
    # )

    # folder.add_item(
    #     label = 'EPG',
    #     path  = plugin.url_for(epg_manager, radio=radio),
    # )

    return folder

@plugin.route()
def channels(radio=0, page=1, **kwargs):
    folder = plugin.Folder(_.ALL_CHANNELS)

    radio     = int(radio)
    page      = int(page)
    page_size = settings.getInt('page_size', 0)

    query = Channel.channel_list(radio=radio, page=page, page_size=page_size)

    items = _process_channels(query)
    folder.add_items(items)

    if len(items) == page_size:
        folder.add_item(
            label = _(_.NEXT_PAGE, page=page+1, _bold=True),
            path  = plugin.url_for(channels, radio=radio, page=page+1),
        )

    return folder

def _process_channels(query):
    items = []

    for channel in query:
        context = []

        label = channel.label

        if channel.modified:
            label = _(_.CHANNEL_MODIFIED, label=label)

        if not channel.visible:
            label = _(_.CHANNEL_HIDDEN, label=label)

        if channel.url:
            context.append((_.PLAY_CHANNEL, "PlayMedia({})".format(channel.get_play_path())))

        context.append((_.HIDE_CHANNEL if channel.visible else _.SHOW_CHANNEL,
            "RunPlugin({})".format(plugin.url_for(edit_channel_value, slug=channel.slug, method=Override.toggle_visible.__name__))))

        #context.append((_.EDIT_CHANNEL, "RunPlugin({})".format(plugin.url_for(edit_channel, slug=channel.slug))))

        context.append(('Channel Number', "RunPlugin({})".format(plugin.url_for(edit_channel_value, slug=channel.slug, method=Override.edit_chno.__name__))))
        context.append(('Channel Name', "RunPlugin({})".format(plugin.url_for(edit_channel_value, slug=channel.slug, method=Override.edit_name.__name__))))
        context.append(('Channel Logo', "RunPlugin({})".format(plugin.url_for(edit_channel_value, slug=channel.slug, method=Override.edit_logo.__name__))))
        context.append(('Channel Groups', "RunPlugin({})".format(plugin.url_for(edit_channel_value, slug=channel.slug, method=Override.edit_groups.__name__))))
        context.append(('EPG ID', "RunPlugin({})".format(plugin.url_for(edit_channel_value, slug=channel.slug, method=Override.edit_epg_id.__name__))))

        if channel.custom:
            context.append((_.DELETE_CHANNEL, "RunPlugin({})".format(plugin.url_for(reset_channel, slug=channel.slug))))
        elif channel.modified:
            context.append((_.RESET_CHANNEL, "RunPlugin({})".format(plugin.url_for(reset_channel, slug=channel.slug))))

        items.append(plugin.Item(
            label     = label,
            art       = {'thumb': channel.logo},
            info      = {'plot': channel.plot},
          #  path      = plugin.url_for(edit_channel, slug=channel.slug),
            path      = plugin.url_for(edit_channel_value, slug=channel.slug, method=Override.toggle_visible.__name__),
            context   = context,
            is_folder = True,
        ))

    return items

@plugin.route()
def edit_channel(slug, **kwargs):
    pass

@plugin.route()
def reset_channel(slug, **kwargs):
    channel = Channel.get_by_id(slug)

    if channel.custom:
        if not gui.yes_no('Are you sure you want to delete this channel?'):
            return

        channel.delete_instance()

    Override.delete().where(Override.slug == channel.slug).execute()

    gui.refresh()

@plugin.route()
def edit_channel_value(slug, method, **kwargs):
    channel = Channel.select(Channel, Override).where(Channel.slug == slug).join(Override, join_type="LEFT OUTER JOIN", on=(Channel.slug == Override.slug), attr='override').get()

    create = False
    if not hasattr(channel, 'override'):
        channel.override = Override(playlist=channel.playlist, slug=channel.slug)
        create = True

    method = getattr(channel.override, method)
    if method(channel):
        channel.override.save(force_insert=create)
        gui.refresh()

@plugin.route()
def search_channel(query=None, radio=0, page=1, **kwargs):
    radio  = int(radio)
    page   = int(page)

    if not query:
        query = gui.input(_.SEARCH, default=userdata.get('search', '')).strip()
        if not query:
            return

        userdata.set('search', query)

    folder = plugin.Folder(_(_.SEARCH_FOR, query=query))

    page_size = settings.getInt('page_size', 0)
    db_query  = Channel.channel_list(radio=radio, page=page, search=query, page_size=page_size)

    items = _process_channels(db_query)
    folder.add_items(items)

    if len(items) == page_size:
        folder.add_item(
            label = _(_.NEXT_PAGE, page=page+1, _bold=True),
            path  = plugin.url_for(search_channel, query=query, radio=radio, page=page+1),
        )

    return folder

@plugin.route()
def playlist_channels(playlist_id, radio=0, page=1, **kwargs):
    playlist_id = int(playlist_id)
    radio       = int(radio)
    page        = int(page)

    playlist    = Playlist.get_by_id(playlist_id)

    folder = plugin.Folder(playlist.label)

    page_size = settings.getInt('page_size', 0)
    db_query  = Channel.channel_list(playlist_id=playlist_id, radio=radio, page=page, page_size=page_size)

    items = _process_channels(db_query)
    folder.add_items(items)

    if len(items) == page_size:
        folder.add_item(
            label = _(_.NEXT_PAGE, page=page+1, _bold=True),
            path  = plugin.url_for(playlist_channels, playlist_id=playlist_id, radio=radio, page=page+1),
        )

    if playlist.source_type == Playlist.TYPE_CUSTOM:
        folder.add_item(
            label = _(_.ADD_CHANNEL, _bold=True),
            path  = plugin.url_for(add_channel, playlist_id=playlist_id, radio=radio),
        )

    return folder

@plugin.route()
def add_channel(playlist_id, radio, **kwargs):
    playlist_id = int(playlist_id)
    radio = int(radio)

    url = gui.input(_.ENTER_CHANNEL_URL)
    if not url:
        return

    playlist = Playlist.get_by_id(playlist_id)

    channel = Channel.from_url(playlist, url)
    channel.radio = radio
    channel.save(force_insert=True)

    gui.refresh()

def iptv_is_setup():
    addon = get_addon(IPTV_SIMPLE_ID, required=False, install=False)
    if not addon:
        return False

    output_dir    = xbmc.translatePath(settings.get('output_dir', '').strip() or ADDON_PROFILE)
    playlist_path = os.path.join(output_dir, PLAYLIST_FILE_NAME)
    epg_path      = os.path.join(output_dir, EPG_FILE_NAME)

    return addon.getSetting('m3uPathType') == '0' and addon.getSetting('epgPathType') == '0' \
            and addon.getSetting('m3uPath') == playlist_path and addon.getSetting('epgPath') == epg_path

@plugin.route()
def setup(**kwargs):
    if _setup():
        gui.refresh()

def _setup():
    addon = get_addon(IPTV_SIMPLE_ID, required=True, install=True)

    with gui.progress(_.SETTING_UP_IPTV) as progress:
        kodi_rpc('Addons.SetAddonEnabled', {'addonid': IPTV_SIMPLE_ID, 'enabled': False})

        output_dir    = xbmc.translatePath(settings.get('output_dir', '').strip() or ADDON_PROFILE)
        playlist_path = os.path.join(output_dir, PLAYLIST_FILE_NAME)
        epg_path      = os.path.join(output_dir, EPG_FILE_NAME)

        if not os.path.exists(playlist_path):
            with open(playlist_path, 'w') as f:
                f.write('''#EXTM3U
#EXTINF:-1 tvg-id="iptv_merge" tvg-chno="1000" tvg-logo="{}",{}
{}'''.format(ADDON_ICON, 'IPTV Merge: Click me to run a merge!', plugin.url_for(merge)))

        if not os.path.exists(epg_path):
            with open(epg_path, 'w') as f:
                f.write('''<?xml version="1.0" encoding="utf-8" ?><tv><channel id="iptv_merge"></channel></tv>''')

        ## IMPORT ANY CURRENT SOURCES ##
        cur_epg_url  = addon.getSetting('epgUrl')
        cur_epg_path = addon.getSetting('epgPath')
        cur_epg_type = addon.getSetting('epgPathType')

        if cur_epg_path != epg_path and os.path.exists(xbmc.translatePath(cur_epg_path)):
            epg = EPG(source_type=EPG.TYPE_FILE, path=cur_epg_path, enabled=cur_epg_type == '0')
            epg.auto_archive_type()
            try: epg.save()
            except: pass

        if cur_epg_url:
            epg = EPG(source_type=EPG.TYPE_URL, path=cur_epg_url, enabled=cur_epg_type == '1')
            epg.auto_archive_type()
            try: epg.save()
            except: pass

        cur_m3u_url  = addon.getSetting('m3uUrl')
        cur_m3u_path = addon.getSetting('m3uPath')
        cur_m3u_type = addon.getSetting('m3uPathType')
        start_chno   = int(addon.getSetting('startNum') or 1)
        #user_agent   = addon.getSetting('userAgent')

        if cur_m3u_path != playlist_path and os.path.exists(xbmc.translatePath(cur_m3u_path)):
            playlist = Playlist(source_type=Playlist.TYPE_FILE, path=cur_m3u_path, enabled=cur_m3u_type == '0')
            playlist.auto_archive_type()
            if start_chno != 1:
                playlist.use_start_chno = True
                playlist.start_chno = start_chno

            try: playlist.save()
            except: pass

        if cur_m3u_url:
            playlist = Playlist(source_type=Playlist.TYPE_URL, path=cur_m3u_url, enabled=cur_m3u_type == '1')
            playlist.auto_archive_type()
            if start_chno != 1:
                playlist.use_start_chno = True
                playlist.start_chno = start_chno

            try: playlist.save()
            except: pass
        #####

        addon.setSetting('epgPath', epg_path)
        addon.setSetting('m3uPath', playlist_path)
        addon.setSetting('epgUrl', '')
        addon.setSetting('m3uUrl', '')
        addon.setSetting('m3uPathType', '0')
        addon.setSetting('epgPathType', '0')

        monitor = xbmc.Monitor()

        progress.update(30)

        monitor.waitForAbort(2)
        kodi_rpc('Addons.SetAddonEnabled', {'addonid': IPTV_SIMPLE_ID, 'enabled': True})

        progress.update(60)

        monitor.waitForAbort(2)

        progress.update(100)

        set_kodi_setting('epg.futuredaystodisplay', 7)
      #  set_kodi_setting('epg.ignoredbforclient', True)
        set_kodi_setting('pvrmanager.syncchannelgroups', True)
        set_kodi_setting('pvrmanager.preselectplayingchannel', True)
        set_kodi_setting('pvrmanager.backendchannelorder', True)
        set_kodi_setting('pvrmanager.usebackendchannelnumbers', True)

    gui.ok(_.SETUP_IPTV_COMPLETE)

    return True

@plugin.route()
def merge(**kwargs):
    if get_kodi_string('_iptv_merge_force_run'):
        raise PluginError(_.MERGE_IN_PROGRESS)
    else:
        set_kodi_string('_iptv_merge_force_run', '1')

@plugin.route()
def proxy_merge(type='all', **kwargs):
    merge = Merger()

    if type == 'playlist':
        path = merge.playlists()

    elif type == 'epg':
        path = merge.epgs()

    elif type == 'all':
        merge.playlists()
        merge.epgs()
        path = merge.output_path

    return plugin.Item(path=path)

@plugin.route()
@plugin.merge()
def service_merge(forced=0, **kwargs):
    merge = Merger(forced=int(forced))
    merge.playlists()
    merge.epgs()

@plugin.route()
def setup_addon(addon_id, **kwargs):
    if not iptv_is_setup() and not _setup():
        return

    addon, data = merge_info(addon_id)

    if METHOD_PLAYLIST in data:
        playlist, created = Playlist.get_or_create(path=addon_id, defaults={'source_type': Playlist.TYPE_ADDON, 'enabled': True})
        if not playlist.enabled:
            playlist.enabled = True
            playlist.save()

    if METHOD_EPG in data:
        epg, created = EPG.get_or_create(path=addon_id, defaults={'source_type': EPG.TYPE_ADDON, 'enabled': True})
        if not epg.enabled:
            epg.enabled = True
            epg.save()

    set_kodi_string('_iptv_merge_force_run', '1')