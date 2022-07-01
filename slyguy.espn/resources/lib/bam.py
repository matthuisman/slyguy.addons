from slyguy import mem_cache
from slyguy.exceptions import Error
from slyguy.session import Session

from .language import _

API_KEY = 'ZXNwbiZhbmRyb2lkJjEuMC4w.AL-8jWFe7X4SvBYXmEkM9raE4YLLcronwHCF8_nFvmU'
CONFIG_URL = 'https://bam-sdk-configs.bamgrid.com/bam-sdk/v3.0/espn-a9b93989/android/v6.1.0/google/tv/prod.json'
HEADERS = {
    'User-Agent': 'BAMSDK/v6.1.0 (espn-a9b93989 4.7.1.0; v3.0/v6.1.0; android; tv)',
    'x-bamsdk-client-id': 'espn-a9b93989',
    'x-bamsdk-platform': 'android-tv',
    'x-bamsdk-version': '6.1.0',
    'Accept-Encoding': 'gzip',
}

ERROR_MAP = {
    'not-entitled': _.NOT_ENTITLED,
    'blackout': _.GEO_ERROR,
}

class BamError(Error):
    pass

class Bam():
    def __init__(self):
        self._session = Session(HEADERS, timeout=30)
        self._session.headers.update({'Authorization': 'Bearer {}'.format(API_KEY)})

    def _check_errors(self, data, error=_.API_ERROR):
        if not type(data) is dict:
            return

        try:
            if data.get('status') in (400, 403):
                message = ERROR_MAP.get(data.get('exception'), data.get('message'))
                raise BamError(_(error, msg=message))

            elif data.get('errors'):
                error_msg = ERROR_MAP.get(data['errors'][0].get('code')) or data['errors'][0].get('description') or data['errors'][0].get('code')
                raise BamError(_(error, msg=error_msg))

            elif data.get('error'):
                error_msg = ERROR_MAP.get(data.get('error_code')) or data.get('error_description') or data.get('error_code')
                raise BamError(_(error, msg=error_msg))
        except:
            self.logout()
            raise

    def login(self, id_token):
        config = self._session.get(CONFIG_URL).json()

        payload = {
            'deviceFamily': 'android',
            'applicationRuntime': 'android',
            'deviceProfile': 'tv',
            'attributes': {},
        }

        endpoint = config['services']['device']['client']['endpoints']['createDeviceGrant']['href']
        device_data = self._session.post(endpoint, json=payload, timeout=20).json()
        self._check_errors(device_data)

        payload = {
            'subject_token': device_data['assertion'],
            'subject_token_type': 'urn:bamtech:params:oauth:token-type:device',
            'platform': 'android',
            'grant_type': 'urn:ietf:params:oauth:grant-type:token-exchange',
        }

        endpoint = config['services']['token']['client']['endpoints']['exchange']['href']
        data = self._session.post(endpoint, data=payload).json()
        self._check_errors(data)

        payload = {
            'id_token': id_token,
        }

        endpoint = config['services']['account']['client']['endpoints']['createAccountGrant']['href']
        grant_data = self._session.post(endpoint, json=payload, headers={'Authorization': data['access_token']}).json()
        self._check_errors(grant_data)

        payload = {
            'subject_token': grant_data['assertion'],
            'subject_token_type': 'urn:bamtech:params:oauth:token-type:account',
            'platform': 'android',
            'grant_type': 'urn:ietf:params:oauth:grant-type:token-exchange',
        }

        endpoint = config['services']['token']['client']['endpoints']['exchange']['href']
        data = self._session.post(endpoint, data=payload).json()
        self._check_errors(data)

        mem_cache.set('espn_token', data['access_token'], data['expires_in'] - 15)
        return data['access_token']

    @property
    def token(self):
        return mem_cache.get('espn_token')

    def playback(self, source_url, token):
        headers = {'accept': 'application/vnd.media-service+json; version=5', 'Authorization': token}
        data = self._session.get(source_url.format(scenario='ctr-regular'), headers=headers).json()
        self._check_errors(data)

        data = {
            'url': data['stream']['complete'][0]['url'],
            'type': 'HLS',
            'headers': {
                'authorization': token,
            }
        }

        return data

    def logout(self):
        mem_cache.delete('espn_token')
