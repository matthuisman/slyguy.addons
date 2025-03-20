from slyguy import plugin, _
from slyguy.log import log
from slyguy.yt import play_yt


@plugin.route('/')
def home(**kwargs):
    if kwargs.get('action') == 'play_video':
        return plugin.redirect(plugin.url_for(play, video_id=kwargs.get('videoid')))

    folder = plugin.Folder()
    folder.add_item(label='TEST 4K', info={'trailer': plugin.url_for(play, video_id='Q82tQJyJwgk')}, playable=True, path=plugin.url_for(play, video_id='Q82tQJyJwgk'))
    folder.add_item(label='TEST 4K HDR', playable=True, path=plugin.url_for(play, video_id='tO01J-M3g0U'))
    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)
    return folder


@plugin.route('/play')
def play(video_id, **kwargs):
    return play_yt(video_id)


# stub out search so tmdbhelper works
@plugin.route('/search')
@plugin.route('/kodion/search/query')
def search(**kwargs):
    log.warning("Youtube for Trailers does not support search ({}). Returning empty result".format(kwargs['_url']))
    return plugin.Folder(no_items_label=None, show_news=False)
