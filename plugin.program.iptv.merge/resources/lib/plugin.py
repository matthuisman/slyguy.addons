import os
from difflib import SequenceMatcher
from distutils.version import LooseVersion

from kodi_six import xbmc, xbmcvfs

from slyguy import plugin, settings, gui, userdata
from slyguy.util import set_kodi_setting, kodi_rpc, set_kodi_string, get_kodi_string, get_addon, run_plugin, safe_copy
from slyguy.constants import ADDON_PROFILE, ADDON_ICON, KODI_VERSION, ADDON_NAME
from slyguy.exceptions import PluginError
from slyguy.monitor import monitor
from slyguy.log import log

from .language import _
from .models import Playlist, EPG, Channel, Override, merge_info
from .constants import *
from .merger import Merger

@plugin.route('')
def home(**kwargs):
    folder = plugin.Folder(cacheToDisc=False)

    if not _setup(check_only=True):
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

    if settings.getBool('http_api'):
        folder.add_item(
            label = "HTTP API Running",
            path = plugin.url_for(http_info),
        )

    if settings.getBool('bookmarks', True):
        folder.add_item(label=_.BOOKMARKS, path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False)

    return folder

@plugin.route()
def http_info(**kwargs):
    gui.text("Playlist URL\n[B]{}[/B]\n\nEPG URL\n[B]{}[/B]".format(userdata.get('_playlist_url'), userdata.get('_epg_url')))

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
            (_.DISABLE_PLAYLIST if playlist.enabled else _.ENABLE_PLAYLIST, 'RunPlugin({})'.format(plugin.url_for(edit_playlist_value, playlist_id=playlist.id, method=Playlist.toggle_enabled.__name__))),
            (_.DELETE_PLAYLIST, 'RunPlugin({})'.format(plugin.url_for(delete_playlist, playlist_id=playlist.id))),
            (_.INSERT_PLAYLIST, 'RunPlugin({})'.format(plugin.url_for(new_playlist, position=playlist.order))),
        ]

        if playlist.order > 1:
            context.append((_.MOVE_UP, 'RunPlugin({})'.format(plugin.url_for(shift_playlist, playlist_id=playlist.id, shift=-1))))

        if playlist.order < len(playlists)+1:
            context.append((_.MOVE_DOWN, 'RunPlugin({})'.format(plugin.url_for(shift_playlist, playlist_id=playlist.id, shift=1))))

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
            (_.DISABLE_EPG if epg.enabled else _.ENABLE_EPG, 'RunPlugin({})'.format(plugin.url_for(edit_epg_value, epg_id=epg.id, method=EPG.toggle_enabled.__name__))),
            (_.DELETE_EPG, 'RunPlugin({})'.format(plugin.url_for(delete_epg, epg_id=epg.id))),
        ]

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
    if not gui.yes_no(_.CONF_DELETE_PLAYLIST):
        return

    playlist_id = int(playlist_id)
    playlist = Playlist.get_by_id(playlist_id)
    playlist.delete_instance()
    Playlist.update(order = Playlist.order - 1).where(Playlist.order >= playlist.order).execute()

    gui.refresh()

@plugin.route()
def delete_epg(epg_id, **kwargs):
    if not gui.yes_no(_.CONF_DELETE_EPG):
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
        addon, data = merge_info(playlist.path)
        if 'configure' in data:
            folder.add_item(
                label = _.CONFIGURE_ADDON,
                path  = plugin.url_for(configure_addon, addon_id=playlist.path),
            )

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
        label = _(_.USE_STARTING_CHNO, value=playlist.use_start_chno),
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
def configure_addon(addon_id, **kwargs):
    addon, data = merge_info(addon_id)
    if 'configure' in data:
        path = data['configure'].replace('$ID', addon_id)
        run_plugin(path, wait=True)

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
        addon, data = merge_info(epg.path)
        if 'configure' in data:
            folder.add_item(
                label = _.CONFIGURE_ADDON,
                path  = plugin.url_for(configure_addon, addon_id=epg.path),
            )

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
    radio = int(radio)

    if radio:
        folder = plugin.Folder(_.MANAGE_RADIO)
    else:
        folder = plugin.Folder(_.MANAGE_TV)

    for playlist in Playlist.select().where(Playlist.enabled == True).order_by(Playlist.order):
        folder.add_item(
            label = playlist.label,
            art = {'thumb': playlist.thumb},
            path = plugin.url_for(playlist_channels, playlist_id=playlist.id, radio=radio),
        )

    folder.add_item(
        label = _(_.ALL_CHANNELS, _bold=True),
        path = plugin.url_for(channels, radio=radio),
    )

    folder.add_item(
        label = _(_.SEARCH, _bold=True),
        path = plugin.url_for(search_channel, radio=radio),
    )

    # folder.add_item(
    #     label = 'Groups',
    #     path = plugin.url_for(group_manager, radio=radio),
    # )

    # folder.add_item(
    #     label = 'EPG',
    #     path = plugin.url_for(epg_manager, radio=radio),
    # )

    return folder

@plugin.route()
@plugin.pagination()
def channels(radio=0, page=1, **kwargs):
    folder = plugin.Folder(_.ALL_CHANNELS)

    radio = int(radio)
    page_size = settings.getInt('page_size', 0)

    query = Channel.channel_list(radio=radio, page=page, page_size=page_size)

    items = _process_channels(query)
    folder.add_items(items)
    return folder, len(items) == page_size

def _process_channels(query):
    items = []

    for channel in query:
        context = []

        label = channel.label

        if channel.modified:
            label = _(_.CHANNEL_MODIFIED, label=label)

        if not channel.visible:
            label = _(_.CHANNEL_HIDDEN, label=label)

        context.append((_.HIDE_CHANNEL if channel.visible else _.SHOW_CHANNEL,
            'RunPlugin({})'.format(plugin.url_for(edit_channel_value, slug=channel.slug, method=Override.toggle_visible.__name__))))

        #context.append((_.EDIT_CHANNEL, 'RunPlugin({})'.format(plugin.url_for(edit_channel, slug=channel.slug))))

        context.append(("Channel Number", 'RunPlugin({})'.format(plugin.url_for(edit_channel_value, slug=channel.slug, method=Override.edit_chno.__name__))))
        context.append(("Channel Name", 'RunPlugin({})'.format(plugin.url_for(edit_channel_value, slug=channel.slug, method=Override.edit_name.__name__))))
        context.append(("Channel Logo", 'RunPlugin({})'.format(plugin.url_for(edit_channel_value, slug=channel.slug, method=Override.edit_logo.__name__))))
        context.append(("Channel Groups", 'RunPlugin({})'.format(plugin.url_for(edit_channel_value, slug=channel.slug, method=Override.edit_groups.__name__))))
        context.append(("EPG ID", 'RunPlugin({})'.format(plugin.url_for(edit_channel_value, slug=channel.slug, method=Override.edit_epg_id.__name__))))

        if channel.custom:
            context.append((_.DELETE_CHANNEL, 'RunPlugin({})'.format(plugin.url_for(reset_channel, slug=channel.slug))))
        elif channel.modified:
            context.append((_.RESET_CHANNEL, 'RunPlugin({})'.format(plugin.url_for(reset_channel, slug=channel.slug))))

        items.append(plugin.Item(
            label = label,
            art = {'thumb': channel.logo},
            info = {'plot': channel.plot},
            path = channel.get_play_path(force_proxy=True),
            context = context,
            is_folder = False,
        ))

    return items

@plugin.route()
def edit_channel(slug, **kwargs):
    pass

@plugin.route()
def reset_channel(slug, **kwargs):
    channel = Channel.get_by_id(slug)

    if channel.custom:
        if not gui.yes_no(_.CONF_DELETE_CHANNEL):
            return

        channel.delete_instance()

    Override.delete().where(Override.slug == channel.slug).execute()

    gui.refresh()

@plugin.route()
def edit_channel_value(slug, method, **kwargs):
    channel = Channel.select(Channel, Override).where(Channel.slug == slug).join(Override, join_type='LEFT OUTER JOIN', on=(Channel.slug == Override.slug), attr='override').get()

    create = False
    if not hasattr(channel, 'override'):
        channel.override = Override(playlist=channel.playlist, slug=channel.slug)
        create = True

    method = getattr(channel.override, method)
    if method(channel):
        channel.override.save(force_insert=create)
        gui.refresh()

@plugin.route()
@plugin.pagination()
def search_channel(query=None, radio=0, page=1, **kwargs):
    radio = int(radio)
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
    return folder, len(items) == page_size

@plugin.route()
@plugin.pagination()
def playlist_channels(playlist_id, radio=0, page=1, **kwargs):
    playlist_id = int(playlist_id)
    radio = int(radio)

    playlist = Playlist.get_by_id(playlist_id)

    folder = plugin.Folder(playlist.label)

    page_size = settings.getInt('page_size', 0)
    db_query = Channel.channel_list(playlist_id=playlist_id, radio=radio, page=page, page_size=page_size)

    items = _process_channels(db_query)
    folder.add_items(items)

    if playlist.source_type == Playlist.TYPE_CUSTOM:
        folder.add_item(
            label = _(_.ADD_CHANNEL, _bold=True),
            path  = plugin.url_for(add_channel, playlist_id=playlist_id, radio=radio),
        )

    return folder, len(items) == page_size

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

@plugin.route()
def setup(**kwargs):
    if _setup():
        gui.refresh()

def _setup(check_only=False, reinstall=True, run_merge=True):
    addon = get_addon(IPTV_SIMPLE_ID, required=not check_only, install=not check_only)
    if not addon:
        return False

    output_dir = settings.get('output_dir', '').strip() or ADDON_PROFILE
    playlist_path = os.path.join(output_dir, PLAYLIST_FILE_NAME)
    epg_path = os.path.join(output_dir, EPG_FILE_NAME)
    addon_path = xbmc.translatePath(addon.getAddonInfo('profile'))

    is_multi_instance = LooseVersion(addon.getAddonInfo('version')) >= LooseVersion('20.8.0')
    instance_filepath = os.path.join(addon_path, 'instance-settings-1.xml')

    if is_multi_instance:
        try:
            with open(instance_filepath) as f:
                data = f.read()
        except:
            data = ''

        is_setup = 'id="kodi_addon_instance_name">{}</setting>'.format(ADDON_NAME) in data \
            and 'id="m3uPathType">0</setting>' in data and 'id="epgPathType">0</setting>' in data \
            and 'id="m3uPath">{}</setting>'.format(playlist_path) in data and 'id="epgPath">{}</setting>'.format(epg_path) in data
    else:
        is_setup = addon.getSetting('m3uPathType') == '0' and addon.getSetting('epgPathType') == '0' \
                    and addon.getSetting('m3uPath') == playlist_path and addon.getSetting('epgPath') == epg_path

    if check_only:
        return is_setup

    elif is_setup and not reinstall:
        if run_merge:
            set_kodi_string('_iptv_merge_force_run', '1')
        return True

    with gui.busy():
        kodi_rpc('Addons.SetAddonEnabled', {'addonid': IPTV_SIMPLE_ID, 'enabled': False})
        monitor.waitForAbort(2)

        ## IMPORT ANY CURRENT URL SOURCES ##
        cur_epg_url = addon.getSetting('epgUrl')
        cur_epg_type = addon.getSetting('epgPathType')
        if cur_epg_url:
            epg = EPG(source_type=EPG.TYPE_URL, path=cur_epg_url, enabled=cur_epg_type == '1')
            try: epg.save()
            except: pass

        cur_m3u_url = addon.getSetting('m3uUrl')
        cur_m3u_type = addon.getSetting('m3uPathType')
        start_chno = int(addon.getSetting('startNum') or 1)
        #user_agent = addon.getSetting('userAgent')
        if cur_m3u_url:
            playlist = Playlist(source_type=Playlist.TYPE_URL, path=cur_m3u_url, enabled=cur_m3u_type == '1')
            if start_chno != 1:
                playlist.use_start_chno = True
                playlist.start_chno = start_chno

            try: playlist.save()
            except: pass
        ################################

        addon.setSetting('epgPath', epg_path)
        addon.setSetting('m3uPath', playlist_path)
        addon.setSetting('epgUrl', '')
        addon.setSetting('m3uUrl', '')
        addon.setSetting('m3uPathType', '0')
        addon.setSetting('epgPathType', '0')

        # newer PVR Simple uses instance settings that can't yet be set via python api
        # so do a workaround where we leverage the migration when no instance settings found
        if is_multi_instance:
            # addon.setSetting('m3uRefreshMode', '1')
            # addon.setSetting('m3uRefreshIntervalMins', '10')
            for file in os.listdir(addon_path):
                if file.startswith('instance-settings-') and file.endswith('.xml'):
                    xbmcvfs.delete(os.path.join(addon_path, file))

            kodi_rpc('Addons.SetAddonEnabled', {'addonid': IPTV_SIMPLE_ID, 'enabled': True})
            monitor.waitForAbort(1)

            # wait for migration to occur
            max_wait = 10
            while not os.path.exists(instance_filepath):
                monitor.waitForAbort(1)
                max_wait -= 1
                if max_wait <= 0:
                    break

            kodi_rpc('Addons.SetAddonEnabled', {'addonid': IPTV_SIMPLE_ID, 'enabled': False})
            monitor.waitForAbort(2)

            if os.path.exists(instance_filepath):
                with open(instance_filepath, 'r') as f:
                    data = f.read()

                data = data.replace('Migrated Add-on Config', ADDON_NAME)
                data = data.replace('<setting id="m3uPathType" default="true">1</setting>', '<setting id="m3uPathType">0</setting>') #IPTV Simple 20.8.0 bug
                with open(instance_filepath, 'w') as f:
                    f.write(data)
            else:
                log.warning('Failed to find IPTV Simple Client settings file: {}'.format(instance_filepath))

        set_kodi_setting('epg.futuredaystodisplay', 7)
        #  set_kodi_setting('epg.ignoredbforclient', True)
        set_kodi_setting('pvrmanager.syncchannelgroups', True)
        set_kodi_setting('pvrmanager.preselectplayingchannel', True)
        set_kodi_setting('pvrmanager.backendchannelorder', True)
        set_kodi_setting('pvrmanager.usebackendchannelnumbers', True)

        kodi_rpc('Addons.SetAddonEnabled', {'addonid': IPTV_SIMPLE_ID, 'enabled': True})
        monitor.waitForAbort(2)

        if run_merge:
            set_kodi_string('_iptv_merge_force_run', '1')

    gui.ok(_.SETUP_IPTV_COMPLETE)

    return True

@plugin.route()
def merge(**kwargs):
    if get_kodi_string('_iptv_merge_force_run'):
        raise PluginError(_.MERGE_IN_PROGRESS)
    else:
        set_kodi_string('_iptv_merge_force_run', '1')

@plugin.route()
@plugin.merge()
def run_merge(type='all', refresh=1, forced=0, **kwargs):
    refresh = int(refresh)
    merge = Merger(forced=int(forced))

    if type == 'playlist':
        path = merge.playlists(refresh)

    elif type == 'epg':
        merge.playlists(refresh)
        path = merge.epgs(refresh)

    elif type == 'all':
        merge.playlists(refresh)
        merge.epgs(refresh)
        path = merge.output_path

    return path

@plugin.route()
def setup_addon(addon_id, **kwargs):
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

    if 'configure' in data:
        path = data['configure'].replace('$ID', addon_id)
        run_plugin(path, wait=True)

    _setup(reinstall=False, run_merge=True)
