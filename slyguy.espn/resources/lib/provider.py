import uuid
import hashlib
import hmac
import base64
from time import time
from contextlib import contextmanager

from slyguy import mem_cache, userdata
from slyguy.log import log
from slyguy.session import Session

from .util import check_errors

CONFIG_URL = 'https://secure.espncdn.com/connected-devices/app-configurations/watchespn-androidtv-3.23.config.json'
HEADERS = {
    'User-Agent': 'ESPN/4.7.1 Dalvik/2.1.0 (Linux; U; Android 8.1.0;)',
}

class Provider(object):
    def __init__(self):
        self._session = Session(HEADERS, timeout=30)
        self.logged_in = userdata.get('provider_device_id') != None

    @mem_cache.cached(60*60)
    def _config(self):
        return self._session.get(CONFIG_URL).json()

    def _generate_message(self, method, path):
        config = self._config()['adobePass']

        message = '{method} requestor_id={requestor_id}, nonce={nonce}, signature_method=HMAC-SHA1, request_time={time}, request_uri={path}'.format(
            method=method, requestor_id=config['requestorId'], nonce=uuid.uuid4(), time=int(time() * 1000), path=path,
        )

        signature = hmac.new(config['consumerSecretKey'].encode('utf-8'), message.encode('utf-8'), hashlib.sha1)
        signature = base64.b64encode(signature.digest()).decode('utf-8')
        message = '{message}, public_key={consumer_key}, signature={signature}'.format(message=message, consumer_key=config['consumerKey'], signature=signature)

        return message

    @contextmanager
    def login(self):
        self.logout()

        config = self._config()['adobePass']

        path = '/regcode'
        device_id = str(uuid.uuid1().hex)[:16]

        params = {
            'deviceId': device_id,
            'deviceType': config['deviceType'],
        }

        headers = {
            'Authorization': self._generate_message('POST', path),
            'Accept': 'application/json; charset=utf-8',
        }

        data = self._session.post('{}/reggie/v1/{}{}'.format(config['serviceUrl'], config['requestorId'], path), params=params, headers=headers).json()
        data['device_id'] = device_id

        try:
            yield data
        finally:
            try:
                self.delete_code(data['code'])
            except Exception as e:
                log.debug('failed to delete reg code')

    def authenticate(self, device_id):
        config = self._config()['adobePass']
        path = '/tokens/authn'

        params = {
            'deviceId': device_id,
            'requestor': config['requestorId'],
        }

        headers = {
            'Authorization': self._generate_message('GET', path),
            'Accept': 'application/json; charset=utf-8',
        }

        resp = self._session.get('{}/api/v1{}'.format(config['serviceUrl'], path), params=params, headers=headers)
        if resp.ok:
            data = resp.json()
            expires = int(data['expires'])
            userdata.set('provider_device_id', device_id)
            return True

    def re_authenticate(self):
        self.authenticate(userdata.get('provider_device_id'))

    def delete_code(self, code):
        config = self._config()['adobePass']
        path = '/regcode/{}'.format(code)

        headers = {
            'Authorization': self._generate_message('DELETE', path),
            'Accept': 'application/json; charset=utf-8',
        }

        resp = self._session.delete('{}/reggie/v1/{}{}'.format(config['serviceUrl'], config['requestorId'], path), headers=headers, timeout=10)
        return resp.ok

    def token(self, resource):
        self.re_authenticate()

        config = self._config()['adobePass']

        path = '/authorize'
        params = {
            'deviceId': userdata.get('provider_device_id'),
            'requestor': config['requestorId'],
            'resource': resource,
        }
        headers = {
            'Authorization': self._generate_message('GET', path),
            'Accept': 'application/json; charset=utf-8',
        }

        data = self._session.get('{}/api/v1{}'.format(config['serviceUrl'], path), params=params, headers=headers).json()
        check_errors(data)

        path = '/tokens/media'
        params = {
            'deviceId': userdata.get('provider_device_id'),
            'requestor': config['requestorId'],
            'resource': data['resource'],
        }
        headers = {
            'Authorization': self._generate_message('GET', path),
            'Accept': 'application/json; charset=utf-8',
        }

        data = self._session.get('{}/api/v1{}'.format(config['serviceUrl'], path), params=params, headers=headers).json()
        check_errors(data)

        return data

    def _logout(self, device_id):
        if not device_id:
            return

        config = self._config()['adobePass']

        path = '/logout'
        params = {
            'deviceId': device_id,
        }
        headers = {
            'Authorization': self._generate_message('DELETE', path),
            'Accept': 'application/json; charset=utf-8',
        }

        self._session.delete('{}/api/v1{}'.format(config['serviceUrl'], path), params=params, headers=headers)

    def logout(self):
        device_id = userdata.get('provider_device_id')
        userdata.delete('provider_device_id')
        self._logout(device_id)
