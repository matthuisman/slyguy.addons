import uuid
from time import time

from slyguy import userdata, mem_cache, log
from slyguy.session import Session
from slyguy.exceptions import Error

import arrow

from . import queries
from .constants import *
from .language import _
from .settings import settings


class APIError(Error):
    pass


ERROR_MAP = {
    'not-entitled': _.NOT_ENTITLED,
    'idp.error.identity.bad-credentials': _.BAD_CREDENTIALS,
    'account.profile.pin.invalid': _.BAD_PIN,
}


class API(object):
    def new_session(self):
        self._session = Session(HEADERS, timeout=30)
        self.logged_in = userdata.get('refresh_token') != None
        self._cache = {}

    @mem_cache.cached(60*10)
    def get_config(self):
        return self._session.get(CONFIG_URL).json()

    @mem_cache.cached(60*10)
    def _transaction_id(self):
        return str(uuid.uuid4())

    @property
    def session(self):
        return self._session

    def _set_authentication(self, token):
        if not token:
            return

        self._session.headers.update({'Authorization': 'Bearer {}'.format(token)})
        self._session.headers.update({'x-bamsdk-transaction-id': self._transaction_id()})

    def _set_token(self, force=False):
        if not force and userdata.get('expires', 0) > time():
            self._set_authentication(userdata.get('access_token'))
            return

        payload = {
            'operationName': 'refreshToken',
            'variables': {
                'input': {
                    'refreshToken': userdata.get('refresh_token'),
                },
            },
            'query': queries.REFRESH_TOKEN,
        }

        endpoint = self.get_config()['services']['orchestration']['client']['endpoints']['refreshToken']['href']
        data = self._session.post(endpoint, json=payload, headers={'authorization': API_KEY}).json()
        self._check_errors(data)
        self._set_auth(data['extensions']['sdk'])

    def _set_auth(self, sdk):
        self._set_authentication(sdk['token']['accessToken'])
        userdata.set('feature_flags', sdk['featureFlags'])
        userdata.set('expires', int(time() + sdk['token']['expiresIn'] - 15))
        userdata.set('access_token', sdk['token']['accessToken'])
        userdata.set('refresh_token', sdk['token']['refreshToken'])

    def register_device(self):
        self.logout()

        payload = {
            'variables': {
                'registerDevice': {
                    'applicationRuntime': 'android',
                    'attributes': {
                        'operatingSystem': 'Android',
                        'operatingSystemVersion': '8.1.0',
                    },
                    'deviceFamily': 'android',
                    'deviceLanguage': 'en',
                    'deviceProfile': 'tv',
                }
            },
            'query': queries.REGISTER_DEVICE,
        }

        endpoint = self.get_config()['services']['orchestration']['client']['endpoints']['registerDevice']['href']
        data = self._session.post(endpoint, json=payload, headers={'authorization': API_KEY}).json()
        self._check_errors(data)
        return data['extensions']['sdk']['token']['accessToken']

    def check_email(self, email, token):
        payload = {
            'operationName': 'Check',
            'variables': {
                'email': email,
            },
            'query': queries.CHECK_EMAIL,
        }

        endpoint = self.get_config()['services']['orchestration']['client']['endpoints']['query']['href']
        data = self._session.post(endpoint, json=payload, headers={'authorization': token}).json()
        self._check_errors(data)
        return data['data']['check']['operations'][0]

    def login(self, email, password, token):
        payload = {
            'operationName': 'loginTv',
            'variables': {
                'input': {
                    'email': email,
                    'password': password,
                },
            },
            'query': queries.LOGIN,
        }

        endpoint = self.get_config()['services']['orchestration']['client']['endpoints']['query']['href']
        data = self._session.post(endpoint, json=payload, headers={'authorization': token}).json()
        self._check_errors(data)
        self._set_auth(data['extensions']['sdk'])

    def request_otp(self, email, token):
        payload = {
            'operationName': 'requestOtp',
            'variables': {
                'input': {
                    'email': email,
                    'reason': 'Login',
                },
            },
            'query': queries.REQUESET_OTP,
        }

        endpoint = self.get_config()['services']['orchestration']['client']['endpoints']['query']['href']
        data = self._session.post(endpoint, json=payload, headers={'authorization': token}).json()
        self._check_errors(data)
        return data['data']['requestOtp']['accepted']

    def login_otp(self, email, passcode, token):
        payload = {
            'operationName': 'authenticateWithOtp',
            'variables': {
                'input': {
                    'email': email,
                    'passcode': passcode,
                },
            },
            'query': queries.LOGIN_OTP,
        }

        endpoint = self.get_config()['services']['orchestration']['client']['endpoints']['query']['href']
        data = self._session.post(endpoint, json=payload, headers={'authorization': token}).json()
        error = self._check_errors(data, raise_on_error=False)
        if error:
            return error

        self._login_action_grant(data['data']['authenticateWithOtp']['actionGrant'], token)

    def _login_action_grant(self, action_grant, token):
        payload = {
            'operationName': 'loginWithActionGrant',
            'variables': {
                'input': {
                    'actionGrant': action_grant,
                },
            },
            'query': queries.LOGIN_ACTION_GRANT,
        }

        endpoint = self.get_config()['services']['orchestration']['client']['endpoints']['query']['href']
        data = self._session.post(endpoint, json=payload, headers={'authorization': token}).json()
        self._check_errors(data)
        self._set_auth(data['extensions']['sdk'])

    def _check_errors(self, data, error=_.API_ERROR, raise_on_error=True):
        if not type(data) is dict:
            return

        error_msg = None
        if data.get('errors'):
            if 'extensions' in data['errors'][0]:
                code = data['errors'][0]['extensions'].get('code')
            else:
                code = data['errors'][0].get('code')

            error_msg = ERROR_MAP.get(code) or data['errors'][0].get('message') or data['errors'][0].get('description') or code
            error_msg = _(error, msg=error_msg)

        elif data.get('error'):
            error_msg = ERROR_MAP.get(data.get('error_code')) or data.get('error_description') or data.get('error_code')
            error_msg = _(error, msg=error_msg)

        elif data.get('status') == 400:
            error_msg = _(error, msg=data.get('message'))

        if error_msg and raise_on_error:
            raise APIError(error_msg)

        return error_msg

    def _json_call(self, endpoint, **kwargs):
        self._set_token()
        data = self._session.get(endpoint, **kwargs).json()
        self._check_errors(data)
        return data

    @mem_cache.cached(60*5)
    def account(self):
        self._set_token()
        endpoint = self.get_config()['services']['orchestration']['client']['endpoints']['query']['href']

        payload = {
            'operationName': 'EntitledGraphMeQuery',
            'variables': {},
            'query': queries.ENTITLEMENTS,
        }

        data = self._session.post(endpoint, json=payload).json()
        self._check_errors(data)
        return data['data']['me']

    def switch_profile(self, profile_id, pin=None):
        self._set_token()

        payload = {
            'operationName': 'switchProfile',
            'variables': {
                'input': {
                    'profileId': profile_id,
                },
            },
            'query': queries.SWITCH_PROFILE,
        }

        if pin:
            payload['variables']['input']['entryPin'] = str(pin)

        endpoint = self.get_config()['services']['orchestration']['client']['endpoints']['query']['href']
        data = self._session.post(endpoint, json=payload).json()
        self._check_errors(data)
        self._set_auth(data['extensions']['sdk'])
        mem_cache.empty()

    def set_imax(self, value):
        self._set_token()

        payload = {
            'variables': {
                'input': {
                    'imaxEnhancedVersion': value,
                },
            },
            'query': queries.SET_IMAX,
        }

        endpoint = self.get_config()['services']['orchestration']['client']['endpoints']['query']['href']
        data = self._session.post(endpoint, json=payload).json()
        self._check_errors(data)
        if data['data']['updateProfileImaxEnhancedVersion']['accepted']:
            self._set_auth(data['extensions']['sdk'])
            return True
        else:
            return False

    def _endpoint(self, href, **kwargs):
        profile, session = self.profile()

        self._cache['basic_tier'] = 'DISNEY_PLUS_NO_ADS' not in session['entitlements']
        region = session['portabilityLocation']['countryCode'] if session['portabilityLocation'] else session['location']['countryCode']
        maturity = session['preferredMaturityRating']['impliedMaturityRating'] if session['preferredMaturityRating'] else 1850
        kids_mode = profile['attributes']['kidsModeEnabled'] if profile else False
        app_language = profile['attributes']['languagePreferences']['appLanguage'] if profile else 'en-US'

        _args = {
            'apiVersion': '5.1',
            'region': region,
            'impliedMaturityRating': maturity,
            'kidsModeEnabled': 'true' if kids_mode else 'false',
            'appLanguage': app_language,
            'partner': BAM_PARTNER,
        }
        _args.update(**kwargs)
        return href.format(**_args)

    def is_subscribed(self):
        try:
            return self.profile()[1]['isSubscriber']
        except Exception as e:
            log.warning("Failed to check subscriber due to: {}".format(e))
            return True

    def profile(self):
        session = self._cache.get('session')
        profile = self._cache.get('profile')

        if not session or not profile:
            data = self.account()

            self._cache['session'] = session = data['activeSession']
            if data['account']['activeProfile']:
                for row in data['account']['profiles']:
                    if row['id'] == data['account']['activeProfile']['id']:
                        self._cache['profile'] = profile = row
                        break

        return profile, session

    def avatar_by_id(self, ids):
        endpoint = self._endpoint(self.get_config()['services']['content']['client']['endpoints']['getAvatars']['href'], avatarIds=','.join(ids))
        return self._json_call(endpoint)['data']['Avatars']

    def userstates(self, pids):
        self._set_token()
        payload = {
            'pids': pids,
        }
        endpoint = self._endpoint(self.get_config()['services']['explore']['client']['endpoints']['getUserState']['href'], version=EXPLORE_VERSION)
        data = self._session.post(endpoint, json=payload).json()
        self._check_errors(data)
        return data['data']['entityStates']

    @mem_cache.cached(60*5)
    def deeplink(self, ref_id, ref_type='deeplinkId', action='browse'):
        params = {
            'refId': ref_id,
            'refIdType': ref_type,
            'action': action,
        }
        endpoint = self._endpoint(self.get_config()['services']['explore']['client']['endpoints']['getDeeplink']['href'], version=EXPLORE_VERSION)
        return self._json_call(endpoint, params=params)['data']['deeplink']

    @mem_cache.cached(60*5)
    def page(self, page_id, limit=999, enhanced_limit=0):
        params = {
            'disableSmartFocus': 'true',
            'limit': limit,
            'enhancedContainersLimit': enhanced_limit,
        }
        endpoint = self._endpoint(self.get_config()['services']['explore']['client']['endpoints']['getPage']['href'], version=EXPLORE_VERSION, pageId=page_id)
        return self._json_call(endpoint, params=params)['data']['page']

    @mem_cache.cached(60*5)
    def set(self, set_id, limit=100, page=1):
        params = {
            'limit': limit,
            'offset': limit*(page-1),
        }
        endpoint = self._endpoint(self.get_config()['services']['explore']['client']['endpoints']['getSet']['href'], version=EXPLORE_VERSION, setId=set_id)
        return self._json_call(endpoint, params=params)['data']['set']

    @mem_cache.cached(60*5)
    def season(self, season_id, limit=100, page=1):
        params = {
            'limit': limit,
            'offset': limit*(page-1),
        }
        endpoint = self._endpoint(self.get_config()['services']['explore']['client']['endpoints']['getSeason']['href'], version=EXPLORE_VERSION, seasonId=season_id)
        return self._json_call(endpoint, params=params)['data']['season']

    @mem_cache.cached(60*5)
    def search(self, query):
        params = {
            'query': query,
        }
        endpoint = self._endpoint(self.get_config()['services']['explore']['client']['endpoints']['search']['href'], version=EXPLORE_VERSION)
        return self._json_call(endpoint, params=params)['data']['page']

    def upnext(self, content_id):
        params = {
            'contentId': content_id,
        }
        endpoint = self._endpoint(self.get_config()['services']['explore']['client']['endpoints']['getUpNext']['href'], version=EXPLORE_VERSION)
        return self._json_call(endpoint, params=params)['data']['upNext']

    def player_experience(self, available_id):
        endpoint = self._endpoint(self.get_config()['services']['explore']['client']['endpoints']['getPlayerExperience']['href'], version=EXPLORE_VERSION, availId=available_id)
        return self._json_call(endpoint)['data']['playerExperience']

    def edit_watchlist(self, event_type, page_info, action_info):
        self._set_token()
        profile, session = self.profile()
        event_time = arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss.SSS") + "Z"
        payload = [{
            'data': {
                'action_info_block': action_info,
                'page_info_block': page_info,
                'event_type': event_type,
                'event_occurred_timestamp': event_time,
            },
            'datacontenttype': 'application/json;charset=utf-8',
            'subject': 'sessionId={},profileId={}'.format(session['sessionId'], profile['id']),
            'source': 'urn:dss:source:sdk:android:google:tv',
            'type': 'urn:dss:event:cs:user-content-actions:preference:v1:watchlist',
            'schemaurl': 'https://github.bamtech.co/schema-registry/schema-registry-client-signals/blob/series/0.X.X/smithy/dss/cs/event/user-content-actions/preference/v1/watchlist.smithy',
            'id': str(uuid.uuid4()),
            'time': event_time,
        }]

        endpoint = self.get_config()['services']['telemetry']['client']['endpoints']['envelopeEvent']['href']
        data = self._session.post(endpoint, json=payload).json()
        self._check_errors(data)
        return not any([x['error'] is not None for x in data])

    def remove_continue_watching(self, action_info):
        self._set_token()
        profile, session = self.profile()
        event_time = arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss.SSS") + "Z"
        payload = [{
            'data': {
                'action_info_block': action_info,
            },
            'datacontenttype': 'application/json;charset=utf-8',
            'subject': 'sessionId={},profileId={}'.format(session['sessionId'], profile['id']),
            'source': 'urn:dss:source:sdk:android:google:tv',
            'type': 'urn:dss:event:cs:user-content-actions:preference:v1:watch-history-preference',
            'schemaurl': 'https://github.bamtech.co/schema-registry/schema-registry-client-signals/blob/series/1.X.X/smithy/dss/cs/event/user-content-actions/preference/v1/watch-history-preference.smithy',
            'id': str(uuid.uuid4()),
            'time': event_time,
        }]

        endpoint = self.get_config()['services']['telemetry']['client']['endpoints']['envelopeEvent']['href']
        data = self._session.post(endpoint, json=payload).json()
        self._check_errors(data)
        return not any([x['error'] is not None for x in data])

    def playback(self, resource_id, wv_secure=False):
        self._set_token()
        headers = {'accept': 'application/vnd.media-service+json', 'authorization': userdata.get('access_token'), 'x-dss-feature-filtering': 'true'}

        payload = {
            "playbackId": resource_id,
            "playback": {
                "attributes": {
                    "codecs": {
                        'supportsMultiCodecMaster': False, #if true outputs all codecs and resoultion in single playlist
                    },
                    "protocol": "HTTPS",
                   # "ads": "",
                    "frameRates": [60],
                    "assetInsertionStrategy": "SGAI",
                    "playbackInitializationContext": "ONLINE"
                },
            }
        }

        video_ranges = []
        audio_types = []

        # atmos not yet supported on basic tier. Add in-case support is added
        if settings.getBool('dolby_atmos', False):
            audio_types.append('ATMOS')

        # DTSX works on both tiers
        if settings.getBool('dtsx', False):
            audio_types.append('DTS_X')

        if wv_secure and settings.getBool('dolby_vision', False):
            video_ranges.append('DOLBY_VISION')

        if wv_secure and settings.getBool('hdr10', False):
            video_ranges.append('HDR10')

        if settings.getBool('h265', False):
            payload['playback']['attributes']['codecs'] = {'video': ['h264', 'h265']}

        if audio_types:
            payload['playback']['attributes']['audioTypes'] = audio_types

        if video_ranges:
            payload['playback']['attributes']['videoRanges'] = video_ranges

        if not wv_secure:
            payload['playback']['attributes']['resolution'] = {'max': ['1280x720']}

        scenario = 'ctr-high' if wv_secure else 'ctr-regular'
        endpoint = self._endpoint(self.get_config()['services']['media']['client']['endpoints']['mediaPayload']['href'].format(scenario=scenario))
        playback_data = self._session.post(endpoint, headers=headers, json=payload).json()
        self._check_errors(playback_data)
        return playback_data

    def update_resume(self, media_id, fguid, playback_time):
        self._set_token()

        payload = [{
            'server': {
                'fguid': fguid,
                'mediaId': media_id,
                # 'origin': '',
                # 'host': '',
                # 'cdn': '',
                # 'cdnPolicyId': '',
            },
            'client': {
                'event': 'urn:bamtech:api:stream-sample',
                'timestamp': str(int(time()*1000)),
                'play_head': playback_time,
                # 'playback_session_id': str(uuid.uuid4()),
                # 'interaction_id': str(uuid.uuid4()),
                # 'bitrate': 4206,
            },
        }]

        endpoint = self.get_config()['services']['telemetry']['client']['endpoints']['postEvent']['href']
        return self._session.post(endpoint, json=payload).status_code

    def logout(self):
        mem_cache.empty()
        userdata.delete('access_token')
        userdata.delete('expires')
        userdata.delete('refresh_token')
        userdata.delete('feature_flags')
        self.new_session()
