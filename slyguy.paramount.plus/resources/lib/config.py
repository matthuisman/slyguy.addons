from slyguy import userdata
from slyguy.constants import ADDON_VERSION
from slyguy.session import Session
from slyguy.log import log
from slyguy.util import get_url_headers

REGION_US = 'US'
REGION_INTL = 'INTL'

CONFIG = {
    REGION_US: {
        'base_url': 'https://www.paramountplus.com',
        'at_token': 'ABC+2JjrOUYWbaaqKmzwPdppq0RDB2WdufcFmIsSnJDmDEQpVgyAjQpqpEDksKZNMKQ=',
        'link_platform_url': 'http://link.theplatform.com/s/dJ5BDC/media/guid/2198311517/{video_id}',
        'device_link': True,
    },
    REGION_INTL: {
        'base_url': 'https://www.intl.paramountplus.com',
        'at_token': 'ABAS/G30Pp6tJuNOlZ1OEE6Rf5goS0KjICkGkBVIapVuxemiiASyWVfW4v7SUeAkogc=',
        'device_link': False,
    }
}

REGIONS = [REGION_US, REGION_INTL]

class Config(object):
    def __init__(self):
        self._config = {}

    def init(self, fresh=False):
        if not fresh:
            self._config = userdata.get('config') or {}
            if not self._config or self._config.get('version') == ADDON_VERSION:
                return self._config

        self.clear()
        for region in REGIONS:
            config = self.load_config(region)
            if config:
                self._config = config
                break

        if self._config:
            self.save()

        return self._config

    @property
    def headers(self):
        return {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.37',
        }

    def clear(self):
        self._config = {}
        self.save()

    def refresh(self):
        log.debug('Refreshing config')
        config = self.load_config(self.region)
        if not config:
            log.debug('Failed to refresh config. using existing config')
        else:
            self._config = config
            self.save()

    @property
    def at_token(self):
        return CONFIG[self.region]['at_token']

    @property
    def loaded(self):
        return self._config.get('region') != None

    @property
    def region(self):
        return self._config['region']

    @property
    def country_code(self):
        return self._config['country']

    @property
    def locale(self):
        return self._config['locale']

    @property
    def episodes_section(self):
        return CONFIG[self.region]['episodes_section']

    @property
    def playhead_url(self):
        return CONFIG[self.region]['base_url'].replace('https://www.', 'https://sparrow.') + '/streamer/v1.0/ingest/beacon.json'

    @property
    def api_url(self):
        return CONFIG[self.region]['base_url'] + '/apps-api{}'

    @property
    def ip_url(self):
        return CONFIG[self.region]['base_url'] + '/apps/user/ip.json'

    @property
    def device_link_url(self):
        return CONFIG[self.region]['base_url'] + '/androidtv'

    def has_mvpd(self):
        return self._config['mvpd']

    def get_link_platform_url(self, video_id):
        url = CONFIG[self.region].get('link_platform_url')
        return url.format(video_id=video_id) if url else None

    def has_device_link(self):
        return CONFIG[self.region]['device_link']

    def has_profiles(self):
        return self._config['profiles']

    def has_home(self):
        return self._config['home']

    def has_movies(self):
        return self._config['movies']

    def has_live_tv(self):
        return self._config['live_tv']

    def has_news(self):
        #todo
        return False

    def has_brands(self):
        #return self._config['brands']
        return False

    def image(self, image_name, dimensions='w400'):
        return '{base_url}/thumbnails/photos/{dimensions}/{file}|{headers}'.format(base_url=CONFIG[self.region]['base_url'], dimensions=dimensions, file=image_name[6:], headers=get_url_headers(self.headers)) if image_name else None

    def thumbnail(self, image_url, dimensions='w400'):
        return image_url.replace('https://thumbnails.cbsig.net/', 'https://thumbnails.cbsig.net/_x/{}/'.format(dimensions))

    def save(self):
        userdata.set('config', self._config)

    def load_config(self, region):
        resp = Session().get(CONFIG[region]['base_url']+'/apps-api/v2.0/androidphone/app/status.json', params={'at': CONFIG[region]['at_token']}, headers=self.headers)
        if not resp.ok:
            return None

        data = resp.json()
        app_version = data['appVersion']
        app_config = data['appConfig']

        if not app_version.get('availableInRegion'):
            return None

        app_locale = 'en-us'
        for locale in data.get('localesSupport', []):
            if locale.get('isDefaultLanguage'):
                app_locale = locale['lang']
                break

        config = {
            'version': ADDON_VERSION,
            'region': region,
            'locale': app_locale,
            'country': app_version['clientRegion'],
            'mvpd': app_version['clientRegion'] in app_config.get('mvpd_enabled_countries', []),
            'live_tv': app_config.get('livetv_disabled') != 'true',
            'feed_id': app_config.get('live_tv_national_feed_content_id'),
            'home': True if region == REGION_US else app_config.get('homepage_configurator_enabled') == 'true',
            'movies': True if region == REGION_US else app_config.get('movies_enabled') == 'true',
            'movies_trending': True if region == REGION_US else app_config.get('movies_trending_enabled') == 'true',
            'movie_genres': True if region == REGION_US else app_config.get('movies_genres_enabled') == 'true',
            'brands': True if region == REGION_US else app_config.get('brands_enabled') == 'true',
            'fathom': app_config.get('fathom_enabled') == 'true',
            'freewheel': app_config.get('freewheel_enabled') == 'true',
            'syncback': app_config.get('syncbak_enabled') == 'true',
            'sports_hq': app_config.get('sports_hq_enabled') == 'true',
            'profiles': app_config.get('user_profiles') == 'true',
        }

        return config

    # # https://github.com/matthuisman/slyguy.addons/issues/136
    # def _at_token(self):
    #     payload = '{}|{}'.format(int(time())*1000, CONFIG[self.region]['aes_secret'])

    #     try:
    #         #python3
    #         key = bytes.fromhex(CONFIG[self.region]['aes_key'])
    #     except AttributeError:
    #         #python2
    #         key = str(bytearray.fromhex(CONFIG[self.region]['aes_key']))

    #     iv = os.urandom(16)
    #     encrypter = pyaes.Encrypter(pyaes.AESModeOfOperationCBC(key, iv))

    #     ciphertext = encrypter.feed(payload)
    #     ciphertext += encrypter.feed()
    #     ciphertext = b'\x00\x10' + iv + ciphertext

    #     return b64encode(ciphertext).decode('utf8')
