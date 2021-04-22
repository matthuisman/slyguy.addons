from slyguy import userdata, inputstream, plugin
from slyguy.session import Session
from slyguy.exceptions import Error

from .constants import HEADERS, BASE_URL
from .language import _

class APIError(Error):
    pass

class API(object):
    def new_session(self):
        self.logged_in = False

        self._session = Session(HEADERS, base_url=BASE_URL)
        self.set_authentication()

    def set_authentication(self):
        token = userdata.get('auth_token')
        if not token:
            return

        self._session.headers.update({'x-auth-token': token})
        self.logged_in = True

    def login(self, username, password):
        self.logout()

        data = {'user': {
            'email': username, 
            'password': password, 
            'remember_me': True
        }}

        data = self._session.post('/services/users/auth/sign_in', json=data).json()
        if 'error' in data:
            raise APIError(data['error'])

        auth_token = data['auth_token']
        user_id = data['account']['user_id']

        userdata.set('auth_token', auth_token)
        userdata.set('user_id', user_id)

        self.set_authentication()

    def my_library(self):
        meta = {}

        items = self._session.get('/services/content/v3/user_library/{}/index'.format(userdata.get('user_id')), params={'sort_by': 'relevance'}).json()
        _meta = self._session.get('/services/meta/v2/film/{}/show_multiple'.format(','.join(str(x['info']['film_id']) for x in items))).json()
        for item in _meta:
            meta[item['film_id']] = item

        for item in items:
            item['meta'] = meta.get(item['info']['film_id'], {})

        return items

    def get_stream(self, film_id):
        play_data = self._session.get('/services/content/v4/media_content/play/film/{}'.format(film_id), params={'encoding_type':'dash', 'drm':'widevine'}).json()
        if 'error' in play_data:
            raise APIError(play_data['error'])

        mpd_url = play_data['streams'][0]['url']
        key_url = BASE_URL.format('/services/license/widevine/cenc?context={}'.format(play_data['streams'][0]['drm_key_encoded'].strip()))

        item = plugin.Item(
            path = play_data['streams'][0]['url'],
            inputstream = inputstream.Widevine(license_key=key_url),
            headers = self._session.headers,
        )

        return item

    def logout(self):
        userdata.delete('auth_token')
        userdata.delete('user_id')
        self.new_session()