from slyguy import util, userdata
from slyguy.session import Session
from slyguy.exceptions import Error

from .constants import *
from .language import _

class APIError(Error):
    pass

class API(object):
    def new_session(self):
        self._session = Session(HEADERS)
        self.logged_in = userdata.get('access_token', None) is not None

    def login(self, username, password):
        payload = {
            'returnSecureToken': True,
            'email': username,
            'password': password,
            'clientType': 'CLIENT_TYPE_WEB',
        }

        data = self._session.post('https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword', params={'key': API_KEY}, json=payload).json()
        if 'error' in data:
            raise APIError(data['error']['message'])

        userdata.set('access_token', data['idToken'])
        self.new_session()

    def races(self, year=2023):
        params = {
            'q': '+tags:Superview +tags:{} -tags:delete -tags:test'.format(year),
            'limit': 100,
            'offset': 0,
            'sort': '-published_at',
        }

        data = self._session.get('https://edge.api.brightcove.com/playback/v1/accounts/2178772919001/videos',
            params = params,
            headers = {'accept': 'application/json;pk={}'.format(BRIGHTCOVE_KEY)}
        )

        return data.json()['videos']

    def play(self, id):
        return self.get_brightcove_src(id)

    def get_brightcove_src(self, referenceID):
        headers = {
            'User-Agent': 'Mozilla/5.0 (CrKey armv7l 1.5.16041) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.0 Safari/537.36',
            'Origin': 'https://www.supercars.com',
            'X-Forwarded-For': '18.233.21.73',
            'BCOV-POLICY': BRIGHTCOVE_KEY,
        }
        brightcove_url = BRIGHTCOVE_URL.format(referenceID)
        data = Session().get(brightcove_url, headers=headers).json()
        return util.process_brightcove(data)

    def logout(self):
        userdata.delete('access_token')
