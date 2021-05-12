import uuid
import time
from contextlib import contextmanager

import arrow

from slyguy import userdata
from slyguy.log import log
from slyguy.session import Session
from slyguy.exceptions import Error
from slyguy.mem_cache import cached
from slyguy.util import jwt_data

from .constants import HEADERS, DEFAULT_TOKEN, UUID_NAMESPACE, API_BASE, WV_LICENSE_URL
from .language import _

class APIError(Error):
    pass


class API(object):
    def new_session(self):
        self.logged_in = False

        self._session = Session(HEADERS, base_url=API_BASE)
        self._set_authentication()

    def _set_authentication(self):
        token = userdata.get('token')
        if not token:
            return

        self._session.headers.update({'Authorization': 'Bearer {}'.format(token)})
        self.logged_in = True

    @contextmanager
    def api_call(self):
        if self.logged_in:
            self.refresh_token()

        try:
            yield
        except Exception as e:
            log.exception(e)
            raise APIError(_.NO_DATA)

    def refresh_token(self):
        if not self.logged_in or time.time() < userdata.get('expires', 0):
            return

        data = self._session.put('/oam/v2/user/tokens').json()

        if 'errorMessage' in data:
            raise APIError(_(_.TOKEN_ERROR, msg=data['errorMessage']))

        self._set_token(data['sessionToken'])

    def _set_token(self, token):
        data = jwt_data(token)
        expires = min(int(time.time()+86400), data['exp']-10)

        userdata.set('expires', expires)
        userdata.set('token', token)

        self._set_authentication()

    def login(self, username, password):
        self.logout()

        deviceid = str(uuid.uuid3(uuid.UUID(UUID_NAMESPACE), str(username)))

        payload = {
            "username": username,
            "password": password,
            "deviceID": deviceid,
        }

        headers = {'Authorization': 'Bearer {}'.format(DEFAULT_TOKEN)}

        with self.api_call():
            data = self._session.post('/oam/v2/user/tokens', json=payload, headers=headers).json()

        if 'errorMessage' in data:
            raise APIError(_(_.LOGIN_ERROR, msg=data['errorMessage']))

        userdata.set('deviceid', deviceid)

        self._set_token(data['sessionToken'])

    def whats_on(self, query=''):
        now   = arrow.utcnow()
        later = now.shift(days=21)

        params = {
            'count': 100,
            'offset': 0,
            'language': '*',
            'query': query,
            'sort': 'startTime',
            'sortOrder': 'asc',
            'startTime.lte': later.format('YYYY-MM-DDTHH:mm:ss.000') + 'Z',
            'endTime.gte': now.format('YYYY-MM-DDTHH:mm:ss.000') + 'Z',
            'types': 'live/competitions,live/teamCompetitions,live/events',
        }

        with self.api_call():
            return self._session.get('/ocm/v2/search', params=params).json()['results']

    def search(self, query):
        params = {
            'count': 100,
            'offset': 0,
            'language': '*',
            'query': query,
            'sort': 'liveEventDate',
            'sortOrder': 'desc',
            'searchMethods': 'prefix,fuzzy',
            'types': 'vod/competitions,vod/teamCompetitions,vod/events',
        }

        with self.api_call():
            return self._session.get('/ocm/v2/search', params=params).json()['results']

    def sparksport(self):
        with self.api_call():
            return self._session.get('https://d2rhrqdzx7i00p.cloudfront.net/sparksport2').json()

    def page(self, page_id):
        with self.api_call():
            return self._session.get('/ocm/v4/pages/{}'.format(page_id)).json()

    @cached(expires=60*10)
    def section(self, section_id):
        with self.api_call():
            return self._session.get('/ocm/v4/sections/{}'.format(section_id)).json()

    def live_channels(self):
        with self.api_call():
            return self._session.get('/ocm/v2/epg/stations').json()['epg/stations']

    def entitiy(self, entity_id):
        with self.api_call():
            data = self._session.get('/ocm/v2/entities/{}'.format(entity_id)).json()

        for key in data:
            try:
                if data[key][0]['id'] == entity_id:
                    return data[key][0]
            except (TypeError, KeyError):
                continue

        return None

    def play(self, entity_id):
        entity = self.entitiy(entity_id)
        if not entity or not entity.get('assetIDs'):
            raise APIError(_.NO_ASSET_ERROR)

        with self.api_call():
            assets = self._session.get('/ocm/v2/assets/{}'.format(entity['assetIDs'][0])).json()['assets']

        mpd_url = None
        for asset in assets:
            try:
                urls = asset['liveURLs'] or asset['vodURLs']
                mpd_url = urls['dash']['primary']
                backup  = urls['dash'].get('backup')
                if 'dai.google.com' in mpd_url and backup and 'dai.google.com' not in backup:
                    mpd_url = backup
            except (TypeError, KeyError):
                continue
            else:
                break

        if not mpd_url:
            raise APIError(_.NO_MPD_ERROR)

        # Hack until Spark fix their bad second base-url
        # if '/startover/' in mpd_url:
        #     mpd_url = mpd_url.split('/')
        #     mpd_url = "/".join(mpd_url[:-3]) + '/master.mpd'
        #

        payload = {
            'assetID': entity_id,
            'playbackUrl': mpd_url,
            'deviceID': userdata.get('deviceid'),
        }

        data = self._session.post('/oem/v2/entitlement?tokentype=isp-atlas', json=payload).json()
        token = data.get('entitlementToken')

        if not token:
            raise APIError(_(_.NO_ENTITLEMENT, error=data.get('errorMessage')))

        params = {
            'progress': 0,
            'device': userdata.get('deviceid'),
        }

        self._session.put('/oxm/v1/streams/{}/stopped'.format(entity_id), params=params)

        headers = {'X-ISP-TOKEN': token}

        from_start = True
        if entity.get('customAttributes', {}).get('isLinearChannelInLiveEvent') == 'true':
            from_start = False

        return mpd_url, WV_LICENSE_URL, headers, from_start

    def logout(self):
        userdata.delete('token')
        userdata.delete('deviceid')
        userdata.delete('expires')
        self.new_session()