import arrow
import uuid

from slyguy import userdata
from slyguy.session import Session
from slyguy.exceptions import Error
from slyguy.log import log

from .constants import *
from .language import _

class APIError(Error):
    pass

class API(object):
    def new_session(self):
        self.logged_in = False
        self._session = Session(HEADERS)
        self._set_authentication()
        
    def _set_authentication(self):
        access_token = userdata.get('access_token')
        if not access_token:
            return
        
        config = self._get_config()
        self._session._base_url = config['baseApiUrl'] + '{}'
        self._session.headers.update({
            'authorization': 'Bearer {}'.format(access_token),
            'x-device-info': '{}/{} (unknown/sdk_google_atv_x86; ANDROIDTV/27; {}/{})'.format(SITE_ID, APP_VERSION, userdata.get('device_id'), CLIENT_ID),
            'x-disco-params': 'realm={},siteLookupKey={},features=ar,hth={},bid={}'.format(config['realm'], SITE_ID, config['mainTerritoryCode'], BID)
        })
        self.logged_in = True
        
    def _device_id(self):
        return str(uuid.uuid1())

    def _get_config(self):
        # config = userdata.get('config')
        # if not config:
        #     data = self._session.get(BOOTSTRAP_URL).json()
        #     config = data['data']['attributes']
        #     userdata.set('config', config)
        # return config
        return CONFIG

    def device_code(self):
        self.logout()

        data = self._session.get(BOOTSTRAP_URL).json()
        config = self._get_config()
        
        device_id = self._device_id()
        userdata.set('device_id', device_id)

        self._session.headers.update({
            'x-device-info': '{}/{} (unknown/sdk_google_atv_x86; ANDROIDTV/27; {}/{})'.format(SITE_ID, APP_VERSION, device_id, CLIENT_ID),
            'x-disco-params': 'realm={},siteLookupKey={},features=ar,hth={},bid={}'.format(config['realm'], SITE_ID, config['mainTerritoryCode'], BID),
        })
        
        params = {
            'realm': config['realm'],
            'deviceId': device_id,
        }

        data = self._session.get('{}/token'.format(config['baseApiUrl']), params=params).json()
        token = data['data']['attributes']['token']
        self._session.headers['authorization'] = 'Bearer {}'.format(token)
        
        auth_config = self._session.get('{}/cms/configs/auth'.format(config['baseApiUrl'])).json()['data']['attributes']['config']

        payload = {
            "gauthPayload": {
                "brandId": auth_config['brandId'],
                "partnerId": ""
            }
        }
        
        data = self._session.post('{}/authentication/linkDevice/initiate'.format(config['baseApiUrl']), json=payload).json()
        self._check_errors(data)
        return data['data']['attributes']['linkingCode']
        
    def device_login(self):
        resp = self._session.post('{}/authentication/linkDevice/login'.format(self._get_config()['baseApiUrl']))
        if resp.status_code == 204:
            return False
        elif resp.status_code != 200:
            raise APIError('Failed to login :(')
        
        data = resp.json()
        self._check_errors(data)
        token = data['data']['attributes']['token']
        self._session.headers['authorization'] = 'Bearer {}'.format(token)
        userdata.set('access_token', token)
        return True
    
    def _check_errors(self, data):
        if 'errors' in data:
            raise APIError(data['errors'][0]['detail'])

    def channel_data(self):
        return self._session.gz_json(LIVE_DATA_URL)

    def live_channels(self):
        params = {
            'include': 'default',
            'decorators': 'iewingHistory,isFavorite,playbackAllowed',
        }
        data = self._session.get('/cms/routes/channel/hgtv', params=params).json()
        self._check_errors(data)
        
        included = {}
        channel_order = []
        for row in data['included']:
            included[row['id']] = row
            if 'attributes' in row and 'name' in row['attributes'] and row['attributes']['name'] == 'channel-selector':
                channel_order = [x['id'] for x in row['relationships']['items']['data']]

        channels = []
        for _id in channel_order:
            include = included[_id]
            channel_id = include['relationships']['channel']['data']['id']
            if channel_id in included: 
                channel = included[channel_id]
                channel['images'] = [included[x['id']]['attributes'] for x in channel['relationships']['images']['data']]
                if channel['attributes']['hasLiveStream'] and channel['attributes']['playbackAllowed']:
                    channels.append(included[channel_id])

        return channels
    
    def play_channel(self, channel_id):
        payload = {
            "channelId": channel_id,
            "deviceInfo": {
                "adBlocker": False,
                "drmSupported": True,
                "hdrCapabilities": ["SDR"],
                "hwDecodingCapabilities": [],
                "player": {
                    "width": 3840,
                    "height": 2160
                },
                "screen":{
                    "width": 3840,
                    "height": 2160
                },
                "soundCapabilities": ["STEREO"],
            },
        }
        
        data = self._session.post('/playback/v3/channelPlaybackInfo', json=payload).json()
        self._check_errors(data)
        return data['data']['attributes']['streaming'][0]['url']

    def logout(self):
        userdata.delete('access_token')
        userdata.delete('device_id')
        userdata.delete('config')
        self.new_session()
