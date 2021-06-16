import uuid
from time import time
import xml.etree.ElementTree as ET

from slyguy import userdata, mem_cache, settings
from slyguy.session import Session
from slyguy.exceptions import Error
from slyguy.util import strip_namespaces, hash_6, get_system_arch
from slyguy.log import log

from .constants import *
from .language import _

class APIError(Error):
    pass

class API(object):
    def new_session(self):
        self.logged_in = False
        self._session = Session(base_url=API_URL, headers=HEADERS)
        self._set_authentication()

    def _set_authentication(self):
        auth_cookies = userdata.get('auth_cookies')
        if not auth_cookies:
            return

        self._session.cookies.update(auth_cookies)
        self.logged_in = True

    def _device_id(self):
        device_id = userdata.get('device_id')
        if device_id:
            return device_id

        device_id = settings.get('device_id')

        try:
            mac_address = uuid.getnode()
            if mac_address != uuid.getnode():
                mac_address = ''
        except:
            mac_address = ''

        system, arch = get_system_arch()
        device_id = device_id.format(username=userdata.get('username'), mac_address=mac_address, system=system).strip()

        if not device_id:
            device_id = uuid.uuid4()

        log.debug('Raw device id: {}'.format(device_id))
        device_id = hash_6(device_id, length=16)
        log.debug('Hashed device id: {}'.format(device_id))

        userdata.set('device_id', device_id)
        return device_id

    def device_code(self):
        params = {'locale': 'en-us', 'at': AT}
        payload = {'deviceId': self._device_id()}
        return self._session.post('/v2.0/androidtv/ott/auth/code.json', params=params, data=payload).json()

    def _refresh_token(self, force=False):
        if not force and userdata.get('expires', 0) > time() or not self.logged_in:
            return

        log.debug('Refreshing token')
        self.set_profile(userdata.get('profile_id'), refresh=False)

    def login(self, username, password):
        params = {'locale': 'en-us', 'at': AT}
        payload = {
            'j_password': password,
            'j_username': username,
            'deviceId': self._device_id(),
        }
        resp = self._session.post('/v2.0/androidtv/auth/login.json', params=params, data=payload)
        data = resp.json()

        if not data['success']:
            raise APIError(data.get('message'))

        self._save_auth(resp.cookies)
        self._set_profile_data(self.user()['activeProfile'])

    def device_login(self, code, device_token):
        params = {'locale': 'en-us', 'at': AT}
        payload = {
            'activationCode': code,
            'deviceToken': device_token,
            'deviceId': self._device_id(),
        }
        resp = self._session.post('/v2.0/androidtv/ott/auth/status.json', params=params, data=payload)
        data = resp.json()

        if data.get('regenerateCode'):
            return -1
        elif not data['success']:
            return False

        self._save_auth(resp.cookies)
        self._set_profile_data(self.user()['activeProfile'])

        return True

    def _save_auth(self, cookies):
        expires = None
        for cookie in cookies:
            if expires is None or cookie.expires < expires:
                expires = cookie.expires

        userdata.set('expires', min(expires, int(time() + 86400)))
        userdata.set('auth_cookies', cookies.get_dict())

        self._set_authentication()

    def set_profile(self, profile_id, refresh=True):
        if refresh:
            self._refresh_token()

        params = {'locale': 'en-us', 'at': AT}
        resp = self._session.post('/v2.0/androidtv/user/account/profile/switch/{}.json'.format(profile_id), params=params)
        data = resp.json()

        if not data['success']:
            raise APIError('Failed to set profile: {}'.format(profile_id))

        self._set_profile_data(data['profile'])
        self._save_auth(resp.cookies)

    def _set_profile_data(self, profile):
        userdata.set('profile_id', profile['id'])
        userdata.set('profile_name', profile['name'])
        userdata.set('profile_img', profile['profilePicPath'])

    @mem_cache.cached(60*10)
    def show_groups(self):
        params = {'includeAllShowGroups': 'true', 'locale': 'en-us', 'at': AT}
        return self._session.get('/v2.0/androidtv/shows/groups.json', params=params).json()['showGroups']

    @mem_cache.cached(60*10)
    def show_group(self, group_id):
        params = {'includeAllShowGroups': 'true', 'locale': 'en-us', 'at': AT}
        return self._session.get('/v2.0/androidtv/shows/group/{}.json'.format(group_id), params=params).json()['group']

    @mem_cache.cached(60*10)
    def show(self, show_id):
        params = {'locale': 'en-us', 'at': AT}
        return self._session.get('/v3.0/androidtv/shows/{}.json'.format(show_id), params=params).json()

    @mem_cache.cached(60*10)
    def episodes(self, show_id, season):
        params = {
            'platformType': 'androidtv',
            'rows': 1,
            'begin': 0,
            'locale': 'en-us',
            'at': AT,
        }

        section_id = self._session.get('/v2.0/androidtv/shows/{}/videos/config/DEFAULT_APPS_FULL_EPISODES.json'.format(show_id), params=params).json()['section_display_seasons'][0]['sectionId']

        params = {
            'rows': 999,
            'params': 'seasonNum={}'.format(season),
            'begin': 0,
            'seasonNum': season,
            'locale': 'en-us',
            'at': AT,
        }

        return self._session.get('/v2.0/androidtv/videos/section/{}.json'.format(section_id), params=params).json()['sectionItems']['itemList']

    @mem_cache.cached(60*10)
    def seasons(self, show_id):
        params = {'locale': 'en-us', 'at': AT}
        return self._session.get('/v3.0/androidtv/shows/{}/video/season/availability.json'.format(show_id), params=params).json()['video_available_season']['itemList']

    @mem_cache.cached(60*10)
    def search(self, query):
        params = {
            'term': query,
            'termCount': 50,
            'showCanVids': 'true',
            'locale': 'en-us',
            'at': AT,
        }
        return self._session.get('/v3.0/androidtv/contentsearch/search.json', params=params).json()['terms']

    def user(self):
        self._refresh_token()

        params = {'locale': 'en-us', 'at': AT}
        return self._session.get('/v3.0/androidtv/login/status.json', params=params).json()

    def play(self, video_id):
        self._refresh_token()

        params = {'locale': 'en-us', 'at': AT}
        video_data = self._session.get('/v2.0/androidtv/video/cid/{}.json'.format(video_id), params=params).json()['itemList'][0]

        params = {
            'formats': 'mpeg-dash',
            'tracking': True,
            'format': 'SMIL'
        }

        resp = self._session.get('https://link.theplatform.com/s/dJ5BDC/{}'.format(video_data['pid']), params=params)

        root = ET.fromstring(resp.text)
        strip_namespaces(root)

        if root.find("./body/seq/ref/param[@name='exception']") != None:
            error_msg = root.find("./body/seq/ref").attrib.get('abstract')
            raise APIError(_('Play Error', message=error_msg))

        ref = root.find(".//video")
        url = ref.attrib['src']

        params = {'locale': 'en-us', 'at': AT, 'contentId': video_id}
        data = self._session.get('/v3.0/androidtv/irdeto-control/session-token.json', params=params).json()

        return url, data['url'], data['ls_session'], video_data

    def _ip(self):
        params = {'locale': 'en-us', 'at': AT}
        return self._session.get('https://www.paramountplus.com/apps/user/ip.json', params=params).json()['ip']

    def live_channels(self):
        self._refresh_token()
        dma = self.dma()

        params = {
            'start': 0,
            'rows': 30,
         #   '_clientRegion': 'US',
            'dma': dma['dma'] if dma else None,
            'showListing': 'true',
            'locale': 'en-us',
            'at': AT,
        }

        data = self._session.get('/v3.0/androidtv/live/channels.json', params=params).json()

        channels = []
        for row in data['channels']:
            if row['dma'] and dma:
                row['dma'] = dma['tokenDetails']

            channels.append(row)

        return sorted(channels, key=lambda x: x['displayOrder'])

    def epg(self, channel, page=1, rows=25):
        params = {
            'start': (page-1)*rows,
            'rows': rows,
          #  '_clientRegion': 'US',
            'showListing': 'true',
            'locale': 'en-us',
            'at': AT,
        }

        return self._session.get('/v3.0/androidtv/live/channels/{slug}/listings.json'.format(slug=channel), params=params).json()['listing']

    def dma(self):
        self._refresh_token()

        ip = settings.get('region_ip')
        if not ip or ip == '0.0.0.0':
            ip = self._ip()

        params = {
            'ipaddress': ip,
            'dtp': 8, #controls quality
            'syncBackVersion': '3.0',
            'mvpdId': 'AllAccess',
            'is60FPS': 'true',
            #'did': self._device_id(),
            'locale': 'en-us',
            'at': AT,
        }

        data = self._session.get('/v3.0/androidtv/dma.json', params=params).json()
        if not data['success']:
            log.warning('Failed to get local CBS channel for IP address ({}). Server message: {}'.format(ip, data.get('message')))
            return None

        return data['dmas'][0]

    def logout(self):
        userdata.delete('profile_img')
        userdata.delete('profile_name')
        userdata.delete('profile_id')
        userdata.delete('auth_cookies')
        userdata.delete('device_id')
        self.new_session()
