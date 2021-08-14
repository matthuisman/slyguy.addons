import time
from threading import Thread

import requests

from slyguy.session import Session
from slyguy.exceptions import Error

class MVPDError(Error):
    pass

class MVPD(object):
    def __init__(self, config):
        self._session = Session(base_url='https://auth.mtvnservices.com{}')
        self._config = config
        self._client_id = 'paramount-plus-androidtv-intl'
        self._auth_group = 'paramountplus'
        self._token_data = None
        self._refresh_token()

    def _refresh_token(self):
        payload = {}
        url = '/accessToken'
        if self._token_data:
            payload['refreshToken'] = self._token_data['deviceRefreshToken']
            url += '/refresh'

        params = {
            'clientId': self._client_id,
            'countryCode': self._config.country_code,
        }

        self._token_data = self._session.post(url, params=params, json=payload).json()
        self._session.headers.update({'authorization': 'Bearer {}'.format(self._token_data['applicationAccessToken'])})

    def providers(self):
        params = {
            'filterType': 'top',
            'logoSchema': 'white',
            'clientId': self._client_id,
            'countryCode': self._config.country_code,
        }

        return self._session.get('/mvpd', params=params).json()['providers']

    def code(self, provider):
        params = {
            'clientId': self._client_id,
            'countryCode': self._config.country_code,
        }

        data = self._session.post('/access/activationCode', params=params, json={'mvpdCode': provider['code']}).json()
        code = data['activationCode']
        url = data['activationUrl']

        if not url.startswith('https'):
            if not url.startswith('www.'):
                url = 'www.'+url
            url = 'https://{}'.format(url)

        return code, url

    def wait_login(self, code):
        def wait_thread():
            params = {
                'logoSchema': 'white',
                'clientId': self._client_id,
                'countryCode': self._config.country_code,
                'waitWithLastKnownStatus': 'notStarted',
            }

            last_call = time.time()-10

            while True:
                if (time.time() - last_call) < 5:
                    time.sleep(1)
                    continue

                last_call = time.time()
                try:
                    result = self._session.get('/access/activationCode/{}'.format(code), params=params, timeout=(10, 40), attempts=1).json()
                except requests.exceptions.RequestException as e:
                    continue

                if result.get('status') == 'succeeded' or result.get('errorCode') == 'NeedsRefresh':
                    return
                elif not result.get('status'):
                    continue
                else:
                    params['waitWithLastKnownStatus'] = result['status']

        thread = Thread(target=wait_thread)
        thread.daemon = True
        thread.start()
        return thread

    def authorize(self):
        self._refresh_token()

        params = {
            'clientId': self._client_id,
            'countryCode': self._config.country_code,
        }

        data = self._session.get('/access/authorization/{}'.format(self._auth_group), params=params).json()
        if data.get('errorCode'):
            raise MVPDError(data['errorCode'])

        self._refresh_token()
        return self._token_data['applicationAccessToken']

    # def status(self):
    #     params = {
    #         'logoSchema': 'white',
    #         'clientId': self._client_id,
    #         'countryCode': self._config.country_code,
    #     }

    #     return self._session.get('/access/status', params=params).json()
