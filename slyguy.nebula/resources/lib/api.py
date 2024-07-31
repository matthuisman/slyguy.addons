from time import time

from slyguy import userdata, mem_cache
from slyguy.log import log
from slyguy.util import jwt_data
from slyguy.session import Session
from slyguy.exceptions import Error

from .settings import HEADERS, BASE_URL, PAGE_SIZE
from .language import _

class APIError(Error):
    pass

class API(object):
    def new_session(self):
        self.logged_in = False
        self._session = Session(headers=HEADERS, base_url=BASE_URL)
        self.logged_in = userdata.get('key', None) != None

        #LEGACY
        userdata.delete('token')
        userdata.delete('user_id')

    def _set_auth(self, token):
        self._session.headers.update({'Authorization': 'Bearer {}'.format(token)})

    def login(self, username, password):
        self.logout()

        payload = {
            'email': username,
            'password': password,
        }

        data = self._session.post('https://api.watchnebula.com/api/v1/auth/login/', json=payload).json()
        if 'key' not in data or not data['key']:
            msg = data['non_field_errors'][0]
            raise APIError(msg)

        userdata.set('key', data['key'])

    def _refresh_token(self, force=False):
        token = userdata.get('auth_token')
        if token and not force and userdata.get('expires', 0) > time():
            self._set_auth(token)
            return

        log.debug('Refreshing token' if token else 'Fetching token')

        key = userdata.get('key')
        data = self._session.post('https://api.watchnebula.com/api/v1/authorization/', params={'from': 'Android'}, json={}, headers={'Authorization': 'Token {}'.format(key)}).json()

        token = data['token']
        jwt = jwt_data(token)

        userdata.set('auth_token', token)
        userdata.set('expires', jwt['exp'] - 10)

        self._set_auth(token)

    @mem_cache.cached(expires=60*5)
    def categories(self):
        self._refresh_token()
        return self._session.get('/video/categories/').json()['results']

    @mem_cache.cached(expires=60*5)
    def podcast_categories(self):
        self._refresh_token()
        return self._session.get('/podcast/categories/').json()['results']

    @mem_cache.cached(expires=60*5)
    def podcast_creators(self, category='', page=1, page_size=PAGE_SIZE):
        self._refresh_token()

        params = {
            'page': page,
            'page_size': page_size,
        }

        if category:
            params['category'] = category

        return self._session.get('/podcast/channels/', params=params).json()

    @mem_cache.cached(expires=60*5)
    def podcasts(self, slug, page=1, page_size=PAGE_SIZE):
        self._refresh_token()

        params = {
            'page': page,
            'page_size': page_size,
        }

        return self._session.get('/podcast/channels/{slug}/'.format(slug=slug), params=params).json()

    @mem_cache.cached(expires=60*5)
    def search_videos(self, query, page=1, page_size=PAGE_SIZE):
        self._refresh_token()

        params = {
            'page': page,
            'page_size': page_size,
            'text': query,
        }

        return self._session.get('/search/video/', params=params).json()

    @mem_cache.cached(expires=60*5)
    def search_creators(self, query):
        self._refresh_token()

        params = {
            'text': query,
        }

        return self._session.get('/search/channel/video/', params=params).json()  

    @mem_cache.cached(expires=60*5)
    def search_podcasts(self, query):
        self._refresh_token()

        params = {
            'text': query,
        }

        return self._session.get('/search/channel/podcast/', params=params).json()  

    @mem_cache.cached(expires=60*5)
    def featured(self):
        self._refresh_token()
        return self._session.get('/featured/').json()

    @mem_cache.cached(expires=60*5)
    def videos(self, category='', page=1, page_size=PAGE_SIZE):
        self._refresh_token()

        params = {
            'page': page,
            'page_size': page_size,
        }

        if category:
            params['category'] = category

        return self._session.get('/video/', params=params).json()

    def my_videos(self, page=1, page_size=PAGE_SIZE):
        self._refresh_token()

        params = {
            'page': page,
            'page_size': page_size,
        }

        return self._session.get('/library/video/', params=params).json()

    def my_creators(self, page=1, page_size=PAGE_SIZE):
        self._refresh_token()

        params = {
            'page': page,
            'page_size': page_size,
        }

        return self._session.get('/library/video/channels/', params=params).json()

    @mem_cache.cached(expires=60*5)
    def creator(self, slug, page=1, page_size=PAGE_SIZE):
        self._refresh_token()

        params = {
            'page': page,
            'page_size': page_size,
        }

        return self._session.get('/video/channels/{slug}/'.format(slug=slug), params=params).json()

    @mem_cache.cached(expires=60*5)
    def creators(self, category='', page=1, page_size=PAGE_SIZE, random=False):
        self._refresh_token()

        params = {
            'page': page,
            'page_size': page_size,
        }

        if category:
            params['category'] = category

        if random:
            params['random'] = 'true'

        return self._session.get('/video/channels/', params=params).json()

    def follow_creator(self, slug):
        self._refresh_token()

        payload = {
            'channel_slug': slug,
        }

        if not self._session.post('/engagement/video/follow/', json=payload).ok:
            raise APIError('Failed to follow creator')

    def unfollow_creator(self, slug):
        self._refresh_token()

        payload = {
            'channel_slug': slug,
        }

        if not self._session.post('/engagement/video/unfollow/', json=payload).ok:
            raise APIError('Failed to unfollow creator')

    def play(self, slug):
        self._refresh_token()
        return self._session.get('/video/{slug}/stream/'.format(slug=slug)).json()

    def play_podcast(self, channel, episode):
        self._refresh_token()
        return self._session.get('/podcast/channels/{channel}/episodes/{episode}/'.format(channel=channel, episode=episode)).json()

    def logout(self):
        userdata.delete('key')
        userdata.delete('auth_token')
        userdata.delete('expires')
        mem_cache.empty()
        self.new_session()
