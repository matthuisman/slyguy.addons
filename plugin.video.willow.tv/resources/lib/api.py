import hashlib

from slyguy import userdata
from slyguy.session import Session
from slyguy.exceptions import Error
from slyguy.mem_cache import cached

from .constants import *
from .language import _

class APIError(Error):
    pass

class API(object):
    def new_session(self):
        self._session  = Session(HEADERS)
        self.logged_in = userdata.get('userid') != None

    def login(self, username, password):
        self.logout()

        payload = {
            'action': 'login',
            'email': username,
            'password': password,
            'authToken': hashlib.md5('{}::{}::{}'.format(MD5_KEY, username, password).encode('utf8')).hexdigest(),
        }

        data = self._session.post(LOGIN_URL, data=payload).json()

        if data['result']['status'] != 'success':
            raise APIError(_(_.LOGIN_ERROR, msg=data['result'].get('message')))
        
        userdata.set('userid', data['result']['userId'])

    @cached(60*5)
    def _get_explore_data(self):
        return self._session.get(EXPLORE_URL).json()

    def _explore_path(self, name):
        data = self._get_explore_data()
        for row in data['result']['rows']:
            if row['title'].lower().strip() == name.lower().strip():
                return row['items']
        raise APIError("unable to find content for {}".format(name))

    def live_matches(self):
        return self._explore_path('live now')

    @cached(60*10)
    def played_series(self):
        return self._session.get(ARCHIVE_URL).json()

    @cached(60*10)
    def match(self, match_id):
        return self._session.get(ARCHIVES_MATCH_URL.format(match_id=match_id)).json()

    def upcoming_matches(self):
        return self._session.get(UPCOMING_URL).json()

    def get_series(self, series_id):
        data = self.played_series()

        for row in data['vod']:
            if row['sid'] == series_id:
                return row

        return None

    def play_live(self, match_id, priority):
        payload = {
            'mid': match_id,
            'type': 'live',
            'devType': DEV_TYPE,
            'pr': priority,
            'wuid': userdata.get('userid'),
        }

        return self.play(payload)

    def play_replay(self, match_id, content_id):
        payload = {
            'mid': match_id,
            'type': 'replay',
            'devType': DEV_TYPE,
            'title': content_id,
            'wuid': userdata.get('userid'),
        }

        return self.play(payload)

    def play_highlight(self, match_id, content_id):
        payload = {
            'mid': match_id,
            'type': 'highlight',
            'devType': DEV_TYPE,
            'id': content_id,
            'wuid': userdata.get('userid'),
        }

        return self.play(payload)

    def play(self, payload):
        data = self._session.post(PLAYBACK_URL, data=payload).json()   

        if 'error' in data:
            raise APIError(_(_.PLAYBACK_ERROR, msg=data['error'].get('title')))
        elif 'subscribe' in data:
            raise APIError(_(_.SUBSCRIBE_ERROR, msg=data['subscribe'].get('description')))
        elif not data.get('Videos'):
            raise APIError(_.NO_VIDEOS)

        return data['Videos'][0]['Url']

    def logout(self):
        userdata.delete('userid')
        self.new_session()