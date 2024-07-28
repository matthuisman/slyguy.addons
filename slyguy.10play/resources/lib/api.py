from slyguy import mem_cache
from slyguy.session import Session
from slyguy.exceptions import Error

from .constants import *
from .language import _
from .settings import settings


class APIError(Error):
    pass


class API(object):
    def new_session(self):
        self.logged_in = False
        self._session = Session(headers=HEADERS)

    @mem_cache.cached(60*10)
    def _config(self):
        return self._session.get(CONFIG_URL).json()

    def featured(self):
        return self._config()['Home']

    def shows(self):
        return self._config()['Browse TV']['Shows']

    def show(self, id):
        for row in self.shows():
            if row['id'] == id:
                return row
        raise APIError('Show not found')

    def videos(self, video_ids):
        config = self._config()
        url = config['endpoints']['videos']['server'] + config['endpoints']['videos']['methods']['getVideobyIDs']
        url = url.replace('[ids]', ','.join(str(x) for x in video_ids)).replace('[state]', self._get_state())
        return self._session.get(url).json()['items']

    def season(self, show_id, season_id):
        config = self._config()

        show = self.show(show_id)

        season = None
        for row in show['seasons']:
            if row['seasonId'] == season_id:
                season = row
                break

        if not season:
            raise APIError('Season not found')

        query = show['query'] + season['query']

        url = config['endpoints']['searchVideos']['server'] + query

        params = {
            'page_size': 999,
            'page_number': 0,
        }

        return show, self._session.get(url, params=params).json()['items']

    def live_channels(self):
        return self._session.get('https://10play.com.au/api/v1/live/{}'.format(self._get_state())).json()

    @mem_cache.cached(60*5)
    def state(self):
        return self._session.get('https://10play.com.au/geo-web').json()

    def _get_state(self):
        state = settings.STATE.value
        if not state:
            state = self.state()['state']
        return state

    def play(self, id):
        data = self.videos([id])[0]

        url = self._session.head(data['HLSURL'], allow_redirects=True).url
        if 'not-in-oz' in url.lower():
            # some ips dont work with 10-selector.global.ssl.fastly.net
            # user lower quality dai for them (like the website)
            if self.state()['allow'] and 'googleDaiVideoId' in data:
                return self._session.post('https://dai.google.com/ondemand/hls/content/{}/vid/{}/streams'.format(data['googleDaiCmsId'], data['googleDaiVideoId'])).json()['stream_manifest']
            else:
                return url

        new_url = url.replace(',150,',',300,150,')
        if self._session.head(new_url).ok:
            return new_url

        return url

    def play_channel(self, id):
        channels = self.live_channels()

        for row in channels:
            if row['channel']['id'] == id:
                return 'https://dai.google.com/ssai/event/{}/master.m3u8'.format(row['liveShow']['streamKey'])

        raise APIError('Failed to find stream key')
