import codecs

from slyguy import plugin
from slyguy.mem_cache import cached
from slyguy.session import Session
from slyguy.constants import QUALITY_DISABLED

from .settings import settings, DATA_URL
from .language import _


session = Session()


@plugin.route('')
def home(**kwargs):
    if not settings.getBool('bookmarks', True):
        return _stations()

    folder = plugin.Folder(cacheToDisc=False)
    folder.add_item(label=_(_.STATIONS, _bold=True), path=plugin.url_for(stations))
    folder.add_item(label=_(_.BOOKMARKS, _bold=True), path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)
    folder.add_item(label=_.SETTINGS,  path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)
    return folder


@plugin.route()
def stations(**kwargs):
    return _stations()


def _stations():
    folder = plugin.Folder(_.STATIONS)

    channels = get_channels()
    for slug in sorted(channels, key=lambda k: channels[k]['name']):
        channel = channels[slug]

        folder.add_item(
            label = channel['name'],
            path = plugin.url_for(play, slug=slug, _is_live=True),
            info = {'plot': channel.get('description')},
            art = {'thumb': channel.get('logo'), 'fanart': channel.get('fanart')},
            playable = True,
        )

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
        quality = QUALITY_DISABLED,
    )

    return item


@cached(60*5)
def get_channels():
    return session.gz_json(DATA_URL)

@plugin.route()
@plugin.merge()
def playlist(output, **kwargs):
    channels = get_channels()

    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'#EXTM3U\n')

        for slug in sorted(channels, key=lambda k: channels[k]['name']):
            channel = channels[slug]

            f.write(u'#EXTINF:-1 tvg-id="{id}" tvg-chno="{chno}" tvg-logo="{logo}" radio="true",{name}\n{path}\n'.format(
                id=slug, logo=channel.get('logo', ''), name=channel['name'], chno=channel.get('chno', ''),
                    path=plugin.url_for(play, slug=slug, _is_live=True)))
