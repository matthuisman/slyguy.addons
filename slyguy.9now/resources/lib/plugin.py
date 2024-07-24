import string
import codecs

import arrow
from six.moves.urllib.parse import urlencode, parse_qsl
from kodi_six import xbmcplugin
from slyguy import plugin, settings, inputstream
from slyguy.constants import *

from .api import API
from .constants import *
from .language import _

api = API()

@plugin.route('')
def home(**kwargs):
    folder = plugin.Folder()

    folder.add_item(label=_(_.LIVE_TV, _bold=True), path=plugin.url_for(live_tv))
    folder.add_item(label=_(_.FEATURED, _bold=True), path=plugin.url_for(featured))
    folder.add_item(label=_(_.SHOWS, _bold=True), path=plugin.url_for(shows))
    folder.add_item(label=_(_.CATEGORIES, _bold=True), path=plugin.url_for(categories))
    folder.add_item(label=_(_.SEARCH, _bold=True), path=plugin.url_for(search))

    if settings.getBool('bookmarks', True):
        folder.add_item(label=_(_.BOOKMARKS, _bold=True), path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

    folder.add_item(label=_.SETTINGS,  path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

@plugin.route()
def featured(rail=None, **kwargs):
    folder = plugin.Folder(_.FEATURED)

    data = api.featured()
    for row in data['items']:
        if rail == row['id'] or (not rail and row['type'] == 'featured-rail'):
            if rail:
                folder.title = row['title']

            for row2 in row.get('items', []):
                if row2['link']['type'] in ('episode', 'clip'):
                    item = _parse_episode(row2)
                    folder.add_items(item)
                elif row2['link']['type'] == 'tv-series':
                    item = _parse_show(row2)
                    folder.add_items(item)

        elif not rail and row.get('items'):
            folder.add_item(
                label = row['title'],
                path  = plugin.url_for(featured, rail=row['id']),
            )

    return folder

@plugin.route()
def show(show, **kwargs):
    data = api.show(show)

    if settings.getBool('flatten_single_season', True) and len(data['seasons']) == 1:
        if not data['seasons'][0]['episodeCount']:
            return plugin.redirect(plugin.url_for(clips, show=show, season=data['seasons'][0]['slug']))
        else:
            return plugin.redirect(plugin.url_for(episodes, show=show, season=data['seasons'][0]['slug']))

    folder = plugin.Folder(data['tvSeries']['name'], fanart=data['tvSeries']['image']['sizes']['w1920'])

    for row in sorted(data['seasons'], key=lambda x: x['seasonNumber']):
        context = [(_(_.SUGGESTED, _bold=True), 'Container.Update({})'.format(plugin.url_for(suggested, show=show)))]

        if not row['episodeCount']:
            path = plugin.url_for(clips, show=show, season=row['slug'])
            plot = data['tvSeries']['description']
        else:
            path = plugin.url_for(episodes, show=show, season=row['slug'])
            plot = u'{}\n\n{}'.format(data['tvSeries']['description'], _(_.EPIOSDE_COUNT, count=row['episodeCount'], _bold=True))
            context.insert(0, (_(_.CLIPS, _bold=True), 'Container.Update({})'.format(plugin.url_for(clips, show=show, season=row['slug']))))

        folder.add_item(
            label = row['name'],
            art   = {'thumb': data['tvSeries']['image']['sizes']['w768']},
            info  = {'plot': plot},
            path  = path,
            context = context,
        )

    if not settings.getBool('hide_suggested', False):
        folder.add_item(
            label = _.SUGGESTED,
            art = {'thumb': data['tvSeries']['image']['sizes']['w768']},
            path = plugin.url_for(suggested, show=show),
            specialsort = 'bottom',
        )

    return folder

@plugin.route()
def suggested(show, **kwargs):
    data = api.show(show)

    folder = plugin.Folder(data['tvSeries']['name'], fanart=data['tvSeries']['image']['sizes']['w1920'])

    for row in data['items']:
        if row['id'].upper().startswith('RECOMMENDED-SHOWS'):
            for row2 in row.get('items', []):
                if row2['link']['type'] == 'tv-series':
                    item = _parse_show(row2)
                    folder.add_items(item)

    return folder

@plugin.route()
@plugin.pagination()
def episodes(show, season, page=1, **kwargs):
    data = api.episodes(show, season, page=page, items_per_page=None)

    folder = plugin.Folder(
        title = data['tvSeries']['name'],
        fanart = data['tvSeries']['image']['sizes']['w1920'],
        sort_methods = [xbmcplugin.SORT_METHOD_EPISODE, xbmcplugin.SORT_METHOD_UNSORTED, xbmcplugin.SORT_METHOD_LABEL],
    )

    for row in data['episodes']['items']:
        item = _parse_episode(row)
        folder.add_items(item)

    return folder, data['episodes']['count'] > (data['episodes']['take'] + data['episodes']['skip'])

@plugin.route()
@plugin.pagination()
def clips(show, season, page=1, **kwargs):
    data = api.clips(show, season, page=page, items_per_page=50)

    folder = plugin.Folder(
        title = data['tvSeries']['name'],
        fanart = data['tvSeries']['image']['sizes']['w1920'],
    )

    for row in data['clips']['items']:
        item = _parse_episode(row)
        folder.add_items(item)

    return folder, data['clips']['count'] > (data['clips']['take'] + data['clips']['skip'])

@plugin.route()
def shows(sort=None, **kwargs):
    SORT_ALL = 'ALL'
    SORT_0_9 = '0-9'

    sortings = [[_(_.ALL, _bold=True), SORT_ALL], [_.ZERO_NINE, SORT_0_9]]
    for letter in string.ascii_uppercase:
        sortings.append([letter, letter])

    if sort is None:
        folder = plugin.Folder(_.SHOWS)

        for sorting in sortings:
            folder.add_item(label=sorting[0], path=plugin.url_for(shows, sort=sorting[1]))

        return folder

    if sort == SORT_ALL:
        label = _.ALL
    elif sort == SORT_0_9:
        label = _.ZERO_NINE
    else:
        label = sort

    folder = plugin.Folder(_(_.SHOWS_LETTER, sort=label))

    rows = []
    for row in api.shows():
        if not row['name'].strip():
            continue

        sort_by = row['name'].upper().strip()[0]
        if sort_by not in string.ascii_uppercase:
            sort_by = SORT_0_9

        if sort == SORT_ALL or sort == sort_by:
            rows.append(row)

    for row in rows:
        folder.add_items(_parse_show(row))

    return folder

@plugin.route()
def categories(category=None, **kwargs):
    if category is None:
        folder = plugin.Folder(_.CATEGORIES)

        for row in api.categories():
            folder.add_item(
                label = row['name'],
                art = {'thumb': row['image']['sizes']['w768'], 'fanart': row['image']['sizes']['w1920']},
                path = plugin.url_for(categories, category=row['slug']),
            )

        return folder

    data = api.category(category)

    folder = plugin.Folder(data['genre']['name'])

    for row in data['tvSeries']:
        folder.add_items(_parse_show(row))

    return folder

@plugin.route()
@plugin.search()
def search(query, page, **kwargs):
    items = []
    for row in api.shows():
        if not row['name'].strip():
            continue

        if query.lower() in row['name'].lower():
            items.append(_parse_show(row))

    return items, False

def _channels():
    region = settings.getEnum('region', REGIONS, default=NSW)
    data = api.channels(region)
    data['channels'].extend([row for row in data['events'] if row['type'] == 'live-event' and row['nextEvent']['name']])
    data['events'] = [row for row in data['events'] if row not in data['channels']]
    return data

@plugin.route()
def live_events(**kwargs):
    data = _channels()
    now = arrow.now()

    folder = plugin.Folder(_.LIVE_EVENTS)

    for row in sorted(data.get('events', []), key=lambda row:arrow.get(row['startDate'])):
        start = arrow.get(row['startDate']).to('local')
        end = arrow.get(row['endDate']).to('local')

        plot = row['subtitle']
        if now > start and now < end:
            label = row['displayName']
        else:
            label = u'{} [B][{}][/B]'.format(row['displayName'], start.humanize())
            plot += '\n\n[B]{}[/B]'.format(start.format('h:mma DD/MM/YYYY'))

        folder.add_item(
            label = label,
            info = {'plot': plot},
            art = {'thumb': row['image']['sizes']['w768'], 'fanart': row['image']['sizes']['w1920']},
            path = plugin.url_for(play_event, reference=row['referenceId'], _is_live=row['type'] == 'live-event'),
            playable = True,
        )

    return folder

@plugin.route()
def live_tv(**kwargs):
    data = _channels()
    now = arrow.now()

    folder = plugin.Folder(_.LIVE_TV)

    for row in data['channels']:
        plot = u''
        listings = row.get('listings', [])
        for listing in listings:
            start = arrow.get(listing['startTime']).to('utc')
            stop = arrow.get(listing['endTime']).to('utc')

            if (now > start and now < stop) or start > now:
                if len(listings) > 1:
                    plot += u'[{}] {}\n'.format(start.to('local').format('h:mma'), listing['name'])
                else:
                    plot += u'[{} - {}]\n{}'.format(start.to('local').format('h:mma'), stop.to('local').format('h:mma'), listing['name'])

        if row.get('type') == 'live-event':
            path = plugin.url_for(play, reference=row.get('brightcoveId', row['referenceId']), _is_live=True)
        else:
            path = plugin.url_for(play_channel, reference=row['referenceId'], _is_live=True)

        folder.add_item(
            label = row['name'],
            info = {'plot': plot},
            art = {'thumb': row['image']['sizes']['w768']},
            path = path,
            playable = True,
        )

    if data.get('events'):
        folder.add_item(
            label = _(_.LIVE_EVENTS, _bold=True),
            info = {'plot': _(_.EVENT_COUNT, count=len(data['events']), _bold=True)},
            path = plugin.url_for(live_events),
            specialsort = 'bottom',
        )

    return folder


@plugin.route()
def play(reference, **kwargs):
    return _play(reference, is_live=ROUTE_LIVE_TAG in kwargs)


@plugin.route()
def play_event(reference, **kwargs):
    event = None
    data = _channels()
    for row in data.get('events', []):
        if row['referenceId'] == reference:
            event = row
            break

    if not event:
        raise Exception('could not find event')

    item = api.get_brightcove_src(event['referenceId'])
    try:
        item.path += '?{}'.format(event['ssai']['postfixParams'])
    except KeyError:
        pass

    item.headers = HEADERS
    if ROUTE_LIVE_TAG in kwargs and item.inputstream:
        item.inputstream.live = True

    return item


@plugin.route()
def play_channel(reference, **kwargs):
    url = None
    data = _channels()
    for row in data['channels']:
        if row['referenceId'] == reference:
            url = row['stream']['url']
            break

    # fix encoded query
    if '?' in url:
        url = url.split('?')[0] + '?' + urlencode(parse_qsl(url.split('?')[1]))

    return plugin.Item(
        headers = HEADERS,
        path = url,
        inputstream = inputstream.HLS(live=True),
    )


def _play(reference, is_live=False):
    item = api.get_brightcove_src(reference)
    item.headers = HEADERS
    if is_live and item.inputstream:
        item.inputstream.live = True
    return item

def _parse_show(row):
    if not row['episodeCount']:
        plot = row['description']
    else:
        plot = u'{}\n\n{}'.format(row['description'], _(_.EPIOSDE_COUNT, count=row['episodeCount'], _bold=True))

    item = plugin.Item(
        label = row['name'],
        info = {'plot': plot},
        art = {'thumb': row['image']['sizes']['w768'], 'fanart': row['image']['sizes']['w1920']},
        path = plugin.url_for(show, show=row['slug']),
        context = [(_(_.SUGGESTED, _bold=True), 'Container.Update({})'.format(plugin.url_for(suggested, show=row['slug'])))]
    )

    return item

def _parse_episode(row):
    season = row['partOfSeason']['name']
    if season.startswith('Season'):
        season = season[6:].strip()

    return plugin.Item(
        label = row['name'],
        art = {'thumb': row['image']['sizes']['w768']},
        info = {
            'plot': row['description'],
            'season': season,
            'episode': row.get('episodeNumber'),
            'mediatype': 'episode',
            'tvshowtitle': row['partOfSeries']['name'],
        },
        playable = True,
        path = plugin.url_for(play, reference=row['video'].get('brightcoveId', row['video']['referenceId'])),
    )

@plugin.route()
@plugin.merge()
def playlist(output, **kwargs):
    data = _channels()
    region = settings.getEnum('region', REGIONS, default=NSW)

    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'#EXTM3U x-tvg-url="{}"'.format(EPG_URL))

        for row in data['channels']:
            f.write(u'\n#EXTINF:-1 tvg-id="{id}" tvg-name="{name}" tvg-logo="{logo}",{name}\n{url}'.format(
                id=row['slug']+'-'+region, name=row['name'], logo=row['image']['sizes']['w768'],
                    url=plugin.url_for(play_channel, reference=row['referenceId']), _is_live=True),
            )
