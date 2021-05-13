import arrow
import uuid

from six.moves.urllib.parse import urlsplit, parse_qsl, urlencode

from slyguy import settings, mem_cache
from slyguy.session import Session
from slyguy.log import log
from slyguy.mem_cache import cached
from slyguy.exceptions import Error

from .constants import *
from .language import _

class APIError(Error):
    pass

UUID_NAMESPACE = '122e1611-0232-4336-bf43-e054c8ecd0d5'
DEVICE_ID = str(uuid.uuid3(uuid.UUID(UUID_NAMESPACE), str(uuid.getnode())))
SID = str(uuid.uuid3(uuid.UUID(UUID_NAMESPACE), DEVICE_ID))

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

            channels[key]['url'] = channels[key]['url'].replace('%7Bdevice_id%7D', DEVICE_ID)
            channels[key]['url'] = channels[key]['url'].replace('%7Bsid%7D', SID)

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

    # def play(self, id):
    #     params = {}
    #     params.update(PLUTO_PARAMS)
    #     params['channelID'] = id

    #     data = self._session.get('https://boot.pluto.tv/v4/start', params=params).json()

    #     if data['EPG'][0]['isStitched']:
    #         return PLAY_URL.format(id=id, params=data['stitcherParams'])
    #     else:
    #         for row in data['EPG'][0].get('timelines', []):
    #             try: return row['episode']['sourcesWithClipDetails'][0]['sources'][0]['file']
    #             except: pass
    #             else: break

    #     return None

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