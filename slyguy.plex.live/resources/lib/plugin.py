import codecs

import arrow
from slyguy import plugin, inputstream, mem_cache, settings, userdata, gui
from slyguy.session import Session
from slyguy.util import gzip_extract
from slyguy.exceptions import PluginError

from .language import _
from .constants import *

@plugin.route('')
def home(**kwargs):
    folder = plugin.Folder()

    folder.add_item(label=_(_.LIVE_TV, _bold=True), path=plugin.url_for(live_tv))
    folder.add_item(label=_(_.SEARCH, _bold=True), path=plugin.url_for(search))

    if settings.getBool('bookmarks', True):
        folder.add_item(label=_(_.BOOKMARKS, _bold=True),  path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

@mem_cache.cached(60*15)
def _data():
    return Session().gz_json(DATA_URL)

def _app_data():
    data = _data()

    for key in data['regions']:
        data['regions'][key]['sort'] = 1
        data['regions'][key]['channels'] = {}

    data['regions'][ALL] = {'logo': None, 'name':_.ALL, 'channels': {}, 'sort': 0}

    for id in data['channels']:
        channel = data['channels'][id]
        for code in channel['regions']:
            data['regions'][code]['channels'][id] = channel
            data['regions'][ALL]['channels'][id] = channel

    return data

def _process_channels(channels, query=None):
    items = []

    query = query.lower().strip() if query else None

    if settings.getBool('show_epg', True):
        now = arrow.now()
        epg_count = 5
    else:
        epg_count = None

    for id in sorted(channels.keys(), key=lambda x: channels[x]['name']):
        channel = channels[id]

        if query and query not in channel['name'].lower():
            continue

        if not epg_count:
            plot = channel.get('description')
        else:
            plot = u''
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
            label = channel['name'],
            info = {'plot': plot},
            art = {'thumb': channel['logo']},
            playable = True,
            path = plugin.url_for(play, id=id, _is_live=True),
        )
        items.append(item)

    return items

@plugin.route()
def live_tv(code=None, **kwargs):
    data = _app_data()

    if not code:
        folder = plugin.Folder(_.LIVE_TV)

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
    channels = region['channels']

    folder = plugin.Folder(region['name'])
    items = _process_channels(channels)
    folder.add_items(items)
    return folder

@plugin.route()
@plugin.search()
def search(query, page, **kwargs):
    data = _app_data()
    return _process_channels(data['regions'][ALL]['channels'], query=query), False

@plugin.route()
def play(id, **kwargs):
    data = _app_data()
    channel = data['regions'][ALL]['channels'][id]
    region = data['regions'][channel['regions'][0]]

    headers = data['headers']
    headers.update(region.get('headers', {}))

    if not channel.get('url'):
        channel['url'] = Session().head(PLAY_URL.format(id=id), headers=headers).headers.get('location')

    if not channel['url']:
        raise PluginError(_.NO_VIDEO_FOUND)

    return plugin.Item(
        label = channel['name'],
        info = {'plot': channel.get('description')},
        art = {'thumb': channel['logo']},
        inputstream = inputstream.HLS(live=True),
        headers = data['headers'],
        path = channel['url'],
    )

@plugin.route()
@plugin.merge()
def playlist(output, **kwargs):
    data = _app_data()
    data['regions'].pop(ALL, None)

    regions = userdata.get('merge_regions', [])
    regions = [x for x in regions if x in data['regions']]

    if not regions:
        raise Exception(_.NO_REGIONS)

    added = []
    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'#EXTM3U')

        for code in regions:
            region = data['regions'][code]
            channels = region['channels']

            for id in sorted(channels.keys(), key=lambda x: channels[x]['name']):
                if id in added:
                    continue
                else:
                    added.append(id)

                channel = channels[id]
                f.write(u'\n#EXTINF:-1 tvg-id="{id}" tvg-name="{name}" tvg-logo="{logo}" group-title="{region}",{name}\n{url}'.format(
                    id=id, name=channel['name'], logo=channel['logo'], region=region['name'], url=plugin.url_for(play, id=id, _is_live=True),
                ))

@plugin.route()
def configure_merge(**kwargs):
    data = _app_data()
    data['regions'].pop(ALL, None)

    user_regions = userdata.get('merge_regions', [])
    avail_regions = sorted(data['regions'], key=lambda x: (data['regions'][x]['sort'], data['regions'][x]['name']))

    options = []
    preselect = []
    for index, code in enumerate(avail_regions):
        region = data['regions'][code]
        options.append(plugin.Item(label=region['name'], art={'thumb': region['logo']}))
        if code in user_regions:
            preselect.append(index)

    indexes = gui.select(heading=_.SELECT_REGIONS, options=options, multi=True, useDetails=True, preselect=preselect)
    if indexes is None:
        return

    user_regions = [avail_regions[i] for i in indexes]
    userdata.set('merge_regions', user_regions)
