from slyguy import settings

HEADERS = {
    'user-agent': 'okhttp/3.14.2',
}

IMG_URL = 'https://wwwimage-us.pplusstatic.com/thumbnails/photos/{dimensions}/{file}'
LINK_PLATFORM_URL = 'https://link.theplatform.com/s/{account}/{pid}'

REGION_US = {
    'base_url': 'https://www.paramountplus.com',
    'tv_token': 'ABCqWNNSwhIqINWIIAG+DFzcFUvF8/vcN6cNyXFFfNzWAIvXuoVgX+fK4naOC7V8MLI=',
    'mobile_token': 'ABDgN5jjASP6TnsBgfAouEMTWtesH/Rk/BFdMhWkDP5okWhvl43z1KQiBC4YkgQttS4=',
    'aes_key': '302a6a0d70a7e9b967f91d39fef3e387816e3095925ae4537bce96063311f9c5',
    'tv_secret': '415f7ae1f42f5cec',
    'mobile_secret': '003ff1f049feb54a',
    'device_link': True,
    'featured': True,
    'live_tv': True,
    'episodes_section': 'DEFAULT_APPS_FULL_EPISODES',
}

REGION_INTL = {
    'base_url': 'https://www.intl.paramountplus.com',
    'tv_token': 'ABAS/G30Pp6tJuNOlZ1OEE6Rf5goS0KjICkGkBVIapVuxemiiASyWVfW4v7SUeAkogc=',
    'mobile_token': 'ABACev7BJWp2uW4TiEu/FBbUnqfgW7AzjSf2GfqySbARww3ByzSThV5oEOLOqiS16Tc=',
    'episodes_section': 'INTL_SHOW_LANDING',
}

REGIONS = [REGION_US, REGION_INTL]

class Config(object):
    def load(self):
        self._region = settings.getEnum('region_index', REGIONS, default=REGION_US)

    @property
    def api_url(self):
        return self._region['base_url'] + '/apps-api{}'

    @property
    def ip_url(self):
        return self._region['base_url'] + '/apps/user/ip.json'

    @property
    def country_code(self):
        return 'US'

    @property
    def tv_token(self):
        return self._region['tv_token']

    @property
    def mobile_token(self):
        return self._region['mobile_token']

    @property
    def has_device_link(self):
        return self._region.get('device_link', False)

    @property
    def has_featured(self):
        return self._region.get('featured', False)

    @property
    def has_live_tv(self):
        return self._region.get('live_tv', False)

    @property
    def device_link_url(self):
        return self._region['base_url'] + '/androidtv'

    @property
    def episodes_section(self):
        return self._region['episodes_section']

    def image(self, image_name, dimensions='w400'):
        return '{base_url}/thumbnails/photos/{dimensions}/{file}'.format(base_url=self._region['base_url'], dimensions=dimensions, file=image_name[6:]) if image_name else None

    def thumbnail(self, image_url, dimensions='w400'):
        return image_url.replace('https://thumbnails.cbsig.net/', 'https://thumbnails.cbsig.net/_x/{}/'.format(dimensions))
