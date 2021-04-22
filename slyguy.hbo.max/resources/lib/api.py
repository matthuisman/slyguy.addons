import uuid
from time import time

import arrow
import re
from pycaption import detect_format, WebVTTWriter
from kodi_six import xbmc

from slyguy import userdata, settings
from slyguy.session import Session
from slyguy.exceptions import Error
from slyguy.log import log
from slyguy.util import get_system_arch

from .constants import *
from .language import _

class APIError(Error):
    pass

class API(object):
    def new_session(self):
        self.logged_in = False
        self._session  = Session(HEADERS, base_url=BASE_URL, timeout=30)
        self._set_authentication(userdata.get('access_token'))

    def _set_authentication(self, access_token):
        if not access_token:
            return

        self._session.headers.update({'Authorization': 'Bearer {}'.format(access_token)})
        self.logged_in = True

    def _refresh_token(self, force=False):
        if not force and userdata.get('expires', 0) > time():
            return

        payload = {
            'refresh_token': userdata.get('refresh_token'),
            'grant_type': 'refresh_token',
            'scope': 'browse video_playback device',
        }

        self._oauth_token(payload, {'Authorization': None})

    def _oauth_token(self, payload, headers=None):
        data = self._session.post('/tokens', data=payload, headers=headers).json()
        self._check_errors(data)

        self._set_authentication(data['access_token'])
        userdata.set('access_token', data['access_token'])
        userdata.set('expires', int(time() + data['expires_in'] - 15))

        if 'refresh_token' in data:
            userdata.set('refresh_token', data['refresh_token'])

    def _device_serial(self):
        def _format_id(string):
            try:
                mac_address = uuid.getnode()
                if mac_address != uuid.getnode():
                    mac_address = ''
            except:
                mac_address = ''

            system, arch = get_system_arch()
            return str(string.format(mac_address=mac_address, system=system).strip())

        return str(uuid.uuid3(uuid.UUID(UUID_NAMESPACE), _format_id(settings.get('device_id'))))

    def device_code(self):
        self.logout()

        serial = self._device_serial()

        payload = {
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_ID,
            'scope': 'browse video_playback_free account_registration',
            'grant_type': 'client_credentials',
            'deviceSerialNumber': serial,
            'clientDeviceData': {
            	'paymentProviderCode': 'google-play'
            }
        }

        data = self._session.post('/tokens', json=payload).json()
        self._check_errors(data)

        self._set_authentication(data['access_token'])

        payload = {
            'model': DEVICE_MODEL,
            'serialNumber': serial,
            'userIntent': 'login',
        }

        data = self._session.post('/devices/activationCode', json=payload).json()

        return serial, data['activationCode']

    def set_profile(self, profile_id):
        self._refresh_token()

        payload = {
            'grant_type': 'user_refresh_profile',
            'profile_id': profile_id,
            'refresh_token': userdata.get('refresh_token'),
        }

        self._oauth_token(payload)

    def device_login(self, serial, code):
        payload = {
            'model': DEVICE_MODEL,
            'code': code,
            'serialNumber': serial,
            'grant_type': 'user_activation_code',
            'scope': 'browse video_playback device elevated_account_management',
        }

        try:
            self._oauth_token(payload)
            return True
        except Exception as e:
            return False

    def _check_errors(self, data, error=_.API_ERROR):
        if 'code' in data:
            error_msg = data.get('message') or data.get('code')
            raise APIError(_(error, msg=error_msg))

    def profiles(self):
        self._refresh_token()
        payload = [{'id': 'urn:hbo:profiles:mine'},]
        return self._session.post('/content', json=payload).json()[0]['body']['profiles']

    def delete_profile(self, profile_id):
        self._refresh_token()
        data = self._session.delete('https://profiles.api.hbo.com/profiles/{}'.format(profile_id)).json()
        return data['success']

    def add_profile(self, name, kids, avatar):
        self._refresh_token()

        payload = {
            'avatarId': avatar,
            'name': name,
            'profileType': 'adult',
        }

        if kids:
            payload.update({
                'profileType': 'child',
                'exitPinRequired': False,
                'birth': {
                    'year': arrow.now().year - 5,
                    'month': arrow.now().month,
                },
                'parentalControls': {
                    'movie': 'G',
                    'tv': 'TV-G',
                },
            })

        data = self._session.post('https://profiles.api.hbo.com/profiles', json=payload).json()
        self._check_errors(data)

        for row in data['results']['profiles']:
            if row['name'] == name:
                return row

        raise APIError('Failed to create profile')

    def _age_category(self):
        month, year = userdata.get('profile', {}).get('birth', [0,0])

        i = arrow.now()
        n = i.year - year
        if i.month < month:
            n -= 1
        age = max(0, n)

        group = AGE_CATS[0][1]
        for cat in AGE_CATS:
            if age >= cat[0]:
                group = cat[1]

        return group

    def content(self, slug, tab=None):
        self._refresh_token()

        params = {
            'device-code': DEVICE_MODEL,
            'product-code': 'hboMax',
            'api-version': 'v9',
            'country-code': 'us',
            'profile-type': 'default',
            'signed-in': True,
        }

        if userdata.get('profile',{}).get('child', 0):
            params.update({
                'profile-type': 'child',
                'age-category': self._age_category(),
            })

        data = self._session.get('/express-content/{}'.format(slug), params=params).json()
        self._check_errors(data)

        _data = {}
        for row in data:
            _data[row['id']] = row['body']

        return self._process(_data, tab or slug)

    def _process(self, data, slug):
        main = data[slug]

        def process(element):
            element['items'] = []
            element['tabs'] = []
            element['edits'] = []
            element['seasons'] = []
            element['episodes'] = []
            element['target'] = None

            for key in element.get('references', {}):
                if key in ('items', 'tabs', 'edits', 'seasons', 'episodes'):
                    for id in element['references'][key]:
                        if id == '$dataBinding':
                            continue

                        item = {'id': id}
                        if id in data:
                            item.update(data[id])
                        process(item)
                        element[key].append(item)
                else:
                    element[key] = element['references'][key]

            element.pop('references', None)

        process(main)
        return main

    def search(self, query):
        self._refresh_token()

        payload = [{
            'id': 'urn:hbo:flexisearch:{}'.format(query),
        }]

        data = self._session.post('/content', json=payload).json()
        self._check_errors(data)

        keys = {}
        key = None
        for row in data:
            keys[row['id']] = row['body']
            if row['id'].startswith('urn:hbo:grid:search') and row['id'].endswith('-all'):
                key = row['id']

        if not key:
            return None

        return self._process(keys, key)

    def play(self, slug):
        self._refresh_token()

        content_data = self.content(slug)
        if not content_data['edits']:
            raise APIError(_.NO_VIDEO_FOUND)

        selected = content_data['edits'][0]
        for edit in content_data['edits']:
            for row in edit.get('textTracks', []):
                if row.get('language') == 'en-US':
                    selected = edit
                    break

        payload = [{
            'id': selected['video'],
            'headers' : {
                'x-hbo-preferred-blends': 'DASH_WDV,HSS_PR',
                'x-hbo-video-mlp': True,
            }
        }]

        data = self._session.post('/content', json=payload).json()[0]['body']
        self._check_errors(data)

        for row in data['manifests']:
            if row['type'] == 'urn:video:main':
                return row, content_data

        raise APIError(_.NO_VIDEO_FOUND)

    def get_subtitle(self, url, out_file):
        r = self._session.get(url)
        reader = detect_format(r.text)
        vtt = WebVTTWriter().write(reader().read(r.text))
        with open(out_file, 'wb') as f:
            f.write(vtt.encode('utf8'))

    def logout(self):
        userdata.delete('access_token')
        userdata.delete('expires')
        userdata.delete('refresh_token')
        self.new_session()