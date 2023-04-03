import time
from six.moves.urllib_parse import urlencode

from slyguy import userdata
from slyguy.log import log
from slyguy.session import Session
from slyguy.exceptions import Error
from slyguy.util import jwt_data

from .language import _
from .constants import *

class APIError(Error):
    pass

class API(object):
    def new_session(self):
        self.logged_in = False
        self._session = Session(HEADERS, base_url=API_URL)
        self._set_authentication()

    def _set_authentication(self):
        auth_token = userdata.get('auth_token')
        if not auth_token:
            return

        self._session.headers.update({'Authorization': 'Bearer {}'.format(auth_token)})
        self.logged_in = True

    def device_code(self):
        return self._session.get('/v2/token/alt/pin').json()

    def device_login(self, pin, anchor):
        self.logout()

        payload = {
            'pin': pin,
            'anchor': anchor,
        }

        data = self._session.post('/v2/token/alt/pin', json=payload).json()
        return self._parse_auth(data)

    def login(self, username, password):
        self.logout()
        
        payload = {
            'id': username,
            'secret': password,
        }

        data = self._session.post('/v2/login', json=payload).json()
        if not self._parse_auth(data):
            raise APIError(_.LOGIN_ERROR)

    def _parse_auth(self, data):
        if not data.get('authorisationToken'):
            return False

        auth_token = data['authorisationToken']
        jwt = jwt_data(auth_token)

        userdata.set('auth_token', auth_token)
        userdata.set('token_expires', int(time.time()) + (jwt['exp'] - jwt['iat'] - 30))
        if 'refreshToken' in data:
            userdata.set('refresh_token', data['refreshToken'])

        self._set_authentication()
        return True

    def _refresh_token(self, force=False):
        if not force and userdata.get('token_expires', 0) > time.time():
            return

        log.debug('Refreshing token')

        payload = {
            'refreshToken': userdata.get('refresh_token'),
        }

        data = self._session.post('/v2/token/refresh', json=payload).json()
        self._check_errors(data)
        self._parse_auth(data)

    def page(self, content_id, last_seen=None):
        self._refresh_token()

        params = {
            'bpp': 10,
            'rpp': 1,
            'bspp': 1,
            'displaySectionLinkBuckets': 'SHOW',
            'displayEpgBuckets': 'HIDE',
            'displayEmptyBucketShortcuts': 'SHOW',
            'displayContentAvailableOnSignIn': 'SHOW',
            'displayGeoblocked': 'SHOW',
            'lastSeen': last_seen,
        }

        data = self._session.get('/v4/content/{}'.format(content_id), params=params).json()
        self._check_errors(data)
        if data['paging']['moreDataAvailable'] and data['paging']['lastSeen']:
            next_page = self.page(content_id, last_seen=data['paging']['lastSeen'])
            data['buckets'].extend(next_page['buckets'])

        return data

    def bucket(self, content_id, bucket_id, last_seen=None):
        self._refresh_token()

        params = {
            'rpp': 25,
            'displayContentAvailableOnSignIn': 'SHOW',
            'displayGeoblocked': 'SHOW',
            'lastSeen': last_seen,
        }
        data = self._session.get('/v4/content/{}/bucket/{}'.format(content_id, bucket_id), params=params).json()
        self._check_errors(data)
        return data

    def playlist(self, playlist_id, page=1):
        self._refresh_token()

        params = {
            'rpp': 25,
            'p': page,
            'displayGeoblocked': 'SHOW',
        }
        data = self._session.get('/v2/vod/playlist/{}'.format(playlist_id), params=params).json()
        self._check_errors(data)
        if data['videos']['totalPages'] > page:
            next_page = self.playlist(playlist_id, page+1)
            data['videos']['vods'].extend(next_page['videos']['vods'])

        return data

    def search(self, query, page=1):
        self._refresh_token()

        query_params = {
            'x-algolia-agent': 'Algolia for JavaScript (3.35.1); React Native',
            'x-algolia-application-id': 'H99XLDR8MJ',
            'x-algolia-api-key': 'e55ccb3db0399eabe2bfc37a0314c346',
        }

        payload_params = {
            'facets': [],
            'filters': 'type:VOD_VIDEO',
            'hitsPerPage': 20,
            'page': page,
            'query': query,
        }

        payload = {
            'params': urlencode(payload_params),
        }

        data = self._session.post(SEARCH_URL, params=query_params, json=payload).json()
        self._check_errors(data)
        return data

    def _check_errors(self, data):
        if 'statusCode' in data and data['statusCode'] != 200:
            error = data.get('message') or data.get('statusText')
            raise APIError(error)

    def channels(self):
        self._refresh_token()
        params = {'rpp': 15}
        data = self._session.get('/v2/event/live', params=params).json()
        self._check_errors(data)
        return data['events']

    def epg(self, channel_ids, start, stop):
        self._refresh_token()

        params = {
            'categorisedChannelId': channel_ids,
            'channelId': channel_ids,
            'from': start.to('utc').format('YYYY-MM-DDTHH:MM:00.000')+'Z',
            'to': stop.to('utc').format('YYYY-MM-DDTHH:MM:00.000')+'Z',
        }

        data = self._session.get('/v4/epg/content/programmes', params=params).json()
        self._check_errors(data)
        return data['channels']

    def play_event(self, event_id):
        self._refresh_token(force=True)
        event_data = self._session.get('/v2/event/{}'.format(event_id)).json()
        stream_data = self._session.get('/v2/stream/event/{}'.format(event_id)).json()
        playback_data = self._session.get(stream_data['playerUrlCallback']).json()
        self._check_errors(playback_data)
        return playback_data, event_data

    def play_vod(self, vod_id):
        self._refresh_token(force=True)
        vod_data = self._session.get('/v2/vod/{}'.format(vod_id)).json()
        stream_data = self._session.get('/v3/stream/vod/{}'.format(vod_id)).json()
        playback_data = self._session.get(stream_data['playerUrlCallback']).json()
        self._check_errors(playback_data)
        return playback_data, vod_data

    def logout(self):
        userdata.delete('auth_token')
        userdata.delete('refresh_token')
        userdata.delete('token_expires')
        self.new_session()
