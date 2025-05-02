import re
import json

from kodi_six import xbmc
from slyguy.session import Session
from slyguy import plugin, gui, inputstream

from .constants import IMDB_API_URL, IMDB_API_HEADERS, IMDB_VIDEO_URL, IMDB_QUALITY_MAP


def get_trailer(imdb_id):
    session = Session(headers=IMDB_API_HEADERS)

    variables = {'id': imdb_id}
    query = 'query($id: ID!){title(id:$id){latestTrailer{id}}}'
    payload = {'query': query, 'variables': variables}
    data = session.post(IMDB_API_URL, json=payload).json()

    try:
        url = IMDB_VIDEO_URL.format(data['data']['title']['latestTrailer']['id'])
    except KeyError:
        return

    page = session.get(url).text
    r = re.search(r'application/json">([^<]+)', page)
    if not r:
        return

    data = json.loads(r.group(1))
    details = data.get('props', {}).get('pageProps', {}).get('videoPlaybackData', {}).get('video')
    return {i.get('videoDefinition'): i.get('url') for i in details.get('playbackURLs') if i.get('videoMimeType') in ('M3U8', 'MP4')}


def play_imdb(imdb_id):
    videos = get_trailer(imdb_id)
    if not videos:
        gui.notification(_.TRAILER_NOT_FOUND)
        return

    item = plugin.Item()
    if 'DEF_AUTO' in videos:
        item.update(
            path = videos['DEF_AUTO'],
            headers = IMDB_API_HEADERS,
            inputstream = inputstream.HLS(),
        )
    else:
        item.update(
            path = 'special://temp/imdb.m3u8',
            headers = IMDB_API_HEADERS,
            proxy_data = {'custom_quality': True},
        )
        with open(xbmc.translatePath(item.path), 'w') as f:
            f.write('#EXTM3U\n#EXT-X-VERSION:3\n')
            for defintion in videos:
                f.write('\n#EXT-X-STREAM-INF:RESOLUTION={},CODECS=avc\n{}'.format(IMDB_QUALITY_MAP.get(defintion, ''), videos[defintion]))

    return item
