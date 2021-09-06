import hashlib
import uuid

import arrow
import pyaes

from slyguy import userdata, gui, settings, mem_cache
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
        self._session = Session(HEADERS, base_url=API_URL)
        self.logged_in = userdata.get('token') != None

    def _refresh_token(self):
        payload = {
            'username': userdata.get('username'),
            'loginToken': userdata.get('token'),
            'deviceId': userdata.get('deviceid'),
            'accountType': 'foxtel',
            'format': 'json',
            'appID': 'GO2',
            'plt': PLT_DEVICE,
        }

        password = userdata.get('pswd')
        if password:
            log.debug('Using Password Login')
            payload['password'] = self._hex_password(password, userdata.get('deviceid'))
            del payload['loginToken']
        else:
            log.debug('Using Token Login')

        data = self._session.post('/auth.class.api.php/logon/{site_id}'.format(site_id=VOD_SITEID), data=payload).json()

        response = data['LogonResponse']
        error = response.get('Error')
        success = response.get('Success')

        if error:
            self.logout()
            raise APIError(_(_.TOKEN_ERROR, msg=error.get('Message')))

        userdata.set('token', success['LoginToken'])
        userdata.set('deviceid', success['DeviceId'])
        userdata.set('entitlements', success.get('Entitlements', ''))

        self.logged_in = True

    def login(self, username, password, kickdevice=None):
        self.logout()

        raw_id = self._format_id(settings.get('device_id')).lower()
        device_id = hashlib.sha1(raw_id.encode('utf8')).hexdigest()

        log.debug('Raw device id: {}'.format(raw_id))
        log.debug('Hashed device id: {}'.format(device_id))

        hex_password = self._hex_password(password, device_id)

        payload = {
            'username': username,
            'password': hex_password,
            'deviceId': device_id,
            'accountType': 'foxtel',
            'format': 'json',
            'appID': 'GO2',
            'plt': PLT_DEVICE,
        }

        if kickdevice:
            payload['deviceToKick'] = kickdevice
            log.debug('Kicking device: {}'.format(kickdevice))

        data = self._session.post('/auth.class.api.php/logon/{site_id}'.format(site_id=VOD_SITEID), data=payload).json()

        response = data['LogonResponse']
        devices = response.get('CurrentDevices', [])
        error = response.get('Error')
        success = response.get('Success')

        if error:
            if not devices or kickdevice:
                raise APIError(_(_.LOGIN_ERROR, msg=error.get('Message')))

            options = [d['Nickname'] for d in devices]
            index = gui.select(_.DEREGISTER_CHOOSE, options)
            if index < 0:
                raise APIError(_(_.LOGIN_ERROR, msg=error.get('Message')))

            kickdevice = devices[index]['DeviceID']

            return self.login(username, password, kickdevice=kickdevice)

        userdata.set('token', success['LoginToken'])
        userdata.set('deviceid', success['DeviceId'])
        userdata.set('entitlements', success.get('Entitlements', ''))

        if settings.getBool('save_password', False):
            userdata.set('pswd', password)
            log.debug('Password Saved')

        self.logged_in = True

    def _format_id(self, string):
        try:
            mac_address = uuid.getnode()
            if mac_address != uuid.getnode():
                mac_address = ''
        except:
            mac_address = ''

        system, arch = get_system_arch()

        return string.format(username=userdata.get('username'), mac_address=mac_address, system=system).strip()

    def _hex_password(self, password, device_id):
        nickname = self._format_id(settings.get('device_name'))
        log.debug('Device nickname: {}'.format(nickname))

        payload = {
            'deviceId': device_id,
            'nickName': nickname,
            'format': 'json',
            'appID': 'GO2',
            'accountType': 'foxtel',
            'plt': PLT_DEVICE,
        }

        secret = self._session.post('/auth.class.api.php/prelogin/{site_id}'.format(site_id=VOD_SITEID), data=payload).json()['secret']
        log.debug('Pass Secret: {}{}'.format(secret[:5], 'x'*len(secret[5:])))

        try:
            #python3
            iv = bytes.fromhex(AES_IV)
        except AttributeError:
            #python2
            iv = str(bytearray.fromhex(AES_IV))

        encrypter = pyaes.Encrypter(pyaes.AESModeOfOperationCBC(secret.encode('utf8'), iv))

        ciphertext = encrypter.feed(password)
        ciphertext += encrypter.feed()

        try:
            #python3
            hex_password = ciphertext.hex()
        except AttributeError:
            #python2
            hex_password = ciphertext.encode('hex')

        log.debug('Hex password: {}{}'.format(hex_password[:5], 'x'*len(hex_password[5:])))

        return hex_password

    def assets(self, asset_type, _filter=None, showall=False):
        params = {
            'showall': showall,
            'plt': PLT_DEVICE,
            'entitlementToken': self._entitlement_token(),
            'sort': 'latest',
            'format': 'json',
            'appID': 'GO2',
            'serviceID': 'PLAY',
        }

        if _filter:
            params['filters'] = _filter

        return self._session.get('/categoryTree.class.api.php/GOgetAssets/{site_id}/{asset_type}'.format(site_id=VOD_SITEID, asset_type=asset_type), params=params, timeout=20).json()

    def live_channels(self, _filter=None):
        params = {
            'plt': PLT_DEVICE,
            'entitlementToken': self._entitlement_token(),
            'format': 'json',
            'appID': 'GO2',
            'serviceID': 'PLAY',
        }

        if _filter:
            params['filter'] = _filter

        return self._session.get('/categoryTree.class.api.php/GOgetLiveChannels/{site_id}'.format(site_id=LIVE_SITEID), params=params).json()

    def show(self, show_id):
        params = {
            'showId': show_id,
            'plt': PLT_DEVICE,
            'format': 'json',
            'dateFormat': 'ISO8601',
            'appID': 'GO2',
            'serviceID': 'PLAY',
        }

        return self._session.get('/asset.class.api.php/GOgetAssetData/{site_id}/0'.format(site_id=VOD_SITEID), params=params).json()

    def asset(self, media_type, id):
        params = {
            'plt': PLT_DEVICE,
            'format': 'json',
            'dateFormat': 'ISO8601',
            'appID': 'GO2',
            'serviceID': 'PLAY',
        }

        if media_type == TYPE_VOD:
            site_id = VOD_SITEID
        else:
            site_id = LIVE_SITEID

        return self._session.get('/asset.class.api.php/GOgetAssetData/{site_id}/{id}'.format(site_id=site_id, id=id), params=params).json()

    def bundle(self, mode=''):
        params = {
            'plt': PLT_DEVICE,
            'entitlementToken': self._entitlement_token(),
            'apiVersion': 2,
            'filter': '',
            'mode': mode,
            'format': 'json',
            'appID': 'GO2',
            'serviceID': 'PLAY',
        }

        return self._session.get(BUNDLE_URL, params=params).json()

    def _sync_token(self, site_id, catalog_name):
        self._refresh_token()

        params = {
            'serviceID': 'PLAY',
        }

        payload = {
            'loginToken': userdata.get('token'),
            'deviceId': userdata.get('deviceid'),
            'format': 'json',
        }

        vod_token = None
        live_token = None

        data = self._session.post('/userCatalog.class.api.php/getSyncTokens/{site_id}'.format(site_id=VOD_SITEID), params=params, data=payload).json()

        for token in data.get('tokens', []):
            if token['siteId'] == site_id and token['catalogName'] == catalog_name:
                return token['token']

        return None

    def user_catalog(self, catalog_name, site_id=VOD_SITEID):
        token = self._sync_token(site_id, catalog_name)
        if not token:
            return

        params = {
            'syncToken': token,
            'platform': PLT_DEVICE,
            'limit': 100,
            'format': 'json',
            'appID': 'GO2',
            'serviceID': 'PLAY',
        }

        return self._session.get('/userCatalog.class.api.php/getCarousel/{site_id}/{catalog_name}'.format(site_id=site_id, catalog_name=catalog_name), params=params).json()

    @mem_cache.cached(60*5)
    def channel_data(self):
        try:
            return self._session.get(LIVE_DATA_URL).json()
        except:
            return {}

    def search(self, query, _type='VOD'):
        params = {
            'prod': 'FOXTELGO',
            'idm': '04',
            'BLOCKED': 'YES',
            'fx': '"{}"'.format(query),
            'sfx': 'type:{}'.format(_type), #VOD OR LINEAR
            'limit': 100,
            'offset': 0,
            'dpg': 'R18+',
            'ao': 'N',
            'dopt': '[F0:11]',
            'hwid': '_',
            'REGION': '_',
            'utcOffset': '+1200',
            'swver': '3.3.7',
            'aid': '_',
            'fxid': '_',
            'rid': 'SEARCH5',
        }

        return self._session.get(SEARCH_URL, params=params).json()

    def play(self, media_type, id):
        self._refresh_token()

        payload = {
            'deviceId': userdata.get('deviceid'),
            'loginToken': userdata.get('token'),
        }

        if media_type == TYPE_VOD:
            endpoint = 'GOgetVODConfig'
            site_id = VOD_SITEID
        else:
            endpoint = 'GOgetLiveConfig'
            site_id = LIVE_SITEID

        params = {
            'rate': 'WIREDHIGH',
            'plt': 'ipstb',
            'appID': 'PLAY2',
            'deviceCaps': hashlib.md5('TR3V0RwAZH3r3L00kingA7SumStuFF{}'.format('L1').encode('utf8')).hexdigest().lower(),
            'format': 'json',
        }

        data = self._session.post(PLAY_URL.format(endpoint=endpoint, site_id=site_id, id=id), params=params, data=payload).json()

        error = data.get('errorMessage')

        if error:
            raise APIError(_(_.PLAYBACK_ERROR, msg=error))

        streams = sorted(data['media'].get('streams', []), key=lambda s: STREAM_PRIORITY.get(s['profile'].upper(), STREAM_PRIORITY['DEFAULT']), reverse=True)
        if not streams:
            raise APIError(_.NO_STREAM_ERROR)

        playback_url = streams[0]['url']
        playback_url = playback_url.replace('cm=yes&','') #without this = bad widevine key

        ## Get L3 License URL
        params['plt'] = 'andr_phone'
        params['appID'] = 'PLAY2'
        data = self._session.post(LICENSE_URL.format(endpoint=endpoint, site_id=site_id, id=id), params=params, data=payload).json()
        license_url = data['fullLicenceUrl']
        #######

        params = {
            'sessionId': data['general']['sessionID'],
            'deviceId': userdata.get('deviceid'),
            'loginToken': userdata.get('token'),
            'sessionStatus': 'FINISHED',
            'appID': 'GO2',
            'serviceID': 'GO',
            'format': 'json',
        }

        url = '/playback.class.api.php/GOupdateSession/{}/{}'.format(data['general']['siteID'], data['general']['assetID'])
        self._session.get(url, params=params).json()

        return playback_url, license_url

    def asset_for_program(self, show_id, program_id):
        show = self.show(show_id)

        if show.get('programId') == program_id:
            return show

        if 'childAssets' not in show:
            return None

        for child in show['childAssets']['items']:
            if child.get('programId') == program_id:
                return child

            if 'childAssets' not in child:
                return None

            for subchild in child['childAssets']['items']:
                if subchild.get('programId') == program_id:
                    return subchild

        return None

    def _entitlement_token(self):
        entitlements = userdata.get('entitlements')
        if not entitlements:
            return None

        return hashlib.md5(entitlements.encode('utf8')).hexdigest()

    def logout(self):
        userdata.delete('token')
        userdata.delete('deviceid')
        userdata.delete('pswd')
        userdata.delete('entitlements')
        self.new_session()
