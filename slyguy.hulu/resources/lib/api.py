import hashlib
import uuid
from time import time

import arrow
from slyguy import userdata, mem_cache
from slyguy.session import Session
from slyguy.exceptions import Error
from slyguy.util import get_system_arch, chunked
from slyguy.log import log
from slyguy.drm import req_hdcp_level, HDCP_2_2, is_wv_secure

from .language import _
from .settings import settings, API_URL, HEADERS, DEEJAY_DEVICE_ID, DEEJAY_KEY_VERSION


class APIError(Error):
    pass


ERROR_MAP = {
    1003: _.GEO_ERROR,
    'HOME-002': _.EXPIRED_TOKEN,
}


class API(object):
    def new_session(self):
        self.logged_in = False
        self._session = Session(base_url=API_URL, headers=HEADERS)
        self._set_authentication()

    def _set_authentication(self):
        user_token = userdata.get('user_token')
        if not user_token:
            return

        self._session.headers.update({'Authorization': 'Bearer {}'.format(userdata.get('user_token'))})
        self.logged_in = True

    def _set_auth(self, data):
        if 'device_token' in data:
            userdata.set('device_token', data['device_token'])

        userdata.set('user_token', data['user_token'])
        userdata.set('expires', int(time() + int(data['expires_in'])) - 30)
        userdata.set('user_id', data['user_id'])
        userdata.set('profile_id', data['profile_id'])
        self._set_authentication()

    def _refresh_token(self, force=False):
        device_token = userdata.get('device_token')
        if not device_token or (not force and userdata.get('expires', 0) > time()):
            return

        log.debug('Refreshing token')
        payload = {
            'action': 'token_refresh',
            'device_token': device_token,
        }

        data = self._session.post('https://auth.hulu.com/v1/device/device_token/authenticate', data=payload, headers={'Authorization': None}).json()
        self._check_errors(data)
        self._set_auth(data)

    def _get_serial(self):
        def _format_id(string):
            try:
                mac_address = uuid.getnode()
                if mac_address != uuid.getnode():
                    mac_address = ''
            except:
                mac_address = ''

            system, arch = get_system_arch()
            return str(string.format(mac_address=mac_address, system=system).strip())

        serial = '0000{}'.format(hashlib.md5(_format_id(settings.get('device_id')).encode('utf8')).hexdigest())
        log.debug('Serial: {}'.format(serial))
        return serial

    def deeplink(self, id):
        params = {
            'id': id,
            'namespace': 'entity',
            'schema': 1,
            #'device_info': 'android:4.32.0:compass-mvp:site-map',
        }
        params.update(self._lat_long())

        data = self._session.get('https://discover.hulu.com/content/v5/deeplink/playback', params=params).json()
        self._check_errors(data)
        return data.get('eab_id')

    def entities(self, eab_ids):
        self._refresh_token()

        params = {
            'language': 'en',
            'eab_ids': ",".join(eab_ids),
        }
        params.update(self._lat_long())

        data = self._session.get('https://discover.hulu.com/content/v3/entity', params=params).json()
        self._check_errors(data)
        return data['items']

    def series(self, id, **kwargs):
        return self.hub('series/{}'.format(id), limit=1999, **kwargs)

    def episodes(self, id, season, **kwargs):
        return self.hub('series/{}/season/{}'.format(id, season), limit=1999, **kwargs)

    def hub(self, slug, limit=100, page=1, view=False):
        self._refresh_token()

        params = {
            'limit': limit,
            'offset': (page-1)*limit,
            'schema': 1,
            'bowie_context': 'all',
            #'device_info': 'android:4.32.0:compass-mvp:site-map',
        }
        params.update(self._lat_long())

        endpoint = 'view_hubs' if view else 'hubs'
        data = self._session.get('https://discover.hulu.com/content/v5/{}/{}'.format(endpoint, slug), params=params).json()
        self._check_errors(data)
        return data

    def search(self, query):
        self._refresh_token()

        params = {
            'language': 'en',
            'search_query': query,
            'limit': 64,
            'keywords': query,
            'type': 'entity',
            'include_offsite': 'true',
            'bowie_context': 'all',
        }
        params.update(self._lat_long())

        data = self._session.get('https://discover.hulu.com/content/v5/search/entity', params=params).json()
        self._check_errors(data)
        return data['groups'][0]['results']

    def states(self, eab_ids):
        if not eab_ids:
            return {}

        self._refresh_token()

        states = {}
        for chunk in chunked(eab_ids, 100):
            params = {
                'schema': 1,
                'eab_ids': ",".join(chunk),
                'bowie_context': 'all',
                #'device_info': 'android:4.32.0:compass-mvp:site-map',
            }
            params.update(self._lat_long())

            data = self._session.get('https://discover.hulu.com/content/v5/me/state', params=params).json()
            self._check_errors(data)
            for row in data['items']:
                states[row['eab_id']] = row

        return states

    def channels(self):
        self._refresh_token()

        params = {
            'bowie_context': 'all',
        }
        params.update(self._lat_long())

        data = self._session.get('https://guide.hulu.com/guide/views', params=params).json()
        self._check_errors(data)

        for row in data['views']:
            if row['id'] == 'hulu:guide:all-channels':
                return row['details']['channels']

        return []

    def guide(self, ids, start=None, end=None):
        self._refresh_token()

        start = start or arrow.now()
        end = end or start.shift(hours=4)

        payload = {
            'channels': ids,
            'start_time': start.to('utc').format('YYYY-MM-DDTHH:mm:00.000') + 'Z',
            'end_time': end.to('utc').format('YYYY-MM-DDTHH:mm:00.000') + 'Z',
        }

        data = self._session.post('https://guide.hulu.com/guide/listing', params=self._lat_long(), json=payload).json()
        self._check_errors(data)

        epg = {}
        for row in data['channels']:
            epg[row['id']] = row.get('programs') or []

        return epg

    def guide_details(self, eabs):
        self._refresh_token()

        details = {}
        for chunk in chunked(eabs, 500):
            payload = {
                'eabs': chunk,
            }

            data = self._session.post('https://guide.hulu.com/guide/details', json=payload).json()
            self._check_errors(data)
            
            for row in data['items']:
                if 'eab' not in row:
                    continue

                details[row['eab']] = row

        return details

    def _lat_long(self):
        try:
            latitude, longitude = settings.get('lat_long').strip().split(',')
            return {'lat': '{:.7f}'.format(float(latitude)), 'long': '{:.7f}'.format(float(longitude))}
        except:
            return {}

    def device_code(self):
        self.logout()

        serial = self._get_serial()

        payload = {
            'serial_number': serial,
            'friendly_name': 'android',
        }

        data = self._session.post('https://auth.hulu.com/v1/device/code/register', data=payload).json()
        if 'code' not in data:
            raise APIError(_.NO_DEVICE_CODE)

        return data['code'], serial

    def login_device(self, code, serial):
        payload = {
            'code': code,
            'serial_number': serial,
            'device_id': '166',
        }

        data = self._session.post('https://auth.hulu.com/v1/device/code/authenticate', data=payload).json()
        if data.get('errorCode') == 1004:
            return False

        self._check_errors(data)
        if 'device_token' in data:
            userdata.set('serial', serial)
            self._set_auth(data)
            return True

    def login(self, email, password):
        self.logout()

        serial = self._get_serial()

        payload = {
            'user_email': email,
            'password': password,
            'serial_number': serial,
            'friendly_name': 'android',
            'device_id': '166',
        }

        data = self._session.post('https://auth.hulu.com/v2/livingroom/password/authenticate', data=payload).json()
        self._check_errors(data)

        data = data['data']
        userdata.set('serial', serial)
        self._set_auth(data)

    def profiles(self):
        self._refresh_token()
        data = self._session.get('https://home.hulu.com/v2/users/self/profiles').json()
        self._check_errors(data)
        return data['data']

    @mem_cache.cached(60*10)
    def _user_data(self):
        self._refresh_token()

        params = {
            #'expand': 'profiles,pin_enabled,subscriptions',
            'expand': 'subscriptions',
        }

        data = self._session.get('https://home.hulu.com/v3/users/self', params=params).json()
        self._check_errors(data)
        return data['data']

    def set_profile(self, profile_id, pin=None):
        self._refresh_token()

        payload = {
            'device_token': userdata.get('device_token'),
            'profile_id': profile_id,
            'pin': pin or '',
        }

        data = self._session.post('https://auth.hulu.com/v2/device/profiles/switch', data=payload, headers={'Authorization': None}).json()
        self._check_errors(data)
        self._set_auth(data['data'])
        mem_cache.empty()
        if userdata.get('profile_id') != profile_id:
            raise APIError(_.PROFILE_ERROR)

    def update_progress(self, eab_id, position):
        self._refresh_token()

        payload = {
            'eab_id': eab_id,
            'position': position,
        }

        return self._session.post('https://home.hulu.com/v1/users/self/profiles/self/asset_view_progress', json=payload).ok

    def remove_bookmark(self, eab_id):
        params = {
            'id': eab_id,
        }
        return self._session.delete('https://client.hulu.com/user/v1/bookmarks', params=params).ok

    def add_bookmark(self, eab_id):
        payload = {
            'ids': [eab_id],
        }
        return self._session.post('https://client.hulu.com/user/v1/bookmarks', json=payload).ok

    def play(self, bundle):
        self._refresh_token()
        #id = 'EAB::572e65d0-a5de-4baa-bbff-a489bf9e8498::1128409451::144270058' #live channel
        #id = 'EAB::c097d476-149c-44ee-b7de-4b11e610a052::61649804::132682060' #handmaid tale - 4k HDR
        #id = 'EAB::f9f2384a-4e3a-4777-b718-d970c8023805::61673018::140889333' # american horror stories - normal 4k
        #https://www.reddit.com/r/Hulu/comments/omj8a3/american_horror_stories_not_actually_in_4k/

        if 'content_type' in bundle:
            is_live = bundle['content_type'] == 'LIVE'
        else:
            is_live = bundle.get('bundle_type') != 'VOD'

        av_features = bundle.get('av_features', [])

        vid_types = [{'type':'H264','width':3840,'height':2160,'framerate':60,'level':'4.2','profile':'HIGH'}]
        if settings.getBool('h265'):
            vid_types.append({'type':'H265','width':3840,'height':2160,'framerate':60,'level':'5.1','profile':'MAIN_10','tier':'MAIN'})

        aud_types = [{'type':'AAC'}]
        if settings.getBool('ec3'):
            if is_live:
                #IA doesnt seem to like multi-audio sets on live using $Time$ so need to only choose one audio type
                if '5.1' in av_features:
                    aud_types = [{'type':'EC3'}]
            else:
                aud_types.append({'type':'EC3'})

        secondary_audio = settings.getBool('secondary_audio', False)
        patch_updates = True #needed for live to work
        live_segment_delay = 3

        payload = {
            'content_eab_id': bundle['eab_id'],
            'play_intent': 'resume', #live, resume (gives resume position), restart (doesnt give resume position)
            'unencrypted': True,
            'all_cdn': False,
            'ignore_kids_block': False,
            'device_identifier': self._get_serial(),
            'deejay_device_id': DEEJAY_DEVICE_ID,
            'version': DEEJAY_KEY_VERSION,
            'include_t2_rev_beacon': False,
            'include_t2_adinteraction_beacon': False,
            'support_brightline': False,
            'support_innovid': False,
            'support_innovid_truex': False,
            'support_gateway': False,
            'limit_ad_tracking': True,
            'network_mode': 'Ethernet',
            'enable_selectors': False,
            'playback': {
                'version': 2,
                'video': {'codecs':{'values':vid_types, 'selection_mode':'ALL'}},
                'audio': {'codecs':{'values':aud_types, 'selection_mode':'ALL'}},
                'drm': {'values':[{'type':'WIDEVINE', 'version':'MODULAR', 'security_level': 'L1' if is_wv_secure() else 'L3'}], 'selection_mode':'ALL'},
                'manifest': {'type':'DASH', 'https':True, 'multiple_cdns':False, 'patch_updates':patch_updates, 'hulu_types':False, 'live_dai':False, 'multiple_periods':False, 'xlink':False, 'secondary_audio':secondary_audio, 'live_fragment_delay':live_segment_delay},
                'trusted_execution_environment': True,
                'segments': {'values':[{'type':'FMP4','encryption':{'mode':'CENC','type':'CENC'},'https':True}], 'selection_mode':'ONE'}
            },
            # 'interface_version': '1.12.1',
            # 'channel_id': '',
            # 'device_model': 'SHIELD Android TV',
            # 'app_version': app_version,
            # 'kv': key_id,
            # 'device_ad_id': device_id,
            # 'cp_session_id': device_id,
        }

        if (settings.getBool('hdr10', True) or settings.getBool('dolby_vision', False)) and req_hdcp_level(HDCP_2_2): # also need WV L1?
            payload['playback']['video']['dynamic_range'] = 'DOLBY_VISION' if not settings.getBool('hdr10', True) else 'HDR'
            payload['playback']['drm']['multi_key'] = True

        payload.update(self._lat_long())

        data = self._session.post('https://play.hulu.com/v6/playlist', json=payload).json()
        self._check_errors(data)
        return data

    def _check_errors(self, data):
        if not type(data) is dict:
            return

        if data.get('errorCode'):
            message = ERROR_MAP.get(data['errorCode']) or data.get('message') or data.get('error') or data.get('errorCode')
            raise APIError(message)

        if data.get('code'):
            message = ERROR_MAP.get(data['code']) or data.get('message') or data.get('error') or data.get('code')
            raise APIError(message)

        if data.get('error'):
            raise APIError(data['error']['message'])

    def _device_logout(self):
        payload = {
            'device_id': '166',
            'device_token': userdata.get('device_token'),
        }

        self._session.post('https://auth.hulu.com/v1/device/logout', data=payload, timeout=10).json()

    def logout(self):
        if userdata.get('device_token'):
            try: self._device_logout()
            except: pass

        mem_cache.empty()
        userdata.delete('user_id')
        userdata.delete('profile_id')
        userdata.delete('user_token')
        userdata.delete('serial')
        userdata.delete('device_token')
        userdata.delete('expires')
        self.new_session()
