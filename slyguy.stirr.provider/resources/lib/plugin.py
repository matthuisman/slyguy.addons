import codecs

import arrow
from slyguy import plugin, inputstream, mem_cache, settings, gui, userdata
from slyguy.session import Session

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

@mem_cache.cached(60*5)
def _app_data():
    return Session().gz_json(DATA_URL)

def _get_channels(query=None):
    channels = _app_data()['channels']

    query = query.lower().strip() if query else None

    if settings.getBool('show_mini_epg', True):
        now = arrow.now()
        epg_count = 5
    else:
        now = None
        epg_count = None

    items = []
    for id in sorted(channels.keys(), key=lambda x: channels[x]['name']):
        channel = channels[id]

        if query and (query not in channel['name'].lower()):
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
            label = channel['name'],
            info = {'plot': plot},
            art = {'thumb': channel['logo']},
            playable = True,
            path = plugin.url_for(play, id=id, _is_live=True),
        )
        items.append(item)

    return items

@plugin.route()
def live_tv(**kwargs):
    folder = plugin.Folder(_.LIVE_TV)
    items = _get_channels()
    folder.add_items(items)
    return folder

@plugin.route()
@plugin.search()
def search(query, page, **kwargs):
    return _get_channels(query=query), False

@plugin.route()
def play(id, **kwargs):
    data = _app_data()
    channel = data['channels'][id]

    return plugin.Item(
        label = channel['name'],
        info = {'plot': channel['description']},
        art = {'thumb': channel['logo']},
        headers = data['headers'],
        inputstream = inputstream.HLS(live=True),
        path = channel['url'],
    )

@plugin.route()
@plugin.merge()
def playlist(output, **kwargs):
    channels = _app_data()['channels']

    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'#EXTM3U')

        for id in sorted(channels.keys(), key=lambda x: channels[x]['name']):
            channel = channels[id]
            f.write(u'\n#EXTINF:-1 tvg-id="{id}" tvg-name="{name}" tvg-logo="{logo}",{name}\n{url}'.format(
                id = id, name = channel['name'], logo = channel['logo'], url = plugin.url_for(play, id=id, _is_live=True),
            ))
