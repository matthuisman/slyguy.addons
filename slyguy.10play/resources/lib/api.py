from slyguy import settings, mem_cache
from slyguy.session import Session
from slyguy.exceptions import Error

from .constants import *
from .language import _

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
        url = url.replace('[ids]', ','.join(str(x) for x in video_ids)).replace('[state]', STATES[settings.getInt('state')])

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
        url = self._config()['LiveTV']['Livestream_schedule'].format(
            state = STATES[settings.getInt('state')],
            channel = 'all',
        )

        return self._session.get(url).json()

    def play(self, id):
        data = self.videos([id])[0]
        return data['HLSURL']

    def play_channel(self, id):
        url = self._config()['LiveTV']['Livestream_endpoint'].format(
            state = STATES[settings.getInt('state')],
            channel = id,
        )

        return self._session.get(url).json()[0]['HLSURL']
