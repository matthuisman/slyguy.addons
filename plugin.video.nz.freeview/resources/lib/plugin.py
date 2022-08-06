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

    if settings.getBool('show_epg', True):
        now = arrow.now()
        epg_count = 5
    else:
        epg_count = None

    channels = get_channels()
    for slug in sorted(channels, key=lambda k: (float(channels[k].get('channel', 'inf')), channels[k]['name'])):
        channel = channels[slug]

        plot = u''
        count = 0
        if epg_count:
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

        folder.add_item(
            label = channel['name'],
            path = plugin.url_for(play, slug=slug, _is_live=True),
            info = {'plot': plot},
            video = channel.get('video', {}),
            audio = channel.get('audio', {}),
            art = {'thumb': channel.get('logo')},
            playable = True,
        )

    return folder

@plugin.route()
def play(slug, **kwargs):
    channel = get_channels()[slug]
    url = Session().head(channel['mjh_master']).headers.get('location', '')

    item = plugin.Item(
        path = url or channel['mjh_master'],
        headers = channel['headers'],
        info = {'plot': channel.get('description')},
        video = channel.get('video', {}),
        audio = channel.get('audio', {}),
        art = {'thumb': channel.get('logo')},
        proxy_data = {'cert': channel.get('cert')},
    )

    if channel.get('hls', True):
        item.inputstream = inputstream.HLS(live=True)

    return item

def get_channels():
    url = M3U8_URL
    if settings.getBool('use_new', False):
        url = url.lower().replace('i.mjh.nz', 'new.mjh.nz')
    return get_url_channels(url)

@cached(60*5)
def get_url_channels(url):
    return Session().gz_json(url)

@plugin.route()
@plugin.merge()
def playlist(output, **kwargs):
    channels = get_channels()

    url = EPG_URL
    if settings.getBool('use_new', False):
        url = url.lower().replace('i.mjh.nz', 'new.mjh.nz')

    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'#EXTM3U x-tvg-url="{}"'.format(url))

        for slug in sorted(channels, key=lambda k: (float(channels[k].get('channel', 'inf')), channels[k]['name'])):
            channel = channels[slug]

            f.write(u'\n#EXTINF:-1 tvg-id="{id}" tvg-chno="{chno}" tvg-logo="{logo}",{name}\n{url}'.format(
                id=slug, logo=channel.get('logo', ''), name=channel['name'], chno=channel.get('channel', ''),
                    url=plugin.url_for(play, slug=slug, _is_live=True)))
