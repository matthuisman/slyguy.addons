import time
import xml.etree.ElementTree as ET

from slyguy import userdata
from slyguy.session import Session
from slyguy.log import log
from slyguy.exceptions import Error
from slyguy.util import strip_namespaces, jwt_data

from .constants import HEADERS, API_URL, CHANNELS_URL, CONTENT_URL, PLAY_URL, WIDEVINE_URL
from .language import _

class APIError(Error):
    pass

class API(object):
    def new_session(self):
        self.logged_in = False

        ## Legacy ##
        userdata.delete('pswd')
        userdata.delete('access_token')
        ############

        self._session = Session(HEADERS, base_url=API_URL)
        self._set_authentication()

    def _set_authentication(self):
        token = userdata.get('sky_token')
        if not token:
            return

        self._session.cookies.update({'sky-access': token})
        self.logged_in = True

    def series(self, id):
        return self._session.get(CONTENT_URL + id).json()

    def content(self, section='', text='', genre='', channels='', start=0):
        params = {
            'genre': genre,
            'rating': '',
            'text': text,
            'sortBy': 'TITLE',
            'title': '',
            'lastChance': 'false',
            'type': '',
            'channel': channels,
            'section': section,
            'size': 200,
            'start': start,
        }

        return self._session.get(CONTENT_URL, params=params).json()

    def channels(self):
        return self._session.get(CHANNELS_URL).json()['entries']
        
    def login(self, username, password):
        session = self._session.get('/login/initSession').json()

        data = {
            'authType': 'signIn',
            'rememberMe': True,
            'sessionJwt': session['sessionJwt'],
            'username': username,
            'password': password,
        }

        resp = self._session.post('/login/signin', json=data)
        self._process_login(resp)

    def _process_login(self, resp):
        data = resp.json()

        if not resp.ok or 'sky-access' not in resp.cookies:
            raise APIError(_(_.LOGIN_ERROR, message=data.get('message')))

        token = resp.cookies['sky-access']

        userdata.set('sky_token', token)
        userdata.set('device_id', data['deviceId'])

        if 'profileId' in data:
            userdata.set('profile_id', data['profileId'])

        jwt = jwt_data(token)
        userdata.set('token_expires', jwt['exp'])

        self._set_authentication()
        self._get_play_token()
        self._subscriptions()

    def _renew_token(self):
        if time.time() < userdata.get('token_expires'):
            return

        data = {
            'authType': 'renew',
            'deviceID': userdata.get('device_id'),
            'profileId': userdata.get('profile_id'),
            'rememberMe': True,
        }

        resp = self._session.post('/login/renew', json=data)
        self._process_login(resp)

    def _subscriptions(self):
        data = self._session.get('/entitlements/v2/onlineSubscriptions', params={'profileId': userdata.get('profile_id')}).json()
        userdata.set('subscriptions', data['onlineSubscriptions'])

    def _get_play_token(self):
        params = {
            'profileId':   userdata.get('profile_id'),
            'deviceId':    userdata.get('device_id'),
            'partnerId':   'skygo',
            'description': 'undefined undefined undefined',
        }

        resp = self._session.get('/mpx/v1/token', params=params)
        data = resp.json()

        if not resp.ok or 'token' not in data:
            raise APIError(_(_.TOKEN_ERROR, message=data.get('message')))

        userdata.set('play_token', data['token'])

    def _concurrency_unlock(self, root):
        concurrency_url = root.find("./head/meta[@name='concurrencyServiceUrl']").attrib['content']
        lock_id         = root.find("./head/meta[@name='lockId']").attrib['content']
        lock_token      = root.find("./head/meta[@name='lockSequenceToken']").attrib['content']
        lock            = root.find("./head/meta[@name='lock']").attrib['content']

        params = {
            'schema': '1.0',
            'form': 'JSON',
            '_clientId': 'playerplayerHTML',
            '_id': lock_id,
            '_sequenceToken': lock_token,
            '_encryptedLock': lock,
            'httpError': False,
        }
        
        return self._session.get('{}/web/Concurrency/unlock'.format(concurrency_url), params=params).json()

    def play_media(self, id):
        self._renew_token()

        params = {
            'form': 'json',
            'types': None,
            'fields': 'id,content',
            'byId': id,
        }

        data = self._session.get(PLAY_URL, params=params).json()

        if not data['entries']:
            raise APIError(_.VIDEO_UNAVAILABLE)

        videos = data['entries'][0]['media$content']

        chosen = videos[0]
        for video in videos:
            if video['plfile$format'].upper() == 'MPEG-DASH':
                chosen = video
                break

        if chosen['plfile$format'].upper() == 'F4M':
            raise APIError(_.ADOBE_ERROR)

        params = {
            'auth': userdata.get('play_token'), 
            'formats': 'mpeg-dash', 
            'tracking': True, 
            'format': 'SMIL'
        }

        resp = self._session.get(chosen['plfile$url'], params=params)

        root = ET.fromstring(resp.text)
        strip_namespaces(root)

        if root.find("./body/seq/ref/param[@name='exception']") != None:
            error_msg = root.find("./body/seq/ref").attrib.get('abstract')
            raise APIError(_(_.PLAY_ERROR, message=error_msg))

        try:
            data = self._concurrency_unlock(root)
        except Exception as e:
            log.debug('Failed to get concurrency lock. Attempting to continue without it...')
            log.exception(e)

        ref = root.find(".//switch/ref")
        url = ref.attrib['src']

        tracking = {}
        for item in ref.find("./param[@name='trackingData']").attrib['value'].split('|'):
            key, value = item.split('=')
            tracking[key] = value
            
        license = WIDEVINE_URL.format(token=userdata.get('play_token'), pid=tracking['pid'], challenge='B{SSM}')

        return url, license

    def logout(self):
        userdata.delete('device_id')
        userdata.delete('profile_id')
        userdata.delete('play_token')
        userdata.delete('token_expires')
        userdata.delete('sky_token')
        userdata.delete('subscriptions')
        self.new_session()