import uuid
import codecs

import arrow
from slyguy import plugin, inputstream, mem_cache, settings, userdata, gui
from slyguy.session import Session
from slyguy.util import gzip_extract

from .language import _
from .constants import *

@plugin.route('')
def home(**kwargs):
    folder = plugin.Folder()

    folder.add_item(label=_(_.LIVE_TV, _bold=True), path=plugin.url_for(live_tv))

    if settings.getBool('bookmarks', True):
        folder.add_item(label=_(_.BOOKMARKS, _bold=True),  path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

@mem_cache.cached(60*15)
def _data():
    return Session().gz_json(DATA_URL)

def _app_data():
    data = _data()

    region = {'logo': None, 'name':_.ALL, 'channels': {}, 'sort': 0}
    for key in data['regions']:
        data['regions'][key]['sort'] = 1
        region['channels'].update(data['regions'][key]['channels'])

    data['regions'][ALL] = region

    return data

def _process_channels(channels, group=ALL):
    items = []

    show_chno = settings.getBool('show_chno', True)

    if settings.getBool('show_mini_epg', True):
        now = arrow.now()
        epg_count = 5
    else:
        epg_count = None

    for id in sorted(channels.keys(), key=lambda x: channels[x]['chno'] if show_chno else channels[x]['name']):
        channel = channels[id]

        if group != ALL and channel['group'] != group:
            continue

        if not epg_count:
            plot = channel.get('description', '')
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
            label = u'{} | {}'.format(channel['chno'], channel['name']) if show_chno else channel['name'],
            info = {'plot': plot},
            art = {'thumb': channel['logo']},
            playable = True,
            path = plugin.url_for(play, id=id, _is_live=True),
        )
        items.append(item)

    return items

@plugin.route()
def live_tv(code=None, group=None, **kwargs):
    data = _app_data()
    regions = userdata.get('merge_regions', [])

    if not code:
        folder = plugin.Folder(_.LIVE_TV)

        for code in sorted(data['regions'], key=lambda x: (data['regions'][x]['sort'], data['regions'][x]['name'])):
            region = data['regions'][code]
            ch_count = len(region['channels'])

            folder.add_item(
                label = _(u'{name} ({count})'.format(name=region['name'], count=ch_count)),
                art = {'thumb': region.get('logo')},
                info = {
                    'plot': u'{}\n\n{}'.format(region['name'], _(_.CHANNEL_COUNT, count=ch_count)),
                },
                path = plugin.url_for(live_tv, code=code),
            )

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

        folder.add_item(
            label = _.SEARCH,
            art = {'thumb': region.get('logo')},
            path = plugin.url_for(search, code=code),
        )

        return folder

    folder = plugin.Folder(region['name'] if group == ALL else group)
    items = _process_channels(channels, group=group)
    folder.add_items(items)
    return folder

@plugin.route()
def search(code, query=None, **kwargs):
    if not query:
        query = gui.input(_.SEARCH, default=userdata.get('search', '')).strip()
        if not query:
            return

        userdata.set('search', query)

    folder = plugin.Folder(_(_.SEARCH_FOR, query=query))

    data = _app_data()

    results = {}
    for id in data['regions'][code]['channels']:
        channel = data['regions'][code]['channels'][id]
        search_t = '{} {} {}'.format(channel['name'], channel['chno'], channel['group'])
        if query.lower() in search_t.lower():
            results[id] = channel

    items = _process_channels(results)
    folder.add_items(items)

    return folder

def _get_url(channel):
    device_id = str(uuid.uuid3(uuid.UUID(UUID_NAMESPACE), str(uuid.getnode())))

    url = channel['url_alt'] if settings.getBool('show_adverts', True) else channel['url']
    url = url.replace('%7BPSID%7D', device_id)

    return url

@plugin.route()
def play(id, **kwargs):
    data = _app_data()
    data['regions'].pop(ALL, None)

    channel = None
    region = None
    for code in data['regions']:
        channels = data['regions'][code]['channels']
        if id in channels:
            channel = channels[id]
            region = data['regions'][code]
            break

    if not channel:
        raise Exception('Unable to find that channel')

    headers = data.get('headers', {})
    headers.update(region.get('headers', {}))
    headers.update(channel.get('headers', {}))

    return plugin.Item(
        label = channel['name'],
        info = {'plot': channel.get('description', '')},
        art = {'thumb': channel['logo']},
        inputstream = inputstream.HLS(live=True),
        headers = headers,
        path = _get_url(channel),
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

    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'#EXTM3U')

        for code in regions:
            region = data['regions'][code]
            channels = region['channels']

            for id in sorted(channels.keys(), key=lambda x: channels[x]['chno']):
                channel = channels[id]
                f.write(u'\n#EXTINF:-1 tvg-id="{id}" tvg-chno="{chno}" tvg-name="{name}" tvg-logo="{logo}" group-title="{region};{group}",{name}\n{url}'.format(
                    id=id, chno=channel['chno'], name=channel['name'], logo=channel['logo'], region=region['name'], group=channel['group'], url=plugin.url_for(play, id=id, _is_live=True),
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
