import codecs

from slyguy import plugin, inputstream, mem_cache, settings
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

def _channels():
    @mem_cache.cached(60*5)
    def fetch_channels(region):
        return Session().gz_json(DATA_URL.format(region=region))

    region = settings.getEnum('region', REGIONS, default=ALL)
    return fetch_channels(region)

@plugin.route()
def live_tv(**kwargs):
    folder = plugin.Folder(_.LIVE_TV)

    channels = _channels()
    for id in sorted(channels.keys(), key=lambda x: channels[x]['chno']):
        channel = channels[id]
        
        folder.add_item(
            label = _(_.CH_LABEL, chno=channel['chno'], name=channel['name']),
            info = {'plot': channel['description']},
            art = {'thumb': channel['logo']},
            playable = True,
            path = plugin.url_for(play, id=id, _is_live=True),
        )

    return folder

@plugin.route()
def play(id, **kwargs):
    channel = _channels()[id]
    return plugin.Item(
        label = channel['name'],
        info = {'plot': channel['description']},
        art = {'thumb': channel['logo']},
        inputstream = inputstream.HLS(live=True),
        path = channel['url'],
    )

@plugin.route()
@plugin.merge()
def playlist(output, **kwargs):
    channels = _channels()
    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'#EXTM3U')

        for id in sorted(channels.keys(), key=lambda x: channels[x]['chno']):
            channel = channels[id]
            f.write(u'\n#EXTINF:-1 tvg-id="{id}" tvg-chno="{chno}" tvg-name="{name}" tvg-logo="{logo}" group-title="{group}",{name}\n{url}'.format(
                id=id, chno=channel['chno'], name=channel['name'], logo=channel['logo'], group=channel['group'], url=plugin.url_for(play, id=id, _is_live=True),
            ))

@plugin.route()
@plugin.merge()
def epg(output, **kwargs):
    epg_url = EPG_URL.format(region=settings.getEnum('region', REGIONS, default=ALL))
    Session().chunked_dl(epg_url, output)
    if epg_url.endswith('.gz'):
        gzip_extract(output)
