import json
import uuid
from time import time

from slyguy import userdata, settings, mem_cache
from slyguy.session import Session
from slyguy.exceptions import Error
from slyguy.util import get_kodi_setting, jwt_data
from slyguy.log import log

from kodi_six import xbmc

from .constants import *
from .language import _

class APIError(Error):
    pass

ERROR_MAP = {
    'not-entitled': _.NOT_ENTITLED,
    'idp.error.identity.bad-credentials': _.BAD_CREDENTIALS,
}

class API(object):
    def new_session(self):
        self.logged_in = False
        self._session = Session(HEADERS, timeout=30)
        self._set_authentication(userdata.get('access_token'))
        self._set_languages()

    @mem_cache.cached(60*60, key='config')
    def get_config(self):
        return self._session.get(CONFIG_URL).json()

    def _set_languages(self):
        self._app_language = 'en'
        self._playback_language = 'en'
        self._subtitle_language = 'en'
        self._kids_mode = False
        self._maturity_rating = 9999
        self._region = None

        if not self.logged_in:
            return

        token = userdata.get('access_token')
        if '..' in token: #JWE Token
            return

        data = jwt_data(token)['context']

     #   self._maturity_rating = data['preferred_maturity_rating']['implied_maturity_rating']
     #   self._region = data['location']['country_code']

        for profile in data['profiles']:
            if profile['id'] == data['active_profile_id']:
                self._app_language      = profile['language_preferences']['app_language']
                self._playback_language = profile['language_preferences']['playback_language']
                self._subtitle_language = profile['language_preferences']['subtitle_language']
                self._kids_mode         = profile['kids_mode_enabled']
                return

    @mem_cache.cached(60*60, key='transaction_id')
    def _transaction_id(self):
        return str(uuid.uuid4())

    @property
    def session(self):
        return self._session

    def _set_authentication(self, access_token):
        if not access_token:
            return

        ## JWT requires Bearer
        if '..' not in access_token:
            access_token = 'Bearer {}'.format(access_token)

        self._session.headers.update({'Authorization': access_token})
        self._session.headers.update({'x-bamsdk-transaction-id': self._transaction_id()})
        self.logged_in = True

    def _refresh_token(self, force=False):
        if not force and userdata.get('expires', 0) > time():
            return

        payload = {
            'refresh_token': userdata.get('refresh_token'),
            'grant_type': 'refresh_token',
            'platform': 'browser',
        }

        self._oauth_token(payload)

    def _oauth_token(self, payload):
        headers = {
            'Authorization': 'Bearer {}'.format(API_KEY),
        }

        endpoint = self.get_config()['services']['token']['client']['endpoints']['exchange']['href']
        token_data = self._session.post(endpoint, data=payload, headers=headers).json()

        self._check_errors(token_data)

        self._set_authentication(token_data['access_token'])

        userdata.set('access_token', token_data['access_token'])
        userdata.set('expires', int(time() + token_data['expires_in'] - 15))

        if 'refresh_token' in token_data:
            userdata.set('refresh_token', token_data['refresh_token'])

    def login(self, username, password):
        self.logout()

        try:
            self._do_login(username, password)
        except:
            self.logout()
            raise

    def _check_errors(self, data, error=_.API_ERROR):
        if not type(data) is dict:
            return

        if data.get('errors'):
            error_msg = ERROR_MAP.get(data['errors'][0].get('code')) or data['errors'][0].get('description') or data['errors'][0].get('code')
            raise APIError(_(error, msg=error_msg))

        elif data.get('error'):
            error_msg = ERROR_MAP.get(data.get('error_code')) or data.get('error_description') or data.get('error_code')
            raise APIError(_(error, msg=error_msg))

        elif data.get('status') == 400:
            raise APIError(_(error, msg=data.get('message')))

    def _do_login(self, username, password):
        headers = {
            'Authorization': 'Bearer {}'.format(API_KEY),
        }

        payload = {
            'deviceFamily': 'android',
            'applicationRuntime': 'android',
            'deviceProfile': 'tv',
            'attributes': {},
        }

        endpoint = self.get_config()['services']['device']['client']['endpoints']['createDeviceGrant']['href']
        device_data = self._session.post(endpoint, json=payload, headers=headers, timeout=20).json()

        self._check_errors(device_data)

        payload = {
            'subject_token': device_data['assertion'],
            'subject_token_type': 'urn:bamtech:params:oauth:token-type:device',
            'platform': 'android',
            'grant_type': 'urn:ietf:params:oauth:grant-type:token-exchange',
        }

        self._oauth_token(payload)

        payload = {
            'email':    username,
            'password': password,
        }

        endpoint = self.get_config()['services']['bamIdentity']['client']['endpoints']['identityLogin']['href']
        login_data = self._session.post(endpoint, json=payload).json()

        self._check_errors(login_data)

        endpoint = self.get_config()['services']['account']['client']['endpoints']['createAccountGrant']['href']
        grant_data = self._session.post(endpoint, json={'id_token': login_data['id_token']}).json()

        payload = {
            'subject_token': grant_data['assertion'],
            'subject_token_type': 'urn:bamtech:params:oauth:token-type:account',
            'platform': 'android',
            'grant_type': 'urn:ietf:params:oauth:grant-type:token-exchange',
        }

        self._oauth_token(payload)

    def _json_call(self, endpoint, variables=None):
        self._refresh_token()
        params = {'variables': json.dumps(variables)} if variables else None
        data = self._session.get(endpoint, params=params).json()
        self._check_errors(data)
        return data

    def profiles(self):
        self._refresh_token(force=True)
        endpoint = self.get_config()['services']['account']['client']['endpoints']['getUserProfiles']['href']
        return self._json_call(endpoint)

    def active_profile(self):
        endpoint = self.get_config()['services']['account']['client']['endpoints']['getActiveUserProfile']['href']
        return self._json_call(endpoint)

    def set_profile(self, profile, pin=None):
        self._refresh_token()

        endpoint = self.get_config()['services']['account']['client']['endpoints']['setActiveUserProfile']['href'].format(profileId=profile['profileId'])

        payload = {}
        if pin:
            payload['entryPin'] = str(pin)

        grant_data = self._session.put(endpoint, json=payload).json()
        self._check_errors(grant_data)

        payload = {
            'subject_token': grant_data['assertion'],
            'subject_token_type': 'urn:bamtech:params:oauth:token-type:account',
            'platform': 'android',
            'grant_type': 'urn:ietf:params:oauth:grant-type:token-exchange',
        }

        self._oauth_token(payload)

        userdata.set('profile_language', profile['attributes']['languagePreferences']['appLanguage'])

    def search(self, query, page=1, page_size=PAGE_SIZE):
        variables = {
            'preferredLanguage': [self._app_language],
            'index': 'disney_global',
            'q': query,
            'page': page,
            'pageSize': page_size,
            'contentTransactionId': self._transaction_id(),
        }

        endpoint = self.get_config()['services']['content']['client']['endpoints']['searchPersisted']['href'].format(queryId='core/disneysearch')
        return self._json_call(endpoint, variables)['data']['disneysearch']

    def avatar_by_id(self, ids):
        variables = {
            'preferredLanguage': [self._app_language],
            'avatarId': ids,
        }

        endpoint = self.get_config()['services']['content']['client']['endpoints']['searchPersisted']['href'].format(queryId='core/AvatarByAvatarId')
        return self._json_call(endpoint, variables)['data']['AvatarByAvatarId']

    def video_bundle(self, family_id):
        variables = {
            'preferredLanguage': [self._app_language],
            'familyId': family_id,
            'contentTransactionId': self._transaction_id(),
        }

        endpoint = self.get_config()['services']['content']['client']['endpoints']['dmcVideos']['href'].format(queryId='core/DmcVideoBundle')
        return self._json_call(endpoint, variables)['data']['DmcVideoBundle']

    def extras(self, family_id):
        variables = {
            'preferredLanguage': [self._app_language],
            'familyId': family_id,
            'page': 1,
            'pageSize': 999,
            'contentTransactionId': self._transaction_id(),
        }

        endpoint = self.get_config()['services']['content']['client']['endpoints']['dmcVideos']['href'].format(queryId='core/DmcExtras')
        return self._json_call(endpoint, variables)['data']['DmcExtras']

    def series_bundle(self, series_id, page=1, page_size=PAGE_SIZE):
        variables = {
            'preferredLanguage': [self._app_language],
            'seriesId': series_id,
            'episodePage': page,
            'episodePageSize': page_size,
            'contentTransactionId': self._transaction_id(),
        }

        endpoint = self.get_config()['services']['content']['client']['endpoints']['dmcVideos']['href'].format(queryId='core/DmcSeriesBundle')
        return self._json_call(endpoint, variables)['data']['DmcSeriesBundle']

    def episodes(self, season_ids, page=1, page_size=PAGE_SIZE_EPISODES):
        variables = {
            'preferredLanguage': [self._app_language],
            'seasonId': season_ids,
            'episodePage': page,
            'episodePageSize': page_size,
            'contentTransactionId': self._transaction_id(),
        }

        endpoint = self.get_config()['services']['content']['client']['endpoints']['dmcVideos']['href'].format(queryId='core/DmcEpisodes')
        return self._json_call(endpoint, variables)['data']['DmcEpisodes']

    def collection_by_slug(self, slug, content_class):
        variables = {
            'preferredLanguage': [self._app_language],
            'contentClass': content_class,
            'slug': slug,
            'contentTransactionId': self._transaction_id(),
        }

        #endpoint = self.get_config()['services']['content']['client']['endpoints']['dmcVideos']['href'].format(queryId='disney/CollectionBySlug')
        endpoint = self.get_config()['services']['content']['client']['endpoints']['dmcVideos']['href'].format(queryId='core/CompleteCollectionBySlug')
        return self._json_call(endpoint, variables)['data']['CompleteCollectionBySlug']

    def set_by_id(self, set_id, set_type, page=1, page_size=PAGE_SIZE):
        variables = {
            'preferredLanguage': [self._app_language],
            'setId': set_id,
            'setType': set_type,
            'page': page,
            'pageSize': page_size,
            'contentTransactionId': self._transaction_id(),
        }

        #endpoint = self.get_config()['services']['content']['client']['endpoints']['dmcVideos']['href'].format(queryId='disney/SetBySetId')
        endpoint = self.get_config()['services']['content']['client']['endpoints']['dmcVideos']['href'].format(queryId='core/SetBySetId')
        return self._json_call(endpoint, variables)['data']['SetBySetId']

    def add_watchlist(self, content_id):
        variables = {
            'preferredLanguage': [self._app_language],
            'contentIds': content_id,
        }

        endpoint = self.get_config()['services']['content']['client']['endpoints']['dmcVideos']['href'].format(queryId='core/AddToWatchlist')
        return self._json_call(endpoint, variables)['data']['AddToWatchlist']

    def delete_watchlist(self, content_id):
        variables = {
            'preferredLanguage': [self._app_language],
            'contentIds': content_id,
        }

        endpoint = self.get_config()['services']['content']['client']['endpoints']['dmcVideos']['href'].format(queryId='core/DeleteFromWatchlist')
        data = self._json_call(endpoint, variables)['data']['DeleteFromWatchlist']
        xbmc.sleep(500)
        return data

    def up_next(self, content_id):
        variables = {
            'preferredLanguage': [self._app_language],
            'contentId': content_id,
            'contentTransactionId': self._transaction_id(),
        }

        endpoint = self.get_config()['services']['content']['client']['endpoints']['dmcVideos']['href'].format(queryId='core/UpNext')
        return self._json_call(endpoint, variables)['data']['UpNext']

    def videos(self, content_id):
        variables = {
            'preferredLanguage': [self._app_language],
            'contentId': content_id,
            'contentTransactionId': self._transaction_id(),
        }

        endpoint = self.get_config()['services']['content']['client']['endpoints']['dmcVideos']['href'].format(queryId='core/DmcVideos')
        return self._json_call(endpoint, variables)['data']['DmcVideos']

    def update_resume(self, media_id, fguid, playback_time):
        payload = [{
            "server": {
                "fguid": fguid,
                "mediaId": media_id,
            },
            "client": {
                "event": "urn:dss:telemetry-service:event:stream-sample",
                "timestamp": str(int(time()*1000)),
                "play_head": playback_time,
                # "playback_session_id": str(uuid.uuid4()),
                # "interaction_id": str(uuid.uuid4()),
                # "bitrate": 4206,
            },
        }]

        self._refresh_token()
        endpoint = self.get_config()['services']['telemetry']['client']['endpoints']['postEvent']['href']
        return self._session.post(endpoint, json=payload).status_code

    def playback_data(self, playback_url):
        self._refresh_token(force=True)

        config = self.get_config()
        scenario = config['services']['media']['extras']['restrictedPlaybackScenario']

        if settings.getBool('wv_secure', False):
            scenario = config['services']['media']['extras']['playbackScenarioDefault']

            if settings.getBool('h265', False):
                scenario += '-h265'

                if settings.getBool('dolby_vision', False):
                    scenario += '-dovi'
                elif settings.getBool('hdr10', False):
                    scenario += '-hdr10'

                if settings.getBool('dolby_atmos', False):
                    scenario += '-atmos'

        headers = {'accept': 'application/vnd.media-service+json; version=4', 'authorization': userdata.get('access_token')}

        endpoint = playback_url.format(scenario=scenario)
        playback_data = self._session.get(endpoint, headers=headers).json()
        self._check_errors(playback_data)

        return playback_data

    def continue_watching(self):
        set_id = CONTINUE_WATCHING_SET_ID
        set_type = CONTINUE_WATCHING_SET_TYPE
        data = self.set_by_id(set_id, set_type, page_size=999)

        continue_watching = {}
        for row in data['items']:
            if row['meta']['bookmarkData']:
                play_from = row['meta']['bookmarkData']['playhead']
            else:
                play_from = 0

            continue_watching[row['contentId']] = play_from

        return continue_watching

    def logout(self):
        userdata.delete('access_token')
        userdata.delete('expires')
        userdata.delete('refresh_token')

        mem_cache.delete('transaction_id')
        mem_cache.delete('config')

        self.new_session()
