import json
import arrow

from slyguy import userdata, mem_cache
from slyguy.session import Session
from slyguy.exceptions import Error
from slyguy.util import hash_6

from .constants import *
from .language import _


class APIError(Error):
    pass


class API(object):
    def new_session(self):
        self.logged_in = False

        self._session = Session(HEADERS, base_url=API_URL)

        if userdata.get('singtel_tv_no'):
            self.logged_in = True

    def login(self, singtel_tv_no, identification_no):
        self.logout()

        device_id = hash_6(singtel_tv_no, length=16)

        payload = {
            'deviceType': APP_DEVICE,
            'deviceId': device_id,
            'identityType': APP_ID_TYPE,
            'identityId': identification_no,
            'iptvNo': singtel_tv_no,
            'appId': APP_ID,
            'appKey': APP_KEY,
            'mode': APP_MODE,
            'ver': APP_VER,
        }

        data = self._session.post('/HomeLoginService.aspx', data={'JSONtext': json.dumps(payload)}).json()['item'][0]
        if data.get('StatusCode'):
            raise APIError(_.LOGIN_ERROR)

        userdata.set('device_id', device_id)
        userdata.set('singtel_tv_no', singtel_tv_no)
        userdata.set('identification_no', identification_no)

        return data

    @mem_cache.cached(60*5)
    def channels(self):
        data      = self._session.gz_json(DATA_URL)
        channels  = [x for x in data['getAuthorizationResponse']['channelList'] if x['isLive'].upper() == 'Y']

        user_data = self.login(userdata.get('singtel_tv_no'), userdata.get('identification_no'))

        if user_data['OTTAccess'].upper() != 'Y':
            guest_ids = [int(x['ChannelID']) for x in user_data['guestPreviewChannels']]
            channels = [x for x in channels if x['id'] in guest_ids]
        else:
            channels = [x for x in channels if x['shortName'] in user_data['SubscribedCallLetters']]

        return channels

    def _stop_stream(self, channel_id, token):
        start = arrow.utcnow()
        end   = start.shift(seconds=10)

        payload = {
            'deviceType': APP_DEVICE,
            'deviceId': userdata.get('device_id'),
            'identityType': APP_ID_TYPE,
            'identityId': userdata.get('identification_no'),
            'iptvNo': userdata.get('singtel_tv_no'),
            'channelID': channel_id,
            'startTime': start.format('YYYY-MM-DD HH:mm:ss'),
            'stopTime': end.format('YYYY-MM-DD HH:mm:ss'),
            'bitRates': '1',
            'token': token,
            'appId': APP_ID,
            'appKey': APP_KEY,
        }

        resp = self._session.post('/LogStopStream.aspx', data={'JSONtext': json.dumps(payload)})

        return resp.ok

    def play(self, channel_id, call_letter):
        payload = {
            'deviceType': APP_DEVICE,
            'deviceId': userdata.get('device_id'),
            'identityType': APP_ID_TYPE,
            'identityId': userdata.get('identification_no'),
            'iptvNo': userdata.get('singtel_tv_no'),
            'callLetter': call_letter,
            'channelID': channel_id,
            'appId': APP_ID,
            'appKey': APP_KEY,
            'mode': APP_MODE,
            'ver': APP_VER,
        }

        data = self._session.get('/WatchOTTStreaming.aspx', data={'JSONtext': json.dumps(payload)}).json()['item'][0]
        if data.get('StatusCode'):
            raise APIError(_(_.PLAYBACK_ERROR, error=data.get('StatusDesc')))

        self._stop_stream(channel_id, data['UserToken'])

        return data
    
    def logout(self):
        userdata.delete('singtel_tv_no')
        userdata.delete('identification_no')
        userdata.delete('device_id')
        mem_cache.empty()
        self.new_session()