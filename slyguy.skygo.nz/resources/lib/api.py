from time import time

import arrow

from slyguy import userdata, mem_cache
from slyguy.session import Session
from slyguy.log import log
from slyguy.exceptions import Error
from slyguy.util import jwt_data

from .language import _
from .settings import HEADERS, CLIENT_ID, GRAPH_URL
from . import queries


class APIError(Error):
    pass


class API(object):
    def new_session(self):
        self.logged_in = False
        self._session = Session(HEADERS)
        self._set_authentication()

    def _set_authentication(self):
        token = userdata.get('access_token')
        if not token:
            return

        self._session.headers.update({'authorization': 'Bearer {}'.format(token)})
        self._session.headers.update({'x-user-profile': userdata.get('profile_id')})
        self.logged_in = True

    def _query_request(self, query, variables=None, operation_name=None, **kwargs):
        self._refresh_token()

        data = {
            'query': ' '.join(query.split()),
            'variables': variables or {},
        }
        if operation_name:
            data['operationName'] = operation_name

        data = self._session.post(GRAPH_URL, json=data, **kwargs).json()
        if 'errors' in data:
            raise APIError(data['errors'][0]['message'])

        return data

    def _refresh_token(self, force=False):
        if not force and userdata.get('expires', 0) > time() or not self.logged_in:
            return

        log.debug('Refreshing token')

        payload = {
            'client_id': CLIENT_ID,
            'refresh_token': userdata.get('refresh_token'),
            'grant_type': 'refresh_token',
            'scope': 'openid profile email offline_access',
        }

        self._oauth_token(payload)

    def account(self):
        return self._query_request(queries.ACCOUNT, operation_name='CustomerDetails', headers={'x-user-profile': None})['data']['customer']

    def _oauth_token(self, payload):
        token_data = self._session.post('https://login.sky.co.nz/oauth/token', json=payload, error_msg=_.TOKEN_ERROR).json()

        if 'error' in token_data:
            self.logout()
            error = _.REFRESH_TOKEN_ERROR if token_data.get('grant_type') == 'refresh_token' else _.LOGIN_ERROR
            raise APIError(_(error, msg=token_data.get('error_description')))

        userdata.set('access_token', token_data['access_token'])
        userdata.set('expires', int(time() + token_data['expires_in'] - 15))
        if 'refresh_token' in token_data:
            userdata.set('refresh_token', token_data['refresh_token'])

        self._set_authentication()

    def login(self, username, password):
        self.logout()

        payload = {
            'username': username,
            'password': password,
            'scope': 'openid email profile offline_access',
            'audience': 'https://api.sky.co.nz',
            'grant_type': 'password',
            'client_id': CLIENT_ID,
        }

        self._oauth_token(payload)

    @mem_cache.cached(60*5)
    def home(self):
        return self._query_request(queries.HOME)['data']['section']['home']

    @mem_cache.cached(60*5)
    def group(self, id):
        return self._query_request(queries.GROUP, variables={'railId': id})['data']['group']

    @mem_cache.cached(60*5)
    def channels(self, subscribed_only=True):
        ids = []
        channels = []

        variables = {
            'from': arrow.utcnow().format('YYYY-MM-DDTHH:mm:ss.000')+'Z',
            'to': arrow.utcnow().shift(hours=6).format('YYYY-MM-DDTHH:mm:ss.000')+'Z',
        }

        groups = self._query_request(queries.CHANNELS, variables=variables)['data']['linearChannelGroups']
        for group in groups:
            for row in group.get('channels', []):
                if row['__typename'] == 'LinearChannel' and row['id'] not in ids:
                    if subscribed_only and not row.get('mySchedule'):
                        continue
                    ids.append(row['id'])
                    channels.append(row)

        return sorted(channels, key=lambda x: x['number'])

    @mem_cache.cached(60*5)
    def search(self, query):
        return self._query_request(queries.SEARCH, variables={'term': query})['data']['search']['results']

    @mem_cache.cached(60*5)
    def show(self, id):
        return self._query_request(queries.SHOW, variables={'brandId': id})['data']['show']

    @mem_cache.cached(60*5)
    def collection(self, collection_id, filters="", limit=36, after=None, sort="ALPHABETICAL", tv_upcoming=False):
        context = 'VOD,CATCHUP'
        if tv_upcoming:
            context += ',LINEAR'

        filters = 'namedFilters: "{}"'.format(filters) if filters else ''
        limit = 'first: {}'.format(limit) if limit else ''
        sort = 'sort: {}'.format(sort) if sort else ''
        after = 'after: "{}"'.format(after) if after else ''

        query = queries.COLLECTION % (after, limit, context, filters, sort)

        return self._query_request(query, variables={'collectionId': collection_id})['data']['collection']

    @mem_cache.cached(60*10)
    def vod_categories(self):
        return self._query_request(queries.VOD_CATEGORIES, variables={'excludeViewingContexts': ['DOWNLOAD',]})['data']['section']['home']['categories']

    def play(self, asset_id, is_linear=False):
        variables = {
            'deviceId': '',
            'assetId': asset_id,
            'channelId': asset_id,
            # 'playbackDevice': {
            #     'platform': 'Windows',
            #     'osVersion': '10',
            #     'drmType': 'WIDEVINE',
            #     'drmLevel': 'SW_SECURE_DECODE'
            # }
        }

        if is_linear:
            data = self._query_request(queries.LINEAR_START, variables)['data']['startLinearPlayback']
        else:
            data = self._query_request(queries.VOD_START, variables)['data']['startVodPlayback']

        if data['__typename'] == 'SubscriptionNeeded':
            raise APIError(_(_.SUBSCRIPTION_REQUIRED, subscription=data['subscriptions'][0]['title']))
        elif data['__typename'] == 'Geoblocked':
            raise APIError(_.GEO_ERROR)
        elif data['__typename'] == 'ConcurrentStreamsExceeded':
            raise APIError(_.CONCURRENT_STREAMS)
        elif data['__typename'] not in ('LinearPlaybackSources', 'VodPlaybackSources'):
            raise APIError('Unkown error: {}'.format(data['__typename']))

        try:
            if is_linear:
                self._query_request(queries.LINEAR_STOP, variables)['data']['stopLinearPlayback']
            else:
                self._query_request(queries.VOD_STOP, variables)['data']['stopVodPlayback']
        except:
            log.debug('Stop Linear / VOD Failed')

        return data['playbackSource']['streamUri'], data['playbackSource']['drmLicense']['licenseUri']

    def logout(self):
        userdata.delete('access_token')
        userdata.delete('refresh_token')
        userdata.delete('expires')
        userdata.delete('profile_id')
        mem_cache.empty()
        self.new_session()
