import arrow
import uuid

from requests.sessions import session

from slyguy import settings, mem_cache, userdata
from slyguy.log import log
from slyguy.session import Session
from slyguy.exceptions import Error

from .constants import *
from .language import _

class APIError(Error):
    pass

UUID_NAMESPACE = '122e1611-0232-4336-bf43-e054c8ecd0d5'
DEVICE_ID = str(uuid.uuid3(uuid.UUID(UUID_NAMESPACE), str(uuid.getnode())))

PLUTO_PARAMS = {
    'deviceId': DEVICE_ID,
    'deviceMake': 'Chrome',
    'deviceType': 'web',
    'deviceVersion': '90.0.4430.212',
    'deviceModel': 'web',
    'DNT': '0',
    'appName': 'web',
    'appVersion': '5.17.0-38a9908bb8d8f15260d990bd00c1f6b49c7bba28',
    'serverSideAds': 'true',
    'channelSlug': '',
    'episodeSlugs': '',
    'channelID': '',
    'clientID': DEVICE_ID,
    'clientModelNumber': 'na',
}

class API(object):
    def new_session(self):
        self._session = Session(HEADERS)
        self._cache_key = self._region = settings.getEnum('region', REGIONS, default=US)

        if self._region in X_FORWARDS:
            self._session.headers.update({'x-forwarded-for': X_FORWARDS[self._region]})

        elif self._region == CUSTOM:
            region_ip = settings.get('region_ip', '0.0.0.0')
            if region_ip != '0.0.0.0':
                self._session.headers.update({'x-forwarded-for': region_ip})
                self._cache_key = region_ip

        self._cache_key += str(settings.getBool('show_epg', False))

    def _process_channels(self, channels):
        for key in channels:
            if 'url' not in channels[key]:
                channels[key]['url'] = PLAY_URL.format(id=key)
            if 'logo' not in channels[key]:
                channels[key]['logo'] = LOGO_URL.format(id=key)

        return channels

    @mem_cache.cached(60*5)
    def all_channels(self):
        channels = self._session.gz_json(MH_DATA_URL.format(region=ALL))
        return self._process_channels(channels)

    def channels(self, region=None):
        channels = mem_cache.get(self._cache_key)
        if channels:
            return channels

        if self._region == ALL or (self._region not in (LOCAL, CUSTOM) and not settings.getBool('show_epg', False)):
            channels = self._session.gz_json(MH_DATA_URL.format(region=self._region))
        else:
            channels = self.epg()

        if not channels:
            raise APIError(_.NO_CHANNELS)

        mem_cache.set(self._cache_key, channels, expires=(60*5))

        return self._process_channels(channels)

    @mem_cache.cached(60*60)
    def _get_session(self):
        data = self._session.get('https://boot.pluto.tv/v4/start', params=PLUTO_PARAMS).json()
        return {'params': data['stitcherParams'], 'session_id': data['session']['sessionID'], 'token': data['sessionToken']}

    def play(self, id):
        data = self._get_session()
        return ALT_URL.format(id=id, params=data['params'])

    def epg(self, start=None, stop=None):
        start = start or arrow.now().replace(minute=0, second=0, microsecond=0).to('utc')
        stop  = stop or start.shift(hours=6)

        params = {}
        params.update(PLUTO_PARAMS)

        if start: params['start'] = start.format('YYYY-MM-DDTHH:MM:SSZZ')
        if stop: params['stop'] = stop.format('YYYY-MM-DDTHH:MM:SSZZ')

        data = self._session.get(EPG_URL, params=params).json()

        categories = {}
        for row in data.get('categories', []):
            categories[row['id']] = row['name']

        channels = {}
        for row in data.get('channels', []):
            channels[row['id']] = {
                'chno': row['number'],
                'name': row['name'],
                'group': categories[row['categoryID']],
                'logo': LOGO_URL.format(id=row['id']),
                'programs': row.get('timelines', []),
            }

        return channels