import codecs

import arrow
from slyguy import plugin, inputstream
from slyguy.session import Session
from slyguy.mem_cache import cached

from .language import _
from .settings import settings, ChannelMode, DATA_URL, EPG_URL


@plugin.route('')
def home(**kwargs):
    folder = plugin.Folder(cacheToDisc=False)

    folder.add_item(label=_(_.LIVE_TV, _bold=True), path=plugin.url_for(live_tv))
    if settings.getBool('bookmarks', True):
        folder.add_item(label=_(_.BOOKMARKS, _bold=True), path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)
    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), bookmark=False)

    return folder


@plugin.route()
def live_tv(**kwargs):
    folder = plugin.Folder(_.LIVE_TV)
    show_chnos = settings.getBool('show_chnos', True)

    if settings.getBool('show_epg', True):
        now = arrow.now()
        epg_count = 5
    else:
        epg_count = None

    for channel in get_channels():
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

        item = plugin.Item(
            label = channel['name'],
            path = plugin.url_for(play, slug=channel['slug'], _is_live=True),
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
    channel = get_channels(slug)

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


def get_channels(slug=None):
    @cached(60*5)
    def get_data():
        return Session().gz_json(DATA_URL)

    channels = get_data()
    if slug:
        return channels[slug]

    channel_list = []
    for slug in sorted(channels, key=lambda k: (float(channels[k].get('chno', 'inf')), channels[k]['name'])):
        channel = channels[slug]
        channel['slug'] = slug

        if settings.CHANNEL_MODE.value == ChannelMode.FREEVIEW_ONLY and not channel.get('chno'):
            continue
        elif settings.CHANNEL_MODE.value == ChannelMode.FAST_ONLY and channel.get('chno'):
            continue

        if channel.get('epg_id') and not channel.get('programs'):
            channel['programs'] = channels.get(channel['epg_id'], {}).get('programs', [])

        channel_list.append(channel)

    return channel_list


@plugin.route()
@plugin.merge()
def playlist(output, **kwargs):
    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'#EXTM3U x-tvg-url="{}"'.format(EPG_URL))

        for channel in get_channels():
            f.write(u'\n#EXTINF:-1 channel-id="{channel_id}" tvg-id="{epg_id}" tvg-chno="{chno}" tvg-logo="{logo}",{name}\n{url}'.format(
                channel_id=channel['slug'], epg_id=channel.get('epg_id', channel['slug']), logo=channel.get('logo', ''), name=channel['name'], chno=channel.get('chno', ''),
                    url=plugin.url_for(play, slug=channel['slug'], _is_live=True)))
