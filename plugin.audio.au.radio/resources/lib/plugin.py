import codecs

from slyguy import plugin, settings
from slyguy.session import Session
from slyguy.mem_cache import cached

from .constants import DATA_URL, REGIONS
from .language import _

session = Session()

@plugin.route('')
def home(**kwargs):
    folder = plugin.Folder(cacheToDisc=False)

    folder.add_item(label=_(_.STATIONS, _bold=True), path=plugin.url_for(stations))

    if settings.getBool('bookmarks', True):
        folder.add_item(label=_(_.BOOKMARKS, _bold=True), path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

    folder.add_item(label=_.SETTINGS,  path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder


@plugin.route()
def stations(**kwargs):
    region = get_region()
    folder = plugin.Folder(_(_.REGIONS[region]))

    channels = get_channels(region)
    for slug in sorted(channels, key=lambda k: channels[k]['name']):
        channel = channels[slug]

        folder.add_item(
            label    = channel['name'],
            path     = plugin.url_for(play, slug=slug, _is_live=True),
            info     = {'plot': channel.get('description')},
            video    = channel.get('video', {}),
            audio    = channel.get('audio', {}),
            art      = {'thumb': channel.get('logo')},
            playable = True,
        )

    return folder

@plugin.route()
def play(slug, **kwargs):
    region  = get_region()
    channel = get_channels(region)[slug]
    url = session.get(channel['mjh_master'], allow_redirects=False).headers.get('location', '')

    item = plugin.Item(
        path     = url,
        headers  = channel['headers'],
        info     = {'plot': channel.get('description')},
        video    = channel.get('video', {}),
        audio    = channel.get('audio', {}),
        art      = {'thumb': channel.get('logo')},
    )

    return item

@cached(60*5)
def get_channels(region):
    return session.gz_json(DATA_URL.format(region=region))

def get_region():
    return REGIONS[settings.getInt('region_index')]

@plugin.route()
@plugin.merge()
def playlist(output, **kwargs):
    region   = get_region()
    channels = get_channels(region)

    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'#EXTM3U\n')

        for slug in sorted(channels, key=lambda k: channels[k]['name']):
            channel = channels[slug]

            f.write(u'#EXTINF:-1 tvg-id="{id}" tvg-chno="{chno}" tvg-logo="{logo}" radio="true",{name}\n{path}\n'.format(
                id=slug, logo=channel.get('logo', ''), name=channel['name'], chno=channel.get('channel', ''),
                    path=plugin.url_for(play, slug=slug, _is_live=True)))