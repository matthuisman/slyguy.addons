import time
import hashlib

from slyguy import userdata, util
from slyguy.session import Session
from slyguy.exceptions import Error
from slyguy.util import jwt_data
from slyguy.drm import widevine_level

from .constants import API_URL, HEADERS, BRIGHTCOVE_URL, BRIGHTCOVE_ACCOUNT, BRIGHTCOVE_KEY
from . import queries

class APIError(Error):
    pass

class API(object):
    def new_session(self):
        self.logged_in = False

        self._session = Session(HEADERS)
        self._set_authentication()

    def _set_authentication(self):
        token = userdata.get('jwt_token')
        if not token:
            return

        self._session.headers.update({'Authorization': 'Bearer {}'.format(token)})
        self.logged_in = True

    def _device_info(self, username):
        return {
            'uuid': hashlib.sha1(username.encode('utf8')).hexdigest(),
            'name': 'NVIDIA Shield TV',
            'platform': 'AndroidTV',
        }

    def _query_request(self, query, variables=None, **kwargs):
        data = {
            'query': ' '.join(query.split()),
            'variables': variables or {},
        }

        return self._session.post(API_URL, json=data, **kwargs).json()

    def _set_token(self, jwt_token):
        userdata.set('jwt_token', jwt_token)
        data = jwt_data(jwt_token)
        userdata.set('expires', data['exp'] - 2592000)
        self._set_authentication()

    def login(self, username, password):
        self.logout()

        variables = {
            'input': {
                'deviceInfo': self._device_info(username),
            },
            'username': username,
            'password': password,
        }

        data = self._query_request(queries.LOGIN, variables)
        if data.get('errors'):
            raise APIError(data['errors'][0].get('message'))

        self._set_token(data['data']['login']['session']['token'])

    def content(self, screen_id):
        self._check_token()

        variables = {
            'screenId': screen_id,
        }

        return self._query_request(queries.CONTENT, variables)['data']['screen']

    def _check_token(self):
        if time.time() < userdata.get('expires', 0):
            return

        self.set_profile(userdata.get('profile_id'))

    def account(self):
        self._check_token()

        return self._query_request(queries.ACCOUNT)['data']['account']

    def set_profile(self, profile_id):
        variables = {
            'input': {
                'selectedProfile': profile_id,
            },
            'pin': None,
        }

        data = self._query_request(queries.UPDATE_ACCOUNT, variables)['data']['account']
        self._set_token(data['session']['token'])

        for row in data['profiles']:
            if row['id'] == data['selectedProfile']:
                userdata.set('profile_id', row['id'])
                userdata.set('profile_name', row['name'])
                userdata.set('profile_icon', row['avatar']['uri'])
                userdata.set('profile_kids', row['isKid'])
                return

        raise APIError(_.PROFILE_SET_ERROR)

    def search(self, query):
        self._check_token()

        variables = {
            'input': {
                'query': query,
            },
        }

        data = self._query_request(queries.SEARCH, variables)['data']['search']['components']

        results = []
        for row in data:
            results.extend(row['tiles'])

        return results

    def playback_auth(self, contentID):
        self._check_token()

        variables = {
            'contentItemId': contentID,
            'drmLevel': 'WIDEVINE_{}'.format(widevine_level()),
            'os': 'Android_TV',
            'osVersion': "2021",
            'preferredResolution': 'HD',
            'format': 'HD',
            # 'bitrates': {
            #     'lowestBitrate': 1000000,
            #     'SDBitrate': 1000000,
            #     'HDBitrate': 1000000,
            # }
        }

        return self._query_request(queries.PLAYBACK_AUTH, variables)

    def get_brightcove_src(self, referenceID, jwt_token):
        brightcove_url = BRIGHTCOVE_URL.format(BRIGHTCOVE_ACCOUNT, referenceID, jwt_token)
        data = self._session.get(brightcove_url, headers={'BCOV-POLICY': BRIGHTCOVE_KEY}).json()
        return util.process_brightcove(data)

    def logout(self):
        userdata.delete('jwt_token')
        userdata.delete('expires')
        userdata.delete('profile_id')
        userdata.delete('profile_name')
        userdata.delete('profile_icon')
        userdata.delete('profile_kids')
        self.new_session()
