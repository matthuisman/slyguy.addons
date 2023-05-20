import uuid
import time
import json
import threading
import random
import string
from contextlib import contextmanager

import websocket
from six.moves.urllib_parse import urlparse, parse_qs

from slyguy import userdata, settings
from slyguy.session import Session
from slyguy.log import log
from slyguy.exceptions import Error
from slyguy.util import jwt_data, get_system_arch, add_url_args

from .language import _
from .constants import *

class APIError(Error):
    pass

class API(object):
    def __init__(self):
        self.new_session()

    def new_session(self):
        self._logged_in = False
        self._session = Session(HEADERS, base_url=API_URL, timeout=TIMEOUT)
        self._set_access_token(userdata.get('access_token'))

    def _set_access_token(self, token):
        if token:
            self._session.headers.update({'Authorization': token})
            self._logged_in = True

            profile_id = userdata.get('profile')
            if profile_id:
                self._session.headers.update({'x-profile-id': profile_id})

    @property
    def logged_in(self):
        return self._logged_in

    def _parse_tokens(self, access_token, id_token):
        jwt = jwt_data(access_token)

        userdata.set('access_token', access_token)
        userdata.set('id_token', id_token)
        userdata.set('token_expires', int(time.time()) + (jwt['exp'] - jwt['iat'] - 30))
        userdata.set('country', jwt['country'])
        userdata.set('package', jwt['package'])

        self._set_access_token(access_token)

    def _refresh_token(self, force=False):
        if not self._logged_in:
            raise APIError(_.PLUGIN_LOGIN_REQUIRED)

        expires = userdata.get('token_expires', 0)
        if not force and expires > time.time():
            return

        payload = {
            'idToken': userdata.get('id_token'),
            'accessToken': userdata.get('access_token'),
        }

        data = self._session.post(REFRESH_TOKEN_URL, json=payload).json()
        if not data.get('accessToken') or not data.get('idToken'):
            raise APIError(_(_.REFRESH_TOKEN_ERROR, msg=data.get('reason')))

        self._parse_tokens(data['accessToken'], data['idToken'])

    def profiles(self):
        return self._request_json('/cs-mobile/v6/profiles')['items']

    def _request_json(self, url, type='get', timeout=30, attempts=3, refresh_token=True, **kwargs):
        if refresh_token:
            self._refresh_token(force=refresh_token == 'force')

        data = {}
        for i in range(attempts):
            if i > 0:
                log.debug("Try {}/{}".format(i+1, attempts))

            r = self._session.request(type, url, timeout=timeout, attempts=1, **kwargs)
            try: data = r.json()
            except: continue

            if 'errorCode' in data:
                break

            if r.ok:
                return data
            elif not str(r.status_code).startswith('5'):
                break

        if 'errorMessage' in data:
            raise APIError(_(_.API_ERROR, msg=data['errorMessage']))
        elif 'reason' in data:
           raise APIError(_(_.API_ERROR, msg=data['reason']))
        else:
            raise APIError(_(_.REQUEST_ERROR, url=url.split(';')[0], code=r.status_code))

    def content(self, tags, sort, category='', page=1, pagesize=24):
        category = 'filter={};'.format(category) if category else ''

        data = self._request_json('/cs-mobile/now-content/v6/catalogueByPackageAndCountry;videoAssetsFilter=HasStream;productId={product};platformId={platform};tags={tags};subscriptionPackage={package};country={country};{category}sort={sort};page={page};pageSize={pagesize}'.format(
            product=PRODUCT_ID, platform=PLATFORM_ID, tags=tags, country=userdata.get('country', DEFAULT_COUNTRY), package=userdata.get('package', DEFAULT_PACKAGE), sort=sort, category=category, page=page-1, pagesize=pagesize,
        ))

        return data

    def search(self, query):
        data = self._request_json('/cs-mobile/now-content/v6/search;platformId={platform};searchTerm={query}'.format(
            platform=PLATFORM_ID, query=query
        ))

        return data['items'][0]['editorialItems']

    def channels(self, events=2):
        data = self._request_json('/cs-mobile/v7/epg-service/channels/events;genre={genre};platformId={platform};country={country};packageId={package};count={events};utcOffset=+00:00'.format(
            genre='ALL', platform=PLATFORM_ID, country=userdata.get('country', DEFAULT_COUNTRY), package=userdata.get('package', DEFAULT_PACKAGE), events=events
        ))

        return data['items']

    def epg(self, tag, start_date, end_date=None, attempts=3):
        end_date = end_date or start_date.shift(hours=24)

        for i in range(attempts):
            try:
                data = self._request_json('/cs-mobile/epg/v7/getEpgSchedulesByTag;channelTags={tag};startDate={start};endDate={end}'.format(
                    tag=tag, start=start_date.format('YYYY-MM-DDT00:00:00ZZ'), end=end_date.format('YYYY-MM-DDT00:00:00ZZ')
                ), attempts=1)
            except:
                continue

            if len(data.get('items', 0)) > 0:
                break

        return data['items']

    def series(self, id):
        data = self._request_json('/cs-mobile/now-content/v6/getCatalogue;productId={product};platformId={platform};programId={id}'.format(
            product = PRODUCT_ID, platform = PLATFORM_ID, id = id
        ))

        return data['items'][0]['program']

    def get_video(self, id):
        data = self._request_json('/cs-mobile/now-content/v6/getCatalogue;productId={product};platformId={platform};videoId={id}'.format(
            product = PRODUCT_ID, platform = PLATFORM_ID, id = id
        ))

        return data['items'][0]['video']

    def get_channel(self, id):
        for channel in self.channels():
            if channel['id'] == id:
                return channel

        raise APIError(_(_.CHANNEL_NOT_FOUND, id=id))

    def stream_token(self, channel_tag):
        return self._request_json('/dstv_now/play_stream/access_token?channel_tag={}'.format(channel_tag), type='post')['access_token']

    def play_channel(self, id):
        channel = self.get_channel(id)

        stream_url = None
        for stream in channel['streams']:
            if stream['streamType'] in ('MobileAlt' ,'WebAlt'):
                stream_url = stream['playerUrl']
                break

        if not stream_url:
            raise APIError(_.STREAM_ERROR)

        parsed = urlparse(stream_url)
        content_id = parse_qs(parsed.query)['contentId'][0]

        stream_url, license_url, headers = self.play_asset(stream_url, content_id)
        stream_url = add_url_args(stream_url, {'hdnts': self.stream_token(channel['id'])})
        return stream_url, license_url, headers

    def play_video(self, id):
        video = self.get_video(id)
        if not video.get('videoAssets'):
            raise APIError(_.STREAM_ERROR)

        stream_url = video['videoAssets'][0]['url']
        content_id = video['videoAssets'][0]['manItemId']

        return self.play_asset(stream_url, content_id)

    def play_asset(self, stream_url, content_id):
        if '.isml' in stream_url:
            stream_url = stream_url.replace('.isml', '.isml/.mpd')
        elif '.ism' in stream_url:
            stream_url = stream_url.replace('.ism', '.ism/.mpd')

        payload = {
            "device_id": self._device_id(),
            "device_name": "chrome",
            "device_type": "web",
            "drm": "widevine",
            "hdcp": "Unprotected",
            "hdcp_max": "Unprotected",
            "os": "Windows",
            "os_version": "10.0",
            "platform_id": PLATFORM_ID,
            "security_level": "L3",
            "session_type": "streaming"
        }

        session = self._request_json('/vod-auth/entitlement/session', json=payload, type='post')
        session = session['session']

        license_url = LICENSE_URL.format(content_id, session)
        return stream_url, license_url, HEADERS

    def _device_id(self):
        def _format_id(string):
            try:
                mac_address = uuid.getnode()
                if mac_address != uuid.getnode():
                    mac_address = ''
            except:
                mac_address = ''

            system, arch = get_system_arch()
            return str(string.format(mac_address=mac_address, system=system).strip())

        return str(uuid.uuid3(uuid.UUID(UUID_NAMESPACE), _format_id(settings.get('device_id'))))

    @contextmanager
    def device_login(self):
        device_id = self._device_id()

        payload = {
            'deviceId': device_id,
        }

        data = self._request_json('/lean-back-otp/device/registration', type='post', json=payload, refresh_token=False)
        code = data['userCode']

        log.debug('Device ID: {} | Device Code: {}'.format(device_id, code))

        login = DeviceLogin(device_id, code)

        try:
            yield login
        finally:
            login.stop()

        if login.result:
            token_data = login.token_data()
            self._parse_tokens(token_data['accessToken'], token_data['idToken'])

    def logout(self):
        userdata.delete('access_token')
        userdata.delete('id_token')
        userdata.delete('token_expires')
        userdata.delete('country')
        userdata.delete('package')
        userdata.delete('profile')
        userdata.delete('user_agent')
        self.new_session()

class DeviceLogin(object):
    def __init__(self, device_id, code):
        self._code = code
        self._device_id = device_id
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
    def device_id(self):
        return self._device_id

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
            payload = {
                'event': 'pusher:subscribe',
                'data': {
                    'channel': self._device_id,
                }
            }

            self._ws = websocket.create_connection(WEBSOCKET_URL, suppress_origin=True)
            self._ws.send(json.dumps(payload))

            while not self._stop:
                try:
                    data = json.loads(self._ws.recv())
                    if data['event'] == 'login-success':
                        self._token_data = json.loads(data['data'])
                        return
                except:
                    break