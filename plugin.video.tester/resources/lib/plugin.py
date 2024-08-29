from slyguy import plugin, inputstream
from slyguy.language import _

from .constants import VIDEO_TESTS


@plugin.route('')
def home(**kwargs):
    folder = plugin.Folder()

    for index, video in enumerate(VIDEO_TESTS):
        folder.add_item(
            label = video['name'],
            path = plugin.url_for(play_video, index=index),
            playable = True,
        )

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), bookmark=False)
    return folder


@plugin.route()
def play_video(index, **kwargs):
    video = VIDEO_TESTS[int(index)]

    item = plugin.Item(
        path = video['url'],
    )

    if video['type'] == 'ia_hls':
        item.inputstream = inputstream.HLS(force=True, live=False)
    elif video['type'] == 'ia_widevine_hls':
        item.inputstream = inputstream.Widevine(video.get('license_key'), manifest_type='hls')
    elif video['type'] == 'ia_mpd':
        item.inputstream = inputstream.MPD()
    elif video['type'] == 'ia_widevine':
        item.inputstream = inputstream.Widevine(video.get('license_key'))

    return item
