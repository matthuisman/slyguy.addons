import codecs
from xml.sax.saxutils import escape

import arrow

from slyguy import plugin, inputstream, signals, settings
from slyguy.session import Session
from slyguy.util import gzip_extract
from slyguy.language import _
from slyguy.log import log

from .api import API
from .language import _
from .constants import *

api = API()

@signals.on(signals.BEFORE_DISPATCH)
def before_dispatch():
    api.new_session()

@plugin.route('')
def home(**kwargs):
    folder = plugin.Folder()

    folder.add_item(label=_(_.LIVE_TV, _bold=True), path=plugin.url_for(live_tv))

    if settings.getBool('bookmarks', True):
        folder.add_item(label=_(_.BOOKMARKS, _bold=True),  path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

@plugin.route()
def live_tv(**kwargs):
    folder = plugin.Folder(_.LIVE_TV)

    now = arrow.now()
    channels = api.channels()
    EPG_EVENTS_COUNT = 5

    for id in sorted(channels.keys(), key=lambda x: channels[x]['chno']):
        channel = channels[id]

        plot = u''
        count = 0
        for row in channel.get('programs', []):
            start = arrow.get(row['start']).to('utc')
            stop  = arrow.get(row['stop']).to('utc')

            if (now > start and now < stop) or start > now:
                plot += u'[{}] {}\n'.format(start.to('local').format('h:mma'), row['title'])
                count += 1
                if count == EPG_EVENTS_COUNT:
                    break

        folder.add_item(
            label = _(_.CH_LABEL, chno=channel['chno'], name=channel['name']),
            art = {'thumb': channel['logo']},
            info = {'plot': plot.strip('\n')},
            playable = True,
            path = plugin.url_for(play, id=id, _is_live=True),
        )

    return folder

@plugin.route()
def play(id, **kwargs):
    channel = api.all_channels()[id]

    item = plugin.Item(
        label = channel['name'],
        art = {'thumb': channel['logo']},
        path = api.play(id) if settings.getBool('use_alt_streams', False) else channel['url'],
        headers = api._session.headers,
        inputstream = inputstream.HLS(live=True, x_discontinuity=True),
    )

    return item

@plugin.route()
@plugin.merge()
def playlist(output, **kwargs):
    channels = api.channels()

    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'#EXTM3U')

        for id in sorted(channels.keys(), key=lambda x: channels[x]['chno']):
            channel = channels[id]
            f.write(u'\n#EXTINF:-1 tvg-chno="{chno}" tvg-id="{id}" tvg-name="{name}" tvg-logo="{logo}" group-title="{group}",{name}\n{url}'.format(
                chno = channel['chno'], id = id, name = channel['name'], group = channel['group'], logo = channel['logo'], url = plugin.url_for(play, id=id, _is_live=True),
            ))

@plugin.route()
@plugin.merge()
def epg(output, **kwargs):
    region = settings.getEnum('region', REGIONS, default=US)

    if region not in (LOCAL, CUSTOM):
        epg_url = MH_EPG_URL.format(region=region)

        try:
            Session().chunked_dl(epg_url, output)
            if epg_url.endswith('.gz'):
                gzip_extract(output)
            return
        except Exception as e:
            log.exception(e)
            log.debug('Failed to get remote epg: {}. Fall back to scraping'.format(epg_url))

    def process_epg(channels):
        count = 0
        for id in channels:
            channel = channels[id]
            for row in channel.get('programs', []):
                start = arrow.get(row['start']).to('utc')
                stop  = arrow.get(row['stop']).to('utc')
                title = row['title']
                description = row['episode']['description']
                subtitle = row['episode']['name']
                category = row['episode']['genre']
                icon = None

                if subtitle.lower().strip() == title.lower().strip():
                    subtitle = None

                f.write(u'<programme channel="{}" start="{}" stop="{}"><title>{}</title><desc>{}</desc>{}{}{}</programme>'.format(
                        id,
                        start.format('YYYYMMDDHHmmss Z'),
                        stop.format('YYYYMMDDHHmmss Z'),
                        escape(title),
                        escape(description),
                        u'<icon src="{}"/>'.format(escape(icon)) if icon else '',
                        u'<sub-title>{}</sub-title>'.format(escape(subtitle)) if subtitle else '',
                        u'<category>{}</category>'.format(escape(category)) if category else '',
                    ))

                count += 1

        return count

    HOUR_SHIFT = 6
    now = arrow.now()
    start = now.replace(minute=0, second=0, microsecond=0).to('utc')
    stop = start.shift(hours=HOUR_SHIFT)
    END_TIME = start.shift(days=settings.getInt('epg_days', 3))

    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'<?xml version="1.0" encoding="utf-8" ?><tv>')

        channels = api.epg(start, stop)
        for id in channels:
            f.write(u'<channel id="{id}"/>'.format(id=id))

        added = process_epg(channels)
        while stop < END_TIME:
            start = stop
            stop  = start.shift(hours=HOUR_SHIFT)

            channels = api.epg(start, stop)
            added = process_epg(channels)

            if added <= len(channels):
                break

        f.write(u'</tv>')