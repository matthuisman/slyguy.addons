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

@plugin.route()
def toggle_merge(code, **kwargs):
    data = _app_data()

    regions = userdata.get('merge_regions', [])
    region = data['regions'][code]

    if code in regions:
        if code == ALL:
            regions = [ALL]

        regions.remove(code)
    else:
        if code == ALL:
            regions = []

        regions.append(code)

    if ALL in regions and code != ALL:
        regions.remove(ALL)

    gui.notification(_.MERGE_ADDED if code in regions else _.MERGE_REMOVED, heading=region['name'], icon=region['logo'])
    userdata.set('merge_regions', regions)
    gui.refresh()

@plugin.route()
def live_tv(code=None, group=None, **kwargs):
    data = _app_data()
    regions = userdata.get('merge_regions', [])

    if not code:
        folder = plugin.Folder(_.LIVE_TV)

        for code in sorted(data['regions'], key=lambda x: (data['regions'][x]['sort'], data['regions'][x]['name'])):
            region = data['regions'][code]
            ch_count = len(region['channels'])
            in_merge = code in regions

            if code == ALL:
                region['name'] = _(region['name'], _bold=True)

            folder.add_item(
                label = _(u'{name} ({count})'.format(name=region['name'], count=ch_count), _color='FF19f109' if in_merge else ''),
                art = {'thumb': region.get('logo')},
                info = {
                    'plot': u'{}\n\n{}\n\n{}'.format(region['name'], _(_.CHANNEL_COUNT, count=ch_count), _(_.MERGE_INCLUDED, _color='FF19f109') if in_merge else ''),
                },
                context = ((_.MERGE_REMOVE if in_merge else _.MERGE_ADD, 'RunPlugin({})'.format(plugin.url_for(toggle_merge, code=code))),),
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
            label = _(u'{name} ({count})'.format(name=_.ALL, count=all_count), _bold=True),
            art = {'thumb': region.get('logo')},
            path = plugin.url_for(live_tv, code=code, group=ALL),
        )

        for group in sorted(groups):
            folder.add_item(
                label = _(u'{name} ({count})'.format(name=group, count=groups[group])),
                art = {'thumb': region.get('logo')},
                path = plugin.url_for(live_tv, code=code, group=group)
            )

        return folder

    folder = plugin.Folder(region['name'] if group == ALL else group)
    show_chno = settings.getBool('show_chno', True)

    if settings.getBool('show_epg', True):
        now = arrow.now()
        EPG_EVENTS_COUNT = 5
    else:
        EPG_EVENTS_COUNT = None

    for id in sorted(channels.keys(), key=lambda x: channels[x]['chno'] if show_chno else channels[x]['name']):
        channel = channels[id]

        if group != ALL and channel['group'] != group:
            continue
        
        if not EPG_EVENTS_COUNT:
            plot = channel['description']
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
                    if count == EPG_EVENTS_COUNT:
                        break

        folder.add_item(
            label = u'{} | {}'.format(channel['chno'], channel['name']) if show_chno else channel['name'],
            info = {'plot': plot},
            art = {'thumb': channel['logo']},
            playable = True,
            path = plugin.url_for(play, id=id, _is_live=True),
        )

    return folder

@plugin.route()
def play(id, **kwargs):
    data = _app_data()
    channel = data['regions'][ALL]['channels'][id]

    return plugin.Item(
        label = channel['name'],
        info = {'plot': channel['description']},
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
    if ALL in regions:
        regions = [x for x in data['regions']]
    else:
        regions = [x for x in regions if x in data['regions']]

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
