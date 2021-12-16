import re
import time

from bs4 import BeautifulSoup
from slyguy import userdata, inputstream, mem_cache
from slyguy.session import Session
from slyguy.exceptions import Error
from slyguy.util import hash_6, jwt_data

from .constants import *
from .language import _

class APIError(Error):
    pass

class API(object):
    def new_session(self):
        self.logged_in = False
        self._session = Session(base_url=BASE_URL, headers=HEADERS)
        self._set_auth(userdata.get('token'))

    def _set_auth(self, token):
        if not token:
            return

        self._session.cookies.update({'_session': token, '_device': userdata.get('device_id')})
        self.logged_in = True

    def login(self, username, password):
        self.logout(site_logout=False)

        device_id = hash_6(username.lower().strip(), length=20)
        device_id = 'Windows:Chrome:' + device_id[:5] + '_' + device_id[5:13] + '_' + device_id[13:]
        self._session.cookies.update({'_device': device_id})

        resp = self._session.get('/login')
        soup = BeautifulSoup(resp.text, 'html.parser')

        found = None
        for form in soup.find_all('form'):
            data = {}
            for e in form.find_all('input'):
                data[e.attrs['name']] = e.attrs.get('value')

            if 'email' in data and 'password' in data:
                found = data
                break

        if not found:
            raise APIError(_.LOGIN_FORM_ERROR)

        found.update({
            'email': username,
            'password': password,
        })

        resp = self._session.post('/login', data=data, allow_redirects=False)
        if resp.status_code != 302 or not resp.cookies.get('_session'):
            raise APIError(_.LOGIN_FAILED)

        token = resp.cookies.get('_session')
        userdata.set('token', token)
        userdata.set('device_id', device_id)

        self._set_auth(token)

    def play(self, slug):
        resp = self._session.get('/videos/{slug}'.format(slug=slug), allow_redirects=False)

        if resp.status_code == 302 or 'The device limit for your account has been reached' in resp.text:
            raise APIError(_.DEVICE_LIMIT)

        page = resp.text.replace(' ', '').strip()
        play_url = re.search('embed_url:"(.*?)"', page).group(1)

        resp = self._session.get(play_url)
        page = resp.text.replace(' ', '').strip()

        event_id = re.search('eventId:(.*?),', page)

        if event_id:
            config_url = LIVESTREAM_URL.format(event_id=event_id.group(1))
        else:
            config_url = re.search('"config_url":"(.*?)"', page).group(1)
            config_url = config_url.encode().decode('unicode_escape')

        data = self._session.get(config_url, headers={'Referer': 'https://embed.vhx.tv/'}).json()
        if data.get('secure_m3u8_url'):
            return data['secure_m3u8_url'], inputstream.HLS()

        default_cdn = data['request']['files']['dash']['default_cdn']
        mpd_url = data['request']['files']['dash']['cdns'][default_cdn]['url']#.replace('.json?base64_init=1', '.mpd')
        mpd_url = mpd_url.replace('.json', '.mpd')

        if data['request'].get('drm'):
            license_url = self._session.get(data['request']['drm']['cdms']['widevine']['license_url']).text
            ia = inputstream.Widevine(license_key=license_url)
        else:
            ia = inputstream.MPD()

        return mpd_url, ia

    def _vhx_token(self):
        token = mem_cache.get('vhx_token')
        if token:
            return token

        page = self._session.get('/').text.replace(' ', '').strip()
        token = re.search('TOKEN="(.*?)"', page).group(1)
        data = jwt_data(token)
        expires_in = int(data['exp'] - time.time()) - 30
        mem_cache.set('vhx_token', token, expires_in)

        return token

    def browse(self, page=1, per_page=100):
        params = {
            'product': 'https://api.vhx.tv/products/70302',
            'per_page': per_page,
            'page': page,
        }

        return self._session.get('https://api.vhx.tv/browse', params=params, headers={'Authorization': 'Bearer {}'.format(self._vhx_token())}).json()

    def collection(self, id, page=1, per_page=100):
        params = {
            'page': page,
            'per_page': per_page,
        }

        return self._session.get('https://api.vhx.tv/collections/{}/items'.format(id), params=params, headers={'Authorization': 'Bearer {}'.format(self._vhx_token())}).json()

    def search(self, query, page=1, per_page=100):
        params = {
            'query': query,
            'product': 'https://api.vhx.tv/products/70302',
            'page': page,
            'per_page': per_page,
        }

        return self._session.get('https://api.vhx.tv/collections', params=params, headers={'Authorization': 'Bearer {}'.format(self._vhx_token())}).json()

    def logout(self, site_logout=True):
        if site_logout:
            self._session.get('/logout')

        userdata.delete('token')
        userdata.delete('device_id')
        mem_cache.delete('vhx_token')

        self.new_session()
