import codecs

import arrow
from slyguy import plugin, gui, userdata, signals, inputstream, settings
from slyguy.session import Session
from slyguy.mem_cache import cached

from .constants import *
from .language import _

@plugin.route('')
def home(**kwargs):
    folder = plugin.Folder(cacheToDisc=False)

    folder.add_item(label=_(_.STATES, _bold=True),      path=plugin.url_for(states))
    folder.add_item(label=_(_.STATIONS, _bold=True),    path=plugin.url_for(stations))
    folder.add_item(label=_(_.SEARCH, _bold=True),      path=plugin.url_for(search))

    if settings.getBool('bookmarks', True):
        folder.add_item(label=_(_.BOOKMARKS, _bold=True),  path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

@cached(60*15)
def _app_data():
    return Session().gz_json(DATA_URL)

def _get_station_li(callsign, station, epg_count=None, now=None):
    name = station['name']
    if not station['url']:
        name = _(_.NO_STREAM_LABEL, name=name)

    if not epg_count:
        plot = station.get('description', '')
    else:
        plot = u''
        count = 0
        for index, row in enumerate(station.get('programs', [])):
            start = arrow.get(row[0])
            try: stop = arrow.get(station['programs'][index+1][0])
            except: stop = start.shift(hours=1)

            if (now > start and now < stop) or start > now:
                plot += u'[{}] {}\n'.format(start.to('local').format('h:mma'), row[1])
                count += 1
                if count == epg_count:
                    break

    return plugin.Item(
        label = name,
        info = {
            'plot': plot,
        },
        art = {'thumb': station['logo']},
        path = plugin.url_for(play, callsign=callsign, _is_live=True),
        playable = True,
    )

@plugin.route()
def states(**kwargs):
    folder = plugin.Folder(_.STATES)

    all_stations = _filtered_stations()
    states = []

    for callsign in all_stations:
        station = all_stations[callsign]
        states.extend([x for x in station['states'] if x not in states])

    for state in sorted(states):
        folder.add_item(label=state, path=plugin.url_for(stations, state=state, label=state))

    return folder

@plugin.route()
def stations(state=None, label=None, **kwargs):
    folder = plugin.Folder(label or _.STATIONS)

    if settings.getBool('show_mini_epg', True):
        now = arrow.now()
        epg_count = 5
    else:
        now = None
        epg_count = None

    all_stations = _filtered_stations()
    for callsign in sorted(all_stations, key=lambda x: all_stations[x]['name'].lower()):
        station = all_stations[callsign]
        if state and state not in station['states']:
            continue
        
        item = _get_station_li(callsign, station, epg_count=epg_count, now=now)
        folder.add_items(item)

    return folder

@plugin.route()
def search(**kwargs):
    query = gui.input(_.SEARCH, default=userdata.get('search', '')).strip()
    if not query:
        return

    userdata.set('search', query)

    if settings.getBool('show_mini_epg', True):
        now = arrow.now()
        epg_count = 5
    else:
        now = None
        epg_count = None

    all_stations = _filtered_stations()
    folder = plugin.Folder(_(_.SEARCH_FOR, query=query))
    
    query = query.lower().strip()
    for callsign in all_stations:
        station = all_stations[callsign]

        states = [x.lower() for x in station['states']]
        if query == callsign.lower() or query in station['name'].lower():
            item = _get_station_li(callsign, station, epg_count=epg_count, now=now)
            folder.add_items(item)

    return folder

def _filtered_stations():
    stations = {}
    all_stations = _app_data()['channels']

    for callsign in all_stations:
        station = all_stations[callsign]
        if not settings.getBool('show_no_streams', True) and not station['url']:
            continue
        stations[callsign] = station

    return stations

@plugin.route()
def play(callsign, **kwargs):
    app_data = _app_data()
    all_stations = app_data['channels']
    station = all_stations[callsign]

    if not station['url']:
        plugin.exception(_.NO_STREAM_MSG)

    item = plugin.Item(
        label = station['name'],
        path = station['url'],
        art = {'thumb': station['logo']},
        headers = app_data['headers'],
        inputstream = inputstream.HLS(live=True),
    )

    return item

@plugin.route()
@plugin.merge()
def playlist(output, **kwargs):
    all_stations = _app_data()['channels']

    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'#EXTM3U\n')

        for callsign in all_stations:
            station = all_stations[callsign]
            if not station['url']:
                continue

            f.write(u'#EXTINF:-1 tvg-id="{id}" tvg-logo="{logo}",{name}\n{path}\n'.format(
                        id=callsign, name=station['name'], logo=station['logo'], path=plugin.url_for(play, callsign=callsign, _is_live=True)))
