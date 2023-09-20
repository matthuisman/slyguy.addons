import codecs

import arrow
from slyguy import plugin, inputstream, settings
from slyguy.session import Session
from slyguy.mem_cache import cached

from .language import _
from .constants import *

@plugin.route('')
def home(**kwargs):
    folder = plugin.Folder(cacheToDisc=False)

    folder.add_item(label=_(_.LIVE_TV, _bold=True), path=plugin.url_for(live_tv))

    if settings.getBool('bookmarks', True):
        folder.add_item(label=_(_.BOOKMARKS, _bold=True), path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

@plugin.route()
def live_tv(**kwargs):
    folder = plugin.Folder(_.LIVE_TV)
    show_chnos = settings.getBool('show_chnos', True)
    hide_fast = settings.getBool('hide_fast_channels', False)

    if settings.getBool('show_epg', True):
        now = arrow.now()
        epg_count = 5
    else:
        epg_count = None

    channels = get_channels()
    for slug in sorted(channels, key=lambda k: (float(channels[k].get('chno', 'inf')), channels[k]['name'])):
        channel = channels[slug]
        if hide_fast and not channel.get('chno'):
            continue

        plot = u''
        count = 0
        if epg_count:
            if channel.get('epg_id') and not channel.get('programs'):
                channel['programs'] = channels.get(channel['epg_id'], {}).get('programs', [])

            for index, row in enumerate(channel.get('programs', [])):
                start = arrow.get(row[0])
                try: stop = arrow.get(channel['programs'][index+1][0])
                except: stop = start.shift(hours=1)

                if (now > start and now < stop) or start > now:
                    plot += u'[{}] {}\n'.format(start.to('local').format('h:mma'), row[1])
                    count += 1
                    if count == epg_count:
                        break

        if not count:
            plot += channel.get('description', '')

        item = plugin.Item(
            label = channel['name'],
            path = plugin.url_for(play, slug=slug, _is_live=True),
            info = {'plot': plot},
            art = {'thumb': channel.get('logo'), 'fanart': channel.get('fanart')},
            playable = True,
        )

        if channel.get('chno') and show_chnos:
            item.label = _(_.LIVE_CHNO, chno=channel['chno'], label=item.label)

        folder.add_items(item)

    return folder

@plugin.route()
def play(slug, **kwargs):
    channel = get_channels()[slug]

    item = plugin.Item(
        label = channel['name'],
        path = channel['mjh_master'],
        headers = channel['headers'],
        info = {'plot': channel.get('description')},
        art = {'thumb': channel.get('logo'), 'fanart': channel.get('fanart')},
        proxy_data = {'cert': channel.get('cert')},
    )

    manifest = channel.get('manifest', 'hls')

    if manifest == 'mpd':
        item.inputstream = inputstream.MPD()
    elif manifest == 'hls' and channel.get('hls', True):
        item.inputstream = inputstream.HLS(live=True)

    return item

@cached(60*5)
def get_channels():
    return Session().gz_json(M3U8_URL)

@plugin.route()
@plugin.merge()
def playlist(output, **kwargs):
    channels = get_channels()
    hide_fast = settings.getBool('hide_fast_channels', False)

    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'#EXTM3U x-tvg-url="{}"'.format(EPG_URL))

        for slug in sorted(channels, key=lambda k: (float(channels[k].get('chno', 'inf')), channels[k]['name'])):
            channel = channels[slug]
            if hide_fast and not channel.get('chno'):
                continue

            f.write(u'\n#EXTINF:-1 channel-id="{channel_id}" tvg-id="{epg_id}" tvg-chno="{chno}" tvg-logo="{logo}",{name}\n{url}'.format(
                channel_id=slug, epg_id=channel.get('epg_id', slug), logo=channel.get('logo', ''), name=channel['name'], chno=channel.get('chno', ''),
                    url=plugin.url_for(play, slug=slug, _is_live=True)))
