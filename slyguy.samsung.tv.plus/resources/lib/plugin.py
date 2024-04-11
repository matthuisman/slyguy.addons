import codecs

import arrow
from slyguy import plugin, inputstream, mem_cache, settings, userdata, gui
from slyguy.session import Session
from slyguy.exceptions import PluginError

from .language import _
from .constants import *

@plugin.route('')
def home(**kwargs):
    folder = plugin.Folder()

    folder.add_item(label=_(_.LIVE_TV, _bold=True), path=plugin.url_for(live_tv))
    folder.add_item(label=_(_.MY_CHANNELS, _bold=True), path=plugin.url_for(live_tv, code=MY_CHANNELS))
    folder.add_item(label=_(_.SEARCH, _bold=True), path=plugin.url_for(search))

    if settings.getBool('bookmarks', True):
        folder.add_item(label=_(_.BOOKMARKS, _bold=True), path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

@plugin.route()
def add_favourite(id, **kwargs):
    data = _app_data()
    channel = data['regions'][ALL]['channels'].get(id)
    if not channel:
        return

    favourites = userdata.get('favourites') or []
    if id not in favourites:
        favourites.append(id)

    userdata.set('favourites', favourites)
    gui.notification(_.MY_CHANNEL_ADDED, heading=channel['name'], icon=channel['logo'])

@plugin.route()
def del_favourite(id, **kwargs):
    favourites = userdata.get('favourites') or []
    if id in favourites:
        favourites.remove(id)

    userdata.set('favourites', favourites)
    gui.refresh()

@mem_cache.cached(60*15)
def _data():
    return Session().gz_json(DATA_URL)

def _app_data():
    data = _data()

    favourites = userdata.get('favourites') or []
    my_channels = {'logo': None, 'name': _.MY_CHANNELS, 'channels': {}, 'sort': 0}
    all_channels = {'logo': None, 'name':_.ALL, 'channels': {}, 'sort': 1}
    for key in data['regions']:
        data['regions'][key]['sort'] = 2
        for id in data['regions'][key]['channels']:
            all_channels['channels'][id] = data['regions'][key]['channels'][id]
            data['regions'][key]['channels'][id]['epg'] = key
            data['regions'][key]['channels'][id]['region'] = data['regions'][key]['name']
            if id in favourites:
                my_channels['channels'][id] = data['regions'][key]['channels'][id]

    data['regions'][ALL] = all_channels
    data['regions'][MY_CHANNELS] = my_channels
    return data

def _process_channels(channels, group=ALL, region=ALL):
    items = []

    show_chno = settings.getBool('show_chno', True)

    if settings.getBool('show_epg', True):
        now = arrow.now()
        epg_count = 5
    else:
        epg_count = None

    for id in sorted(channels.keys(), key=lambda x: channels[x]['chno'] if show_chno else channels[x]['name']):
        channel = channels[id]
        if group != ALL and channel['group'] != group:
            continue

        # currently dont work :( as license server refuses
        if channel.get('license_url'):
            continue

        plot = u'[B]{} - {}[/B]\n'.format(channel['region'], channel['group'])
        if not epg_count:
            plot += channel.get('description', '')
        else:
            count = 0
            for index, row in enumerate(channel.get('programs', [])):
                start = arrow.get(row[0])
                try: stop = arrow.get(channel['programs'][index+1][0])
                except: stop = start.shift(hours=1)

                if (now > start and now < stop) or start > now:
                    plot += u'[{}] {}\n'.format(start.to('local').format('h:mma'), row[1])
                    count += 1
                    if count == epg_count:
                        break

        item = plugin.Item(
            label = u'{} | {}'.format(channel['chno'], channel['name']) if show_chno else channel['name'],
            info = {'plot': plot},
            art = {'thumb': channel['logo']},
            playable = True,
            path = plugin.url_for(play, id=id, _is_live=True),
            context = ((_.DEL_MY_CHANNEL, 'RunPlugin({})'.format(plugin.url_for(del_favourite, id=id))),) if region == MY_CHANNELS else ((_.ADD_MY_CHANNEL, 'RunPlugin({})'.format(plugin.url_for(add_favourite, id=id))),),
        )
        items.append(item)

    return items

@plugin.route()
def live_tv(code=None, group=None, **kwargs):
    data = _app_data()

    if not settings.getBool('show_countries', True) and code != MY_CHANNELS:
        code = ALL

    if not settings.getBool('show_groups', True):
        group = ALL

    if not code:
        folder = plugin.Folder(_.LIVE_TV)
        data['regions'].pop(MY_CHANNELS)
        for code in sorted(data['regions'], key=lambda x: (data['regions'][x]['sort'], data['regions'][x]['name'])):
            region = data['regions'][code]
            ch_count = len(region['channels'])

            item = plugin.Item(
                label = _(u'{name} ({count})'.format(name=region['name'], count=ch_count)),
                art = {'thumb': region.get('logo')},
                info = {
                    'plot': u'{}\n\n{}'.format(region['name'], _(_.CHANNEL_COUNT, count=ch_count)),
                },
                path = plugin.url_for(live_tv, code=code),
            )

            folder.add_items(item)

        return folder

    region = data['regions'][code]
    folder = plugin.Folder(region['name'])
    channels = region['channels']

    if group is None:
        groups = {}
        all_count = 0
        for id in channels:
            channel = channels[id]
            all_count += 1
            if channel['group'] not in groups:
                groups[channel['group']] = 1
            else:
                groups[channel['group']] += 1

        folder = plugin.Folder(region['name'])

        if all_count:
            folder.add_item(
                label = _(u'{name} ({count})'.format(name=_.ALL, count=all_count)),
                art = {'thumb': region.get('logo')},
                path = plugin.url_for(live_tv, code=code, group=ALL),
            )

        for group in sorted(groups):
            folder.add_item(
                label = _(u'{name} ({count})'.format(name=group, count=groups[group])),
                art = {'thumb': region.get('logo')},
                info = {
                    'plot': u'{}\n\n{}'.format(group, _(_.CHANNEL_COUNT, count=groups[group])),
                },
                path = plugin.url_for(live_tv, code=code, group=group)
            )

        return folder

    folder = plugin.Folder(region['name'] if group == ALL else group, no_items_method='list')
    items = _process_channels(channels, group=group, region=code)
    folder.add_items(items)
    return folder

@plugin.route()
@plugin.search()
def search(query, page, **kwargs):
    data = _app_data()

    results = {}
    for id in data['regions'][ALL]['channels']:
        channel = data['regions'][ALL]['channels'][id]
        search_t = '{} {} {}'.format(channel['name'], channel['chno'], channel['group'])
        if query.lower() in search_t.lower():
            results[id] = channel

    return _process_channels(results), False

def _get_url(channel):
    return channel['url']

@plugin.route()
def play(id, **kwargs):
    data = _app_data()
    channel = data['regions'][ALL]['channels'][id]

    headers = data['headers']
    headers.update(channel.get('headers', {}))

    item = plugin.Item(
        label = channel['name'],
        info = {'plot': channel.get('description')},
        art = {'thumb': channel['logo']},
        headers = headers,
        path = _get_url(channel),
    )

    if channel.get('license_url'):
        item.inputstream = inputstream.Widevine(
            license_key = channel['license_url'],
            manifest_type = 'hls',
            mimetype = 'application/vnd.apple.mpegurl',
        )
    else:
        item.inputstream = inputstream.HLS(live=True)

    return item

@plugin.route()
@plugin.merge()
def playlist(output, **kwargs):
    data = _app_data()
    regions = userdata.get('merge_regions', [])
    regions = [x for x in regions if x in data['regions']]
    if not regions:
        raise PluginError(_.NO_REGIONS)

    _added = []
    _channels = []
    _epgs = []
    for code in regions:
        region = data['regions'][code]
        channels = region['channels']
        for id in sorted(channels.keys(), key=lambda x: channels[x]['chno']):
            if id in _added:
                continue

            _added.append(id)

            channel = channels[id]
            channel['id'] = id
            if channel['epg'] not in _epgs:
                _epgs.append(channel['epg'])

            _channels.append(channel)

    if len(_epgs) > 2:
        epg_urls = [EPG_URL.format(code=ALL)]
    else:
        epg_urls = [EPG_URL.format(code=code) for code in _epgs]

    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'#EXTM3U x-tvg-url="{}"'.format(','.join(epg_urls)))

        for channel in _channels:
            f.write(u'\n#EXTINF:-1 tvg-id="{id}" tvg-chno="{chno}" tvg-name="{name}" tvg-logo="{logo}" group-title="{group}",{name}\n{url}'.format(
                id=channel['id'], chno=channel['chno'], name=channel['name'], logo=channel['logo'], group=channel['group'], url=plugin.url_for(play, id=channel['id'], _is_live=True),
            ))

@plugin.route()
def configure_merge(**kwargs):
    data = _app_data()
    user_regions = userdata.get('merge_regions', [])
    avail_regions = sorted(data['regions'], key=lambda x: (data['regions'][x]['sort'], data['regions'][x]['name']))

    options = []
    preselect = []
    for index, code in enumerate(avail_regions):
        region = data['regions'][code]
        options.append(plugin.Item(label=region['name'], art={'thumb': region['logo']}))
        if code in user_regions:
            preselect.append(index)

    indexes = gui.select(heading=_.SELECT_REGIONS, options=options, multi=True, useDetails=False, preselect=preselect)
    if indexes is None:
        return

    user_regions = [avail_regions[i] for i in indexes]
    userdata.set('merge_regions', user_regions)
