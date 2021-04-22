import time
import hmac
import hashlib
import base64
import json

from six.moves.urllib_parse import quote_plus
from kodi_six import xbmc
from pycaption import detect_format, WebVTTWriter

from slyguy import userdata, settings
from slyguy.session import Session
from slyguy.exceptions import Error
from slyguy.log import log
from slyguy.util import cenc_init, jwt_data

from .constants import *
from .language import _

class APIError(Error):
    pass

class API(object):
    def new_session(self):
        self.logged_in = False
        self._session  = Session(HEADERS, base_url=API_URL)
        self._set_authentication()

    def _set_authentication(self):
        self.logged_in = userdata.get('token') != None

    def nav_items(self, key):
        data = self.page('sitemap')

        for row in data['navs']['browse']:
            if row['path'] == '/'+key:
                return row['items']

        return []

    def page(self, key):
        return self.url('/pages/v6/{}.json'.format(key))

    def url(self, url):
        self._check_token()

        params = {
            'feedTypes': 'posters,landscapes,hero',
            'jwToken': userdata.get('token'),
        }

        return self._session.get(url, params=params).json()

    def search(self, query, page=1, limit=50):
        self._check_token()

        params = {
            'q': query,
            'limit': limit,
            'offset': (page-1)*limit,
            'jwToken': userdata.get('token'),
        }

        if userdata.get('profile_kids', False):
            url = '/search/v12/kids/search'
        else:
            url = '/search/v12/search'

        return self._session.get(url, params=params).json()

    def login(self, username, password):
        self.logout()

        payload = {
            'email': username,
            'password': password,
            'rnd': str(int(time.time())),
            'stanName': 'Stan-Android',
            'type': 'mobile',
            'os': 'Android',
            'stanVersion': STAN_VERSION,
         #   'clientId': '',
           # 'model': '',
          #  'sdk': '',
           # 'manufacturer': '',
        }

        payload['sign'] = self._get_sign(payload)

        self._login('/login/v1/sessions/mobile/account', payload)

    def _check_token(self, force=False):
        if not force and userdata.get('expires') > time.time():
            return

        params = {
            'type': 'mobile',
            'os': 'Android',
            'stanVersion': STAN_VERSION,
        }

        payload = {
            'jwToken': userdata.get('token'),
        }

        self._login('/login/v1/sessions/mobile/app', payload, params)

    def _login(self, url, payload, params=None):
        data = self._session.post(url, data=payload, params=params).json()

        if 'errors' in data:
            try:
                msg = data['errors'][0]['code']
                if msg == 'Streamco.Login.VPNDetected':
                    msg = _.IP_ADDRESS_ERROR
            except:
                msg = ''

            raise APIError(_(_.LOGIN_ERROR, msg=msg))

        userdata.set('token', data['jwToken'])
        userdata.set('expires', int(time.time() + (data['renew'] - data['now']) - 30))
        userdata.set('user_id', data['userId'])

        userdata.set('profile_id', data['profile']['id'])
        userdata.set('profile_name', data['profile']['name'])
        userdata.set('profile_icon', data['profile']['iconImage']['url'])
        userdata.set('profile_kids', int(data['profile'].get('isKidsProfile', False)))

        self._set_authentication()

        try: log.debug('Token Data: {}'.format(json.dumps(jwt_data(userdata.get('token')))))
        except: pass

    def watchlist(self):
        self._check_token()

        params = {
            'jwToken': userdata.get('token'),
        }

        url = '/watchlist/v1/users/{user_id}/profiles/{profile_id}/watchlistitems'.format(user_id=userdata.get('user_id'), profile_id=userdata.get('profile_id'))
        return self._session.get(url, params=params).json()

    def history(self, program_ids=None):
        self._check_token()

        params = {
            'jwToken': userdata.get('token'),
            'limit': 100,
        }

        if program_ids:
            params['programIds'] = program_ids

        url = '/history/v1/users/{user_id}/profiles/{profile_id}/history'.format(user_id=userdata.get('user_id'), profile_id=userdata.get('profile_id'))
        return self._session.get(url, params=params).json()

    # def resume_series(self, series_id):
    #     params = {
    #         'jwToken': userdata.get('token'),
    #     }

    #     url = '/resume/v1/users/{user_id}/profiles/{profile_id}/resumeSeries/{series_id}'.format(user_id=userdata.get('user_id'), profile_id=userdata.get('profile_id'), series_id=series_id)
    #     return self._session.get(url, params=params).json()

    # def resume_program(self, program_id):
    #     params = {
    #         'jwToken': userdata.get('token'),
    #     }

    #     url = '/resume/v1/users/{user_id}/profiles/{profile_id}/resume/{program_id}'.format(user_id=userdata.get('user_id'), profile_id=userdata.get('profile_id'), program_id=program_id)
    #     return self._session.get(url, params=params).json()

    def set_profile(self, profile_id):
        self._check_token()

        params = {
            'type': 'mobile',
            'os': 'Android',
            'stanVersion': STAN_VERSION,
        }

        payload = {
            'jwToken': userdata.get('token'),
            'profileId': profile_id,
        }

        self._login('/login/v1/sessions/mobile/app', payload, params)

    def profiles(self):
        self._check_token()

        params = {
            'jwToken': userdata.get('token'),
        }

        return self._session.get('/accounts/v1/users/{user_id}/profiles'.format(user_id=userdata.get('user_id')), params=params).json()

    def add_profile(self, name, icon_set, icon_index, kids=False):
        self._check_token()

        payload = {
            'jwToken': userdata.get('token'),
            'name': name,
            'isKidsProfile': kids,
            'iconSet': icon_set,
            'iconIndex': icon_index,
        }

        return self._session.post('/accounts/v1/users/{user_id}/profiles'.format(user_id=userdata.get('user_id')), data=payload).json()

    def delete_profile(self, profile_id):
        self._check_token()

        params = {
            'jwToken': userdata.get('token'),
            'profileId': profile_id,
        }

        return self._session.delete('/accounts/v1/users/{user_id}/profiles'.format(user_id=userdata.get('user_id')), params=params).ok

    def profile_icons(self):
        self._check_token()

        params = {
            'jwToken': userdata.get('token'),
        }

        return self._session.get('/accounts/v1/accounts/icons', params=params).json()

    def program(self, program_id):
        self._check_token()

        params = {
            'jwToken': userdata.get('token'),
        }

        if userdata.get('profile_kids', False):
            url = '/cat/v12/kids/programs/{program_id}.json'
        else:
            url = '/cat/v12/programs/{program_id}.json'

        return self._session.get(url.format(program_id=program_id), params=params).json()

    def play(self, program_id):
        self._check_token(force=True)

        program_data = self.program(program_id)
        if 'errors' in program_data:
            try:
                msg = program_data['errors'][0]['code']
                if msg == 'Streamco.Concurrency.OutOfRegion':
                    msg = _.IP_ADDRESS_ERROR
                elif msg == 'Streamco.Catalogue.NOT_SAFE_FOR_KIDS':
                    msg = _.KIDS_PLAY_DENIED
            except:
                msg = ''

            raise APIError(_(_.PLAYBACK_ERROR, msg=msg))

        jw_token = userdata.get('token')

        params = {
            'programId': program_id,
            'jwToken': jw_token,
            'format': 'dash',
            'capabilities.drm': 'widevine',
            'quality': 'high',
        }

        data = self._session.get('/concurrency/v1/streams', params=params).json()

        if 'errors' in data:
            try:
                msg = data['errors'][0]['code']
                if msg == 'Streamco.Concurrency.OutOfRegion':
                    msg = _.IP_ADDRESS_ERROR
            except:
                msg = ''

            raise APIError(_(_.PLAYBACK_ERROR, msg=msg))

        play_data = data['media']
        play_data['drm']['init_data'] = self._init_data(play_data['drm']['keyId'])
        play_data['videoUrl'] = API_URL.format('/manifest/v1/dash/androidtv.mpd?url={url}&audioType=all&version=88'.format(
            url = quote_plus(play_data['videoUrl']),
        ))

        params = {
            'form': 'json',
            'schema': '1.0',
            'jwToken': jw_token,
            '_id': data['concurrency']['lockID'],
            '_sequenceToken': data['concurrency']['lockSequenceToken'],
            '_encryptedLock': 'STAN',
        }

        self._session.get('/concurrency/v1/unlock', params=params).json()

        return program_data, play_data

    def _init_data(self, key):
        key     = key.replace('-', '')
        key_len = '{:x}'.format(len(bytearray.fromhex(key)))
        key     = '12{}{}'.format(key_len, key)
        key     = bytearray.fromhex(key)

        return cenc_init(key)

    def get_subtitle(self, url, out_file):
        r = self._session.get(url)
        reader = detect_format(r.text)
        vtt = WebVTTWriter().write(reader().read(r.text))
        with open(out_file, 'wb') as f:
            f.write(vtt.encode('utf8'))

    def _get_sign(self, payload):
        module_version = 214

        f3757a = bytearray((144, 100, 149, 1, 2, 8, 36, 208, 209, 51, 103, 131, 240, 66, module_version,
                            20, 195, 170, 44, 194, 17, 161, 118, 71, 105, 42, 76, 116, 230, 87, 227, 40, 115,
                            5, 62, 199, 66, 7, 251, 125, 238, 123, 71, 220, 179, 29, 165, 136, 16, module_version,
                            117, 10, 100, 222, 41, 60, 103, 2, 121, 130, 217, 75, 220, 100, 59, 35, 193, 22, 117,
                            27, 74, 50, 85, 40, 39, 31, 180, 81, 34, 155, 172, 202, 71, 162, 202, 234, 91, 176, 199, 207, 131,
                            229, 125, 105, 9, 227, 188, 234, 61, 33, 17, 113, 222, 173, 182, 120, 34, 80, 135, 219, 8, 97, 176, 62,
                            137, 126, 222, 139, 136, 77, 243, 37, 11, 234, 82, 244, 222, 44))

        f3758b = bytearray((120, 95, 52, 175, 139, 155, 151, 35, 39, 184, 141, 27, 55, 215, 102, 173, 2, 37, 141, 164, 236, 217,
                            173, 194, 94, 67, 195, 24, 221, 66, 233, 11, 226, 91, 33, 249, 225, 54, 88, 54, 118, 101, 31, 248, 11,
                            208, 206, 226, 68, 20, 143, 37, 104, 159, 184, 22, 53, 179, 104, 152, 170, 29, 26, 6, 163, 45, 87, 193,
                            136, 226, 128, 245, 231, 238, 154, 211, 71, 134, 232, 99, 35, 54, 170, 128, 1, 218, 249, 70, 182, 145,
                            125, 211, 16, 43, 118, 177, 64, 128, 111, 73, 234, 22, 21, 165, 67, 23, 15, 5, 11, 70, 48, 97, 134, 185,
                            11, 28, 167, 140, 123, 81, 240, 247, 77, 187, 23, 243, 89, 54))

        msg = ''
        for key in sorted(payload.keys()):
            if msg: msg += '&'
            msg += key + '=' + quote_plus(payload[key], safe="_-!.~'()*")

        bArr = bytearray(len(f3757a))
        for i in range(len(bArr)):
            bArr[i] = f3757a[i] ^ f3758b[i]

        bArr2 = bytearray(int(len(bArr)/2))
        for i in range(len(bArr2)):
            bArr2[i] = bArr[i] ^ bArr[len(bArr2) + i]

        signature = hmac.new(bArr2, msg=msg.encode('utf8'), digestmod=hashlib.sha256).digest()

        return base64.b64encode(signature).decode('utf8')

    def logout(self):
        userdata.delete('token')
        userdata.delete('expires')
        userdata.delete('user_id')

        userdata.delete('profile_id')
        userdata.delete('profile_icon')
        userdata.delete('profile_name')
        userdata.delete('profile_kids')

        self.new_session()