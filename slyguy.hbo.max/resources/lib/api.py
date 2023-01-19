import uuid
from time import time
from six.moves.urllib_parse import quote

from kodi_six import xbmc

from slyguy import userdata, settings, mem_cache, gui
from slyguy.session import Session
from slyguy.exceptions import Error
from slyguy.log import log
from slyguy.util import get_system_arch, lang_allowed

from .constants import *
from .language import _

class APIError(Error):
    pass

class NotPairedError(APIError):
    pass

class API(object):
    def new_session(self):
        self.logged_in = False
        self._session = Session(HEADERS, timeout=30)
        self._set_authentication(userdata.get('access_token'))

    def _set_authentication(self, access_token):
        if not access_token:
            return

        self._session.headers.update({'Authorization': 'Bearer {}'.format(access_token)})
        self.logged_in = True

    def _refresh_token(self, force=False):
        if not force and userdata.get('expires', 0) > time():
            return

        payload = {
            'refresh_token': userdata.get('refresh_token'),
            'grant_type': 'refresh_token',
            'scope': 'browse video_playback device',
        }

        self._oauth_token(payload, {'Authorization': None})

    def url(self, name, path=''):
        config = self._client_config()

        if name == 'tokens':
            return 'https://oauth{userSubdomain}.{domain}.hbo.com/auth/tokens'.format(**config['routeKeys'])

        elif name == 'gateway':
            return 'https://gateway{userSubdomain}.{domain}.hbo.com'.format(**config['routeKeys']) + path

        elif name == 'sessions':
            return 'https://sessions{userSubdomain}.{domain}.hbo.com'.format(**config['routeKeys']) + path

        elif name == 'comet':
            return 'https://comet{userSubdomain}.{domain}.hbo.com'.format(**config['routeKeys']) + path

        elif name == 'markers':
            return 'https://markers{userSubdomain}.{domain}.hbo.com'.format(**config['routeKeys']) + path

        elif name == 'artist':
            return 'https://artist.{cdnDomain}.hbo.com'.format(**config['routeKeys']) + path

        else:
            return None

    def _oauth_token(self, payload, headers=None):
        self.logged_in = False
        mem_cache.delete('config')

        data = self._session.post(self.url('tokens'), data=payload, headers=headers).json()
        self._check_errors(data)

        self._set_authentication(data['access_token'])
        userdata.set('access_token', data['access_token'])
        userdata.set('expires', int(time() + data['expires_in'] - 15))

        if 'refresh_token' in data:
            userdata.set('refresh_token', data['refresh_token'])

        mem_cache.delete('config')

    def _device_serial(self):
        def _format_id(string):
            try:
                mac_address = uuid.getnode()
                if mac_address != uuid.getnode():
                    mac_address = ''
            except:
                mac_address = ''

            system, arch = get_system_arch()
            return str(string.format(mac_address=mac_address, system=system, arch=arch).strip())

        _id = _format_id(settings.get('device_id').strip()) or _format_id(DEFAULT_DEVICE_ID)
        return str(uuid.uuid3(uuid.UUID(UUID_NAMESPACE), _id))

    def _guest_login(self):
        serial = self._device_serial()

        payload = {
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_ID,
            'scope': 'browse video_playback_free account_registration',
            'grant_type': 'client_credentials',
            'deviceSerialNumber': serial,
            'clientDeviceData': {
            	'paymentProviderCode': 'google-play'
            }
        }

        data = self._session.post(GUEST_AUTH, json=payload, headers={'Authorization': None}).json()
        if 'code' in data and data['code'] == 'invalid_credentials':
            raise APIError(_.BLOCKED_IP)

        self._check_errors(data)
        self._set_authentication(data['access_token'])
        return serial

    @mem_cache.cached(60*30, key='config')
    def _client_config(self):
        if not self.logged_in:
            log.debug("GUEST CONFIG")
            self._guest_login()
        else:
            log.debug("USER CONFIG")

        payload = {
            'contract': 'hadron:1.1.2.0',
            'preferredLanguages': [DEFAULT_LANGUAGE],
        }

        data = self._session.post(CONFIG_URL, json=payload).json()
        self._check_errors(data)
        return data

    def device_code(self):
        self.logout()

        serial = self._guest_login()

        payload = {
            'model': DEVICE_MODEL,
            'serialNumber': serial,
            'userIntent': 'login',
        }

        data = self._session.post(self.url('comet', '/devices/activationCode'), json=payload).json()
        self._check_errors(data)

        return serial, data['activationCode']

    def set_profile(self, profile_id):
        self._refresh_token()

        payload = {
            'grant_type': 'user_refresh_profile',
            'profile_id': profile_id,
            'refresh_token': userdata.get('refresh_token'),
        }

        self._oauth_token(payload)
        mem_cache.empty()

    def login(self, username, password):
        payload = {
            'username': username,
            'password': password,
            'grant_type': 'user_name_password',
            'scope': 'browse video_playback device elevated_account_management',
        }

        self._oauth_token(payload)

    def device_login(self, serial, code):
        payload = {
            'model': DEVICE_MODEL,
            'code': code,
            'serialNumber': serial,
            'grant_type': 'user_activation_code',
            'scope': 'browse video_playback device elevated_account_management',
        }

        try:
            self._oauth_token(payload)
        except NotPairedError:
            return False
        else:
            return True

    def _check_errors(self, data, error=_.API_ERROR):
        if not data:
            raise APIError(_.BLOCKED_IP)

        if 'code' in data:
            if data['code'] == 'not_paired':
                raise NotPairedError()
            else:
                error_msg = data.get('message') or data.get('code')
                raise APIError(_(error, msg=error_msg))

        # has to be after code
        elif 'statusCode' in data and data['statusCode'] >= 400:
            error_msg = data.get('message')
            raise APIError(_(error, msg=error_msg))

    def profiles(self):
        return self.content([{'id': 'urn:hbo:profiles:mine'}])['urn:hbo:profiles:mine']['profiles']

    def continue_watching(self):
        data = self.content([{'id': 'urn:hbo:continue-watching:mine'}])
        return self._process(data, 'urn:hbo:continue-watching:mine')

    def watchlist(self):
        data = self.content([{'id': 'urn:hbo:query:mylist'}])
        data = self._process(data, 'urn:hbo:query:mylist')

        payload = []
        items = {}
        order = []
        for row in reversed(data['items']):
            order.append(row['id'])
            if not row.get('contentType'):
                payload.append({'id': row['id']})
            else:
                items[row['id']] = row

        def chunks(lst, n):
            for i in range(0, len(lst), n):
                yield lst[i:i + n]

        for chunk in chunks(payload, 32):
            data = self.content(chunk)
            for key in data:
                items[key] = self._process(data, key)

        ordered = []
        for id in order:
            if id in items:
                ordered.append(items[id])

        return ordered

    def add_watchlist(self, slug):
        self._refresh_token()
        return self._session.put(self.url('comet', '/watchlist/{}'.format(slug))).ok

    def delete_watchlist(self, slug):
        self._refresh_token()
        return self._session.delete(self.url('comet', '/watchlist/{}'.format(slug))).ok

    def marker(self, id):
        markers = self.markers([id,])
        return list(markers.values())[0] if markers else None

    def markers(self, ids):
        if not ids:
            return {}

        self._refresh_token()
        if len(ids) == 1:
            #always have at least 2 markers so api returns a list
            ids.append(ids[0])

        params = {
            'limit': len(ids),
        }

        try:
            markers = {}
            for row in self._session.get(self.url('markers', '/markers/{}'.format(','.join(ids))), params=params, json={}).json():
                markers[row['id']] = {'position': row['position'], 'runtime': row['runtime']}
            return markers
        except:
            return {}

    def update_marker(self, url, cut_id, runtime, playback_time):
        self._refresh_token()

        payload = {
            #'appSessionId': session_id,
            #'videoSessionId': video_session,
            'creationTime': int(time()*1000),
            'cutId': cut_id,
            'position': playback_time,
            'runtime': runtime,
        }

        resp = self._session.post(url, json=payload)
        if not resp.ok:
            return False
        else:
            return resp.json().get('status') == 'Accepted'

    def _headwaiter(self):
        config = self._client_config()

        headwaiter = ''
        for key in sorted(config['payloadValues']):
            headwaiter += '{}:{},'.format(key, config['payloadValues'][key])

        return headwaiter.rstrip(',')

    def get_languages(self):
        headers = {
            'x-hbo-headwaiter': self._headwaiter(),
        }
        return [x for x in self._session.get(self.url('sessions', '/sessions/v1/enabledLanguages'), headers=headers).json() if x.get('disabledForCurrentRegion') != True]

    @mem_cache.cached(60*30, key='language')
    def _get_language(self):
        language = userdata.get('language', 'auto')
        if language == 'auto':
            language = xbmc.getLanguage(xbmc.ISO_639_1, True).replace('no-', 'nb-')
            log.debug('Using Kodi language: {}'.format(language))

        available = [x['code'] for x in self.get_languages()]
        log.debug('Available languages: {}'.format(available))

        if lang_allowed(language, available):
            log.debug('Selected language: {}'.format(language))
            return language

        log.debug('Using default language: {}'.format(DEFAULT_LANGUAGE))
        return DEFAULT_LANGUAGE

    def entitlements(self):
        return self.content([{"id":"urn:hbo:entitlement-status:mine"}])['urn:hbo:entitlement-status:mine']

    def express_content(self, slug, tab=None):
        self._refresh_token()

        headers = {
            'x-hbo-headwaiter': self._headwaiter(),
            'accept-language': self._get_language(),
        }
        params = {
            'language': self._get_language(),
        }

        entitlements = self.entitlements()
        if entitlements['outOfTerritory']:
            raise APIError(_.GEO_LOCKED)

        data = self._session.get(self.url('comet', '/express-content/{}?{}'.format(slug, entitlements['expressContentParams'])), params=params, headers=headers).json()
        self._check_errors(data)

        _data = {}
        for row in data:
            _data[row['id']] = row['body']

        return self._process(_data, tab or slug)

    def content(self, payload):
        self._refresh_token()

        headers = {
            'x-hbo-headwaiter': self._headwaiter(),
            'accept-language': self._get_language(),
        }

        data = self._session.post(self.url('comet', '/content'), json=payload, headers=headers).json()
        self._check_errors(data)

        if isinstance(data, dict):
            return data

        _data = {}
        for row in data:
            _data[row['id']] = row['body']

        return _data

    def _process(self, data, slug):
        main = data[slug]
        if len(data) == 1 and 'message' in main:
            raise APIError(_(_.API_ERROR, msg=main['message']))

        def process(element):
            element['items'] = []
            element['tabs'] = []
            element['edits'] = []
            element['previews'] = []
            element['seasons'] = []
            element['extras'] = []
            element['similars'] = []
            element['episodes'] = []
            element['target'] = None

            for key in element.get('references', {}):
                if key in ('items', 'tabs', 'edits', 'seasons', 'previews', 'extras', 'similars', 'episodes'):
                    for id in element['references'][key]:
                        if id == '$dataBinding':
                            continue

                        item = {'id': id}
                        if id in data:
                            item.update(data[id])
                        process(item)
                        element[key].append(item)
                else:
                    element[key] = element['references'][key]

            element.pop('references', None)

        process(main)
        return main

    def search(self, query):
        key = 'urn:hbo:flexisearch:{}'.format(quote(query))
        data = self.content([{'id': key}])

        for key in data:
            if key.startswith('urn:hbo:grid:search') and key.endswith('-all'):
                return self._process(data, key)

        return None

    def play(self, slug):
        self._refresh_token()

        content_data = self.express_content(slug)
        edits = content_data.get('edits', [])
        if not edits:
            raise APIError(_.NO_VIDEO_FOUND)

        edit = None
        options = []
        playback_language = settings.get('playback_language', '').strip().lower()
        for row in edits:
            if playback_language and row['originalAudioLanguage'].lower().startswith(playback_language):
                edit = row
                break

            label = row['originalAudioLanguage']
            for track in row['audioTracks']:
                if track['language'].lower().startswith(row['originalAudioLanguage'].lower()):
                    label = track['displayName']
                    break

            options.append(label)

        if edit is None:
            if len(options) == 1:
                index = 0
            else:
                index = gui.select(options=options, heading=_.PLAYBACK_LANGUAGE)
                if index == -1:
                    return None, None, None

            edit = edits[index]

        payload = [{
            'id': edit['video'],
            'headers' : {
                'x-hbo-preferred-blends': 'DASH_WDV,HSS_PR',
                'x-hbo-video-mlp': True, #multi-language
            }
        }]

        data = self.content(payload).get(edit['video'])
        self._check_errors(data)

        for row in data.get('manifests', []):
            if row['type'] == 'urn:video:main':
                return row, content_data, edit

        raise APIError(_.NO_VIDEO_FOUND)

    def logout(self):
        userdata.delete('access_token')
        userdata.delete('expires')
        userdata.delete('refresh_token')
        userdata.delete('config')
        mem_cache.empty()
        self.new_session()
