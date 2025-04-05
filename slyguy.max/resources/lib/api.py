import uuid

from slyguy import userdata, mem_cache, _
from slyguy.session import Session
from slyguy.exceptions import Error
from slyguy.util import jwt_data

from .constants import HEADERS, BASE_URL, SITE_ID, APP_VERSION, CLIENT_ID, BRAND_ID, REALM, PAGE_SIZE


class APIError(Error):
    pass


class API(object):
    def new_session(self):
        self.logged_in = False
        self._session = Session(HEADERS)

        if not userdata.get('device_id'):
            userdata.set('device_id', self._device_id())

        self._session.headers.update({
            'x-device-info': '{}/{} (NVIDIA/SHIELD Android TV; android/9-mdarcy-userdebug; {}/{})'.format(SITE_ID, APP_VERSION, userdata.get('device_id'), CLIENT_ID),
        })

        self._set_authentication(userdata.get('access_token'))

    def _set_authentication(self, access_token):
        if not access_token:
            return

        self._session.headers.update({'Authorization': 'Bearer {}'.format(access_token)})
        self.logged_in = True

    def _device_id(self):
        return str(uuid.uuid1())

    def route(self, route):
        params = {
            'include': 'default',
            'decorators': 'viewingHistory,isFavorite,contentAction,badges',
            'page[items.size]': PAGE_SIZE,
        }
        data = self._session.get(self._endpoint('/cms/routes/{}'.format(route)), params=params, json={}).json()
        return self._process_data(data)[0]['target']

    @mem_cache.cached(60*30, key='config')
    def _get_config(self):
        if not self.logged_in:
            data = self._session.get(BASE_URL+'/token', params={'realm': REALM}, headers={'Authorization': None}).json()
            self._check_errors(data)
            self._set_authentication(data['data']['attributes']['token'])

        data = self._session.post(BASE_URL+'/session-context/headwaiter/v1/bootstrap', json={}).json()
        self._check_errors(data)
        return data

    def collection(self, id, page=1):
        params = {
            'include': 'default',
            'decorators': 'viewingHistory,badges,isFavorite,contentAction',
            'page[items.number]': page,
            'page[items.size]': PAGE_SIZE,
        }
        data = self._session.get(self._endpoint('/cms/collections/{}'.format(id)), params=params, json={}).json()
        return self._process_data(data)[0]

    def search(self, query, page=1):
        @mem_cache.cached(60*30)
        def get_collection_id():
            params = {'include': 'default'}
            data = self._session.get(self._endpoint('/cms/routes/search/result'), params=params, json={}).json()
            return self._process_data(data)[0]['target']['items'][0]['collection']['id']
        
        params = {
            'include': 'default',
            'decorators': 'viewingHistory,badges,isFavorite,contentAction',
            'pf[query]': query,
            'page[items.number]': page,
            'page[items.size]': PAGE_SIZE,
        }
        data = self._session.get(self._endpoint('/cms/collections/{}'.format(get_collection_id())), params=params, json={}).json()
        return self._process_data(data)[0]

    @mem_cache.cached(60*30)
    def series(self, id):
        params = {
            'include': 'default',
            'decorators': 'viewingHistory,badges,isFavorite,contentAction',
            'page[items.size]': PAGE_SIZE,
        }
        data = self._session.get(self._endpoint('/cms/routes/show/{}'.format(id)), params=params, json={}).json()
        return self.find(self._process_data(data), 'show')

    def find(self, json_data, target_key):
        if isinstance(json_data, dict):
            if target_key in json_data:
                return json_data[target_key]

            for value in json_data.values():
                result = self.find(value, target_key)
                if result is not None:
                    return result
        elif isinstance(json_data, list):
            for item in json_data:
                result = self.find(item, target_key)
                if result is not None:
                    return result
        return None

    @mem_cache.cached(60*5)
    def season(self, series_id, season_num, page=1):
        params = {
            'include': 'default',
            'decorators': 'viewingHistory,badges,isFavorite,contentAction',
            'pf[show.id]': series_id,
            'pf[seasonNumber]': season_num,
            'page[items.number]': page,
            'page[items.size]': PAGE_SIZE,
        }
        data = self._session.get(self._endpoint('/cms/collections/generic-show-page-rail-episodes-tabbed-content'), params=params, json={}).json()
        return self._process_data(data)[0]

    def _endpoint(self, path='/'):
        config = self._get_config()

        matches = []
        for row in config['endpoints']:
            kwargs = {}
            for key in config['routing']:
                kwargs[key] = config['routing'][key]
            base_url = config['apiGroups'][row['apiGroup']]['baseUrl'].format(**kwargs)

            if path.lower() == row['path'].lower():
                return base_url + path
            elif path.startswith(row['path']):
                matches.append([row['path'], base_url])

        if not matches:
            raise APIError('No base url found for "{}"'.format(path))

        matches = sorted(matches, key=lambda x: len(x[0]), reverse=True)
        return matches[0][1] + path

    def device_login(self):
        resp = self._session.post(self._endpoint('/authentication/linkDevice/login'), json={})
        if resp.status_code == 204:
            return False
        elif resp.status_code != 200:
            raise APIError(_.DEVICE_LOGIN_ERROR)

        data = resp.json()
        self._login(data)
        return True

    def _login(self, data):
        self._check_errors(data)
        token = data['data']['attributes']['token']
        self._set_authentication(token)
        token_data = jwt_data(token)

        userdata.set('access_token', token)
        userdata.set('token_expires', token_data['exp'] - 30)
        mem_cache.empty()

        data = self._session.get(self._endpoint('/users/me'), json={}).json()
        self._check_errors(data)
        userdata.set('user_id', data['data']['id'])
        userdata.set('profile', {'id': data['data']['attributes']['selectedProfileId']})      

    def device_code(self, provider=False):
        self.logout()

        if provider:
            payload = {
                "gauthPayload": {
                    "brandId": BRAND_ID,
                },
                "providers": provider,
                "signup": False,
            }
        else:
            payload = {}

        data = self._session.post(self._endpoint('/authentication/linkDevice/initiate'), json=payload).json()
        self._check_errors(data)
        return data['data']['attributes']['targetUrl'], data['data']['attributes']['linkingCode']

    def _process_data(self, data):
        self._check_errors(data)

        linked = {}
        for row in data.get('included', []):
            if row['type'] == 'package':
                continue
            linked[row['id']] = row

        processed = {}
        def _process_row(row):
            if row['id'] in processed:
                return processed[row['id']]
            new_row = {'id': row['id'], 'meta': row.get('meta',{})}
            new_row.update(row.get('attributes', {}))
            processed[row['id']] = new_row
            for name in row.get('relationships', []):
                related = row['relationships'][name]['data']
                if isinstance(related, list):
                    new_row[name] = [_process_row(linked[x['id']]) if x['id'] in linked else x for x in related]
                elif related['id'] in linked:
                    new_row[name] = _process_row(linked[related['id']])
                else:
                    new_row[name] = related
            return new_row

        new_data = []
        if isinstance(data['data'], dict):
            data['data'] = [data['data']]
        for row in data['data']:
            new_data.append(_process_row(row))

        return new_data

    def profiles(self):
        data = self._session.get(self._endpoint('/users/me/profiles'), json={}).json()
        return self._process_data(data)

    def switch_profile(self, profile, pin=None):
        payload = {
            'data': {
                'attributes': {'selectedProfileId': profile['id']},
                'id': userdata.get('user_id'),
                'type': 'user'
            }
        }

        if pin:
            payload['data']['attributes']['profilePin'] = pin

        resp = self._session.post(self._endpoint('/users/me/profiles/switchProfile'), json=payload)
        if resp.ok:
            return True

        data = resp.json()
        self._check_errors(data)

    def _check_errors(self, data):
        if 'errors' in data:
            if data['errors'][0].get('code')  == 'invalid.token':
                self.logout(api_logout=False)
                raise APIError(_.INVALID_TOKEN)
            else:
                raise APIError(data['errors'][0]['detail'])
        elif data.get('type') == 'Error':
            raise APIError(data.get('message'))

    @mem_cache.cached(60*5)
    def get_edit_id(self, id):
        params = {'include': 'edit'}
        data = self._session.get(self._endpoint('/content/videos/{}/activeVideoForShow'.format(id)), params=params).json()
        self._check_errors(data)
        return self._process_data(data)[0]['edit']['id']

    def play(self, edit_id):
        payload = {
            'appBundle': 'com.wbd.stream',
            'applicationSessionId': self._device_id(),
            'capabilities': {
                'codecs': {
                    'audio': {
                        'decoders': [{
                            'codec': 'aac',
                            'profiles': ['lc', 'he', 'hev2', 'xhe']
                        },{
                            'codec': 'eac3',
                            'profiles': ['atmos']
                        }]
                    },
                    'video': {
                        'decoders': [{
                            'codec': 'h264',
                            'levelConstraints': {
                                'framerate': {
                                    'max': 960,
                                    'min': 0
                                },
                                'height': {
                                    'max': 2176,
                                    'min': 48
                                },
                                'width': {
                                    'max': 3840,
                                    'min': 48
                                }
                            },
                            'maxLevel': '5.2',
                            'profiles': ['baseline', 'main', 'high']
                        }, {
                            'codec': 'h265',
                            'levelConstraints': {
                                'framerate': {
                                    'max': 960,
                                    'min': 0
                                },
                                'height': {
                                    'max': 2176,
                                    'min': 144
                                },
                                'width': {
                                    'max': 3840,
                                    'min': 144
                                }
                            },
                            'maxLevel': '5.1',
                            'profiles': ['main', 'main10']
                        }],
                        'hdrFormats': ['hdr10','hdr10plus','dolbyvision','dolbyvision5','dolbyvision8','hlg'],
                    }
                },
                'contentProtection': {
                    'contentDecryptionModules': [{
                        'drmKeySystem': 'widevine',
                        'maxSecurityLevel': 'L1'
                    }]
                },
                'manifests': {
                    'formats': {
                        'dash': {}
                    }
                }
            },
            'consumptionType': 'streaming',
            'deviceInfo': {
                'player': {
                    'mediaEngine': {
                        'name': '',
                        'version': ''
                    },
                    'playerView': {
                        'height': 2176,
                        'width': 3840
                    },
                    'sdk': {
                       'name': '',
                       'version': ''
                    }
                }
            },
            'editId': edit_id,
            'firstPlay': False,
            'gdpr': False,
            'playbackSessionId': str(uuid.uuid4()),
            'userPreferences': {
                #'uiLanguage': 'en'
            }
        }

        data = self._session.post(self._endpoint('/playback-orchestrator/any/playback-orchestrator/v1/playbackInfo'), json=payload).json()
        self._check_errors(data)
        return data

    def logout(self, api_logout=True):
        if userdata.get('access_token') and api_logout:
            try:
                self._session.post(self._endpoint('/logout'), json={})
            except:
                pass
        userdata.delete('user_id')
        userdata.delete('profile')
        userdata.delete('access_token')
        userdata.delete('token_expires')
        userdata.delete('device_id')
        mem_cache.empty()
        self.new_session()
