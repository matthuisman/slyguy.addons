from time import time, sleep

from slyguy import userdata, mem_cache
from slyguy.log import log
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
        self._set_auth(userdata.get('key'))

    def _set_auth(self, key):
        if not key:
            return

        self._session.headers.update({'Authorization': 'Token {}'.format(key)})
        self.logged_in = True

    def login(self, username, password):
        try:
            payload = {
                'email': username,
                'password': password,
            }

            data = self._session.post('https://api.watchnebula.com/api/v1/auth/login/', json=payload).json()
            key = data.get('key')

            if not key:
                msg = data['non_field_errors'][0]
                raise APIError(msg)

            userdata.set('key', key)
            self._set_auth(key)

            data = self._session.get('https://api.watchnebula.com/api/v1/auth/user/', params={'from': 'Android'}, json={}).json()
            userdata.set('user_id', data['zobject_user_id'])

            self._token(force=True)
        except:
            self.logout()
            raise

    def _token(self, force=False):
        token = userdata.get('token')
        if not self.logged_in or (not force and userdata.get('expires', 0) > time()):
            return token

        log.debug('Refreshing token')

        data = self._session.get('https://api.watchnebula.com/api/v1/zype/auth-info/', params={'from': 'Android'}, json={}).json()
        if 'access_token' not in data:
            self._session.post('https://api.watchnebula.com/api/v1/zype/auth-info/new/', json={})

            for i in range(5):
                sleep(1)
                data = self._session.get('https://api.watchnebula.com/api/v1/zype/auth-info/', params={'from': 'Android'}, json={}).json()
                if 'access_token' in data:
                    break

        if data.get('detail'):
            self.logout()
            raise APIError('Unable to refresh token')

        userdata.set('token', data['access_token'])
        userdata.set('expires', data['expires_at'] - 30)
        # if 'refresh_token' in data:
        #     userdata.set('refresh_token', data['refresh_token'])

        return data['access_token']

    @mem_cache.cached(expires=60*5)
    def categories(self):
        params = {
            'access_token': self._token(),
        }

        data = self._session.get('https://api.zype.com/playlists/relationships', params=params).json()['playlists']

        categories = [{'id': None, 'title': _.EVERYTHING}]
        for row in data:
            if not row['active'] or not row['priority'] == 0:
                continue

            for playlist in sorted(row['playlists'], key=lambda x: x['priority']):
                categories.append({'id': playlist['id'], 'title': playlist['title']})

        return categories

    def featured(self, feature_type):
        params = {
            'zobject_type': 'featured',
            'feature_type': feature_type,
            'page': 1,
            'per_page': 500,
            'sort': 'order',
            'access_token': self._token(),
        }

        return self._session.get('https://api.zype.com/zobjects', params=params).json()['response']

    def collections(self):
        params = {
            'zobject_type': 'collection',
            'page': 1,
            'per_page': 500,
            'sort': 'order',
            'access_token': self._token(),
        }

        return self._session.get('https://api.zype.com/zobjects', params=params).json()['response']

    def following(self):
        params = {
            'zobject_type': 'following',
            'user': userdata.get('user_id'),
            'page': 1,
            'per_page': 500,
            'sort': 'title',
            'access_token': self._token(),
        }

        return self._session.get('https://api.zype.com/zobjects', params=params).json()['response']

    @mem_cache.cached(expires=60*5)
    def creators(self, query=None):
        params = {
            'zobject_type': 'channel',
            'page': 1,
            'per_page': 500,
            'sort': 'title',
            'access_token': self._token(),
        }

        if query:
            params['q'] = query

        return self._session.get('https://api.zype.com/zobjects', params=params).json()['response']

    def follow_creator(self, creator_id):
        payload = {
            'channel_id': creator_id,
        }

        self._session.post('https://api.watchnebula.com/api/v1/zype/follow/', json=payload).json()

    def unfollow_creator(self, creator_id):
        payload = {
            'channel_id': creator_id,
        }

        self._session.post('https://api.watchnebula.com/api/v1/zype/unfollow/', json=payload).json()

    def videos(self, playlist_id=None, page=1, items_per_page=100, query=None):
        params = {
            'page': page,
            'per_page': items_per_page,
            'sort': 'published_at',
            'order': 'desc',
            'access_token': self._token(),
        }

        if playlist_id:
            params['playlist_id.inclusive'] = playlist_id

        if query:
            params['q'] = query

        return self._session.get('https://api.zype.com/videos', params=params).json()

    def play(self, video_id):
        params = {
            'access_token': self._token(),
        }

        data = self._session.get('https://player.zype.com/embed/{video_id}'.format(video_id=video_id), params=params).json()

        return data['response']['body']['outputs'][0]['url']

    def logout(self):
        userdata.delete('key')
        userdata.delete('token')
        userdata.delete('expires')
        userdata.delete('user_id')
        self.new_session()

    # @mem_cache.cached(expires=60*5)
    # def playlists(self):
    #     params = {
    #         'active': True,
    #         'page': 1,
    #         'per_page': 500,
    #         'access_token': self._token(),
    #     }

    #     return self._session.get('https://api.zype.com/playlists', params=params).json()['response']:

    # @mem_cache.cached(expires=60*5)
    # def podcasts(self):
    #     params = {
    #         'zobject_type': 'podcast',
    #         'page': 1,
    #         'per_page': 500,
    #         'sort': 'title',
    #         'access_token': self._token(),
    #     }

    #     return self._session.get('https://api.zype.com/zobjects', params=params).json()['response']