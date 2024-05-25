from time import time

from slyguy import util, userdata
from slyguy.util import jwt_data
from slyguy.mem_cache import cached
from slyguy.session import Session

from .constants import *


class API(object):
    def __init__(self):
        self._session = Session(HEADERS, base_url=API_URL)

    def featured(self):
        return self._session.get('/home', params={'device': 'web'}).json()

    def shows(self):
        return self._session.get('/tv-series', params={'device': 'web'}).json()['tvSeries']

    def show(self, show):
        return self._session.get('/tv-series/{show}'.format(show=show), params={'device': 'web'}).json()

    def episodes(self, show, season, page=1, items_per_page=None):
        params = {
            'device': 'web',
            'sort': '',
        }

        if items_per_page:
            params['take'] = items_per_page
            params['skip'] = (page-1)*items_per_page

        return self._session.get('/tv-series/{show}/seasons/{season}/episodes'.format(show=show, season=season), params=params).json()

    def clips(self, show, season, page=1, items_per_page=None):
        params = {
            'device': 'web',
            'sort': '',
            'tagSlug': '',
        }

        if items_per_page:
            params['take'] = items_per_page
            params['skip'] = (page-1)*items_per_page

        return self._session.get('/tv-series/{show}/seasons/{season}/clips'.format(show=show, season=season), params=params).json()

    def categories(self):
        return self._session.get('/genres', params={'device': 'web'}).json()['genres']

    def category(self, category):
        return self._session.get('/genres/{category}'.format(category=category), params={'device': 'web'}).json()

    def _get_token(self):
        token = userdata.get('shared_token')
        if token:
            token_data = jwt_data(token)
            if token_data['exp'] > time() - 60:
                return token

        token = self._session.get(TOKEN_URL).text.strip()
        userdata.set('shared_token', token)
        return token

    @cached(60*5)
    def channels(self, region):
        params = {
            'device': 'web',
            'streamParams': 'web,chrome,windows',
            'token': self._get_token(),
            'region': region,
            'offset': 0,
        }
        return self._session.get(LIVESTREAM_URL, params=params).json()['data']['getLivestream']

    def get_brightcove_src(self, reference):
        if not reference.isdigit():
            reference = 'ref:{}'.format(reference)

        brightcove_url = BRIGHTCOVE_URL.format(BRIGHTCOVE_ACCOUNT, reference)
        resp = self._session.get(brightcove_url, headers={'BCOV-POLICY': BRIGHTCOVE_KEY})
        return util.process_brightcove(resp.json())
