import uuid
import json
import threading
from contextlib import contextmanager

import websocket
from slyguy.session import Session
from slyguy import userdata
from slyguy.exceptions import Error

from .bam import Bam

API_URL = 'https://registerdisney.go.com/jgc/v8/client/ESPN-OTT.GC.ANDTV-PROD{}'
HEADERS = {
    'User-Agent': 'ESPN/4.7.1 Dalvik/2.1.0 (Linux; U; Android 8.1.0;)',
    'always-ok-response': 'true',
}

class ESPN(object):
    def __init__(self):
        self._bam = Bam()
        self._session = Session(headers=HEADERS, base_url=API_URL, timeout=30)
        self.logged_in = userdata.get('espn_refresh') != None

    def _get_id_token(self):
        payload = {
            'refreshToken': userdata.get('espn_refresh'),
        }

        data = self._session.post('/guest/refresh-auth', json=payload).json()
        if not data['data']:
            try: error = data['error']['errors'][0]['code']
            except: error = 'Failed to refresh token'
            raise Error(error)

        token_data = data['data']['token']
        self._set_tokens(token_data)
        return token_data['id_token']

    def _set_tokens(self, data):
        userdata.set('espn_swid', data['swid'])
        userdata.set('espn_token', data['access_token'])
        userdata.set('espn_refresh', data['refresh_token'])

    def playback(self, source_url):
        token = self._bam.token
        if not token:
            id_token = self._get_id_token()
            token = self._bam.login(id_token)

        return self._bam.playback(source_url, token)

    @contextmanager
    def login(self):
        self.logout()

        device_id = str(uuid.uuid1().hex)

        payload = {
            'content': {
                'adId': device_id,
                'correlation-id': device_id,
                'deviceId': device_id,
                'deviceType': 'ANDTV',
                'entitlementPath': 'login',
                'entitlements': [],
            },
            'ttl': 0
        }

        data = self._session.post('/license-plate', json=payload).json()['data']

        code = data['pairingCode']
        fastcast_host = data['fastCastHost']
        fastcast_profile_id = data['fastCastProfileId']
        fastcast_topic = data['fastCastTopic']

        data = self._session.get(fastcast_host + '/public/websockethost').json()
        url = "wss://{host}:{port}/FastcastService/pubsub/profiles/{profile_id}?TrafficManager-Token={token}".format(
            host=data['ip'], port=data['securePort'], profile_id=fastcast_profile_id, token=data['token'])

        login = ESPNLogin(code, fastcast_topic, url)

        try:
            yield login
        finally:
            login.stop()

        if login.result:
            data = login.token_data()
            self._set_tokens(data)

    def _logout(self, token, swid):
        payload = {
            'tokens': [token,],
        }

        self._session.post('/guest/{}/logout'.format(swid), json=payload)

    def logout(self):
        self._bam.logout()

        token = userdata.get('espn_token')
        swid = userdata.get('espn_swid')

        userdata.delete('espn_swid')
        userdata.delete('espn_token')
        userdata.delete('espn_refresh')

        if token and swid:
            self._logout(token, swid)

class ESPNLogin(object):
    def __init__(self, code, topic, url):
        self._code = code
        self._topic = topic
        self._url = url

        self._token_data = None
        self._stop = False
        self._ws = None

        self._thread = threading.Thread(target=self._worker)
        self._thread.daemon = True
        self._thread.start()

    def token_data(self):
        return self._token_data

    def is_alive(self):
        return self._thread.is_alive()

    @property
    def code(self):
        return self._code

    @property
    def result(self):
        return self._token_data is not None

    def stop(self):
        self._stop = True
        if self._ws:
            self._ws.close()
        self._thread.join()

    def _worker(self):
        while not self._stop:
            self._ws = websocket.create_connection(self._url, suppress_origin=True)
            self._ws.send(json.dumps({'op': 'C'}))

            while not self._stop:
                try:
                    data = json.loads(self._ws.recv())
                    if 'op' not in data:
                        continue

                    if data['op'] == 'C':
                        ret = {
                            'op': 'S',
                            'sid': data['sid'],
                            'tc': self._topic,
                            'rc': 200
                        }
                        self._ws.send(json.dumps(ret))

                    elif data['op'] == 'P':
                        self._token_data = json.loads(data['pl'])
                        return

                except:
                    break
