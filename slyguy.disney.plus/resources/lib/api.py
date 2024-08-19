import uuid
from time import time

from slyguy import userdata, mem_cache
from slyguy.session import Session
from slyguy.exceptions import Error

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

    @mem_cache.cached(60*60, key='config')
    def get_config(self):
        return self._session.get(CONFIG_URL).json()

    @mem_cache.cached(60*60, key='transaction_id')
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

    # def device_code(self):
    #     token = self.register_device()

    #     payload = {
    #         'variables': {},
    #         'query': queries.REQUEST_DEVICE_CODE,
    #     }

    #     endpoint = self.get_config()['services']['orchestration']['client']['endpoints']['query']['href']
    #     data = self._session.post(endpoint, json=payload, headers={'authorization': token}).json()
    #     self._check_errors(data)
    #     return data['data']['requestLicensePlate']['licensePlate']

    # def device_login(self, code):
    #     return False

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

    @mem_cache.cached(60*60, key='account')
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
            'apiVersion': '{apiVersion}',
            'region': region,
            'impliedMaturityRating': maturity,
            'kidsModeEnabled': 'true' if kids_mode else 'false',
            'appLanguage': app_language,
            'partner': BAM_PARTNER,
        }
        _args.update(**kwargs)

        href = href.format(**_args)

        # [3.0, 3.1, 3.2, 5.0, 3.3, 5.1, 6.0, 5.2, 6.1]
        api_version = '6.1'
        if '/search/' in href:
            api_version = '5.1'

        return href.format(apiVersion=api_version)

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

    def search(self, query, page_size=PAGE_SIZE_CONTENT):
        endpoint = self._endpoint(self.get_config()['services']['content']['client']['endpoints']['getSearchResults']['href'], query=query, queryType=SEARCH_QUERY_TYPE, pageSize=page_size)
        return self._json_call(endpoint)['data']['search']

    def feature_flags(self):
        self._set_token()
        return userdata.get('feature_flags')

    def avatar_by_id(self, ids):
        endpoint = self._endpoint(self.get_config()['services']['content']['client']['endpoints']['getAvatars']['href'], avatarIds=','.join(ids))
        return self._json_call(endpoint)['data']['Avatars']

    def video_bundle(self, family_id):
        endpoint = self._endpoint(self.get_config()['services']['content']['client']['endpoints']['getDmcVideoBundle']['href'], encodedFamilyId=family_id)
        return self._json_call(endpoint)['data']['DmcVideoBundle']

    def up_next(self, content_id):
        endpoint = self._endpoint(self.get_config()['services']['content']['client']['endpoints']['getUpNext']['href'], contentId=content_id)
        return self._json_call(endpoint)['data']['UpNext'] or {}

    def continue_watching(self):
        endpoint = self._endpoint(self.get_config()['services']['content']['client']['endpoints']['getCWSet']['href'], setId=CONTINUE_WATCHING_SET_ID)
        return self._json_call(endpoint)['data']['ContinueWatchingSet']

    def add_watchlist(self, ref_type, ref_id):
        self._set_token()
        endpoint = self._endpoint(self.get_config()['services']['content']['client']['endpoints']['putItemInWatchlist']['href'], refIdType=ref_type, refId=ref_id)
        return self._session.put(endpoint).ok

    def delete_watchlist(self, ref_type, ref_id):
        endpoint = self._endpoint(self.get_config()['services']['content']['client']['endpoints']['deleteItemFromWatchlist']['href'], refIdType=ref_type, refId=ref_id)
        return self._session.delete(endpoint).ok

    def collection_by_slug(self, slug, content_class, sub_type='StandardCollection'):
        endpoint = self._endpoint(self.get_config()['services']['content']['client']['endpoints']['getCollection']['href'], collectionSubType=sub_type, contentClass=content_class, slug=slug)
        return self._json_call(endpoint)['data']['Collection']

    def set_by_id(self, set_id, set_type, page=1, page_size=PAGE_SIZE_SETS):
        if set_type == 'ContinueWatchingSet':
            endpoint = 'getCWSet'
        elif set_type == 'CuratedSet':
            endpoint = 'getCuratedSet'
        else:
            endpoint = 'getSet'

        endpoint = self._endpoint(self.get_config()['services']['content']['client']['endpoints'][endpoint]['href'], setType=set_type, setId=set_id, pageSize=page_size, page=page)
        return self._json_call(endpoint)['data'][set_type]

    def video(self, content_id):
        endpoint = self._endpoint(self.get_config()['services']['content']['client']['endpoints']['getDmcVideo']['href'], contentId=content_id)
        return self._json_call(endpoint)['data']['DmcVideo']

    def series_bundle(self, series_id):
        endpoint = self._endpoint(self.get_config()['services']['content']['client']['endpoints']['getDmcSeriesBundle']['href'], encodedSeriesId=series_id)
        return self._json_call(endpoint)['data']['DmcSeriesBundle']

    def episodes(self, season_id, page=1, page_size=PAGE_SIZE_CONTENT):
        endpoint = self._endpoint(self.get_config()['services']['content']['client']['endpoints']['getDmcEpisodes']['href'], seasonId=season_id, pageSize=page_size, page=page)
        return self._json_call(endpoint)['data']['DmcEpisodes']

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

    def playback_data(self, playback_url, wv_secure=False):
        self._set_token()

        headers = {'accept': 'application/vnd.media-service+json; version={}'.format(6 if self._cache['basic_tier'] else 5), 'authorization': userdata.get('access_token'), 'x-dss-feature-filtering': 'true'}

        payload = {
            "playback": {
                "attributes": {
                    "codecs": {
                        'supportsMultiCodecMaster': False, #if true outputs all codecs and resoultion in single playlist
                    },
                    "protocol": "HTTPS",
                    #"ads": "",
                    "frameRates": [60],
                    "assetInsertionStrategy": "SGAI",
                    "playbackInitializationContext": "ONLINE"
                },
            }
        }

        video_ranges = []
        audio_types = []

        # atmos not yet supported on version=6 (basic tier). Add in-case support is added
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
        endpoint = playback_url.format(scenario=scenario)
        playback_data = self._session.post(endpoint, headers=headers, json=payload).json()
        self._check_errors(playback_data)
        return playback_data

    def logout(self):
        mem_cache.delete('transaction_id')
        mem_cache.delete('config')
        mem_cache.delete('account')
        userdata.delete('access_token')
        userdata.delete('expires')
        userdata.delete('refresh_token')
        userdata.delete('feature_flags')
        self.new_session()

    ### EXPLORE ###
    def explore_page(self, page_id):
        params = {
            'disableSmartFocus': 'true',
            'limit': 999,
            'enhancedContainersLimit': 0,
        }
        endpoint = self._endpoint(self.get_config()['services']['explore']['client']['endpoints']['getPage']['href'], version=EXPLORE_VERSION, pageId=page_id)
        return self._json_call(endpoint, params=params)['data']['page']

    def explore_set(self, set_id, page=1):
        params = {
            'limit': 999,
            'offset': 30*(page-1),
        }
        endpoint = self._endpoint(self.get_config()['services']['explore']['client']['endpoints']['getSet']['href'], version=EXPLORE_VERSION, setId=set_id)
        return self._json_call(endpoint, params=params)['data']['set']

    def explore_season(self, season_id, page=1):
        params = {
            'limit': 999,
            'offset': 30*(page-1),
        }
        endpoint = self._endpoint(self.get_config()['services']['explore']['client']['endpoints']['getSeason']['href'], version=EXPLORE_VERSION, seasonId=season_id)
        return self._json_call(endpoint, params=params)['data']['season']

    def explore_search(self, query):
        params = {
            'query': query,
        }
        endpoint = self._endpoint(self.get_config()['services']['explore']['client']['endpoints']['search']['href'], version=EXPLORE_VERSION)
        return self._json_call(endpoint, params=params)['data']['page']

    def explore_upnext(self, content_id):
        params = {
            'contentId': content_id,
        }
        endpoint = self._endpoint(self.get_config()['services']['explore']['client']['endpoints']['getUpNext']['href'], version=EXPLORE_VERSION)
        return self._json_call(endpoint, params=params)['data']['upNext']

    def explore_deeplink(self, family_id):
        params = {
            'refId': family_id,
            'refIdType': 'encodedFamilyId',
        }
        endpoint = self._endpoint(self.get_config()['services']['explore']['client']['endpoints']['getDeeplink']['href'], version=EXPLORE_VERSION)
        return self._json_call(endpoint, params=params)['data']['deeplink']['actions'][0]['pageId'].replace('entity-','')

    def explore_playback(self, resource_id, wv_secure=False):
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
