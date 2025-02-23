from difflib import SequenceMatcher

from slyguy.session import Session
from slyguy import util, mem_cache
from slyguy.exceptions import Error
from six.moves.urllib_parse import urljoin

from .constants import HEADERS, API_URL, BRIGHTCOVE_URL, BRIGHTCOVE_KEY, BRIGHTCOVE_ACCOUNT, SEARCH_MATCH_RATIO


class APIError(Error):
    pass


class API(object):
    def __init__(self):
        self._session = Session(HEADERS, base_url=API_URL)

    @mem_cache.cached(60*5)
    def live(self):
        return self._get_page('live-epg')['channels']

    @mem_cache.cached(60*10)
    def _shows(self):
        return self._get_page('shows')

    def shows(self):
        return self._shows()['shows']

    @mem_cache.cached(60*5)
    def show(self, id):
        return self._get_page('shows/{}'.format(id))

    def _get_page(self, url):
        data = self._session.get(url).json()
        if 'statusCode' in data and str(data['statusCode'])[0] != '2':
            raise APIError(data.get('message'))
        return data

    def channels(self):
        return self._shows()['channels']

    def genres(self):
        genres = self.channels()
        genres.extend(self._shows()['genres'])
        return genres

    def genre(self, genre):
        shows = []

        for show in self.shows():
            if genre in show['genres'] or genre == show['channelId']:
                shows.append(show)

        return shows

    def lsai(self, row):
        url = row['videoRenditions']['lsai']['csab']
        payload = {
            "adsParams":{
                "channelId":"x",
                "watchFromStart":"",
                "PPID":"x",
                "cust_params":"x",
                "sz":"620x288",
                "iu_parts":"x",
                "description_url":"x",
                "url":"x",
                "platform":"desktop"
            }
        }
        return urljoin(url, self._session.post(url, json=payload).json()['manifestUrl'])

    def search(self, query):
        shows = []

        for show in self.shows():
            if query.lower() in show['name'].lower() or SequenceMatcher(None, query.lower(), show['name'].lower()).ratio() >= SEARCH_MATCH_RATIO:
                shows.append(show)

        return shows

    def get_brightcove_src(self, referenceID):
        brightcove_url = BRIGHTCOVE_URL.format(BRIGHTCOVE_ACCOUNT, referenceID)

        resp = self._session.get(brightcove_url, headers={'BCOV-POLICY': BRIGHTCOVE_KEY})
        data = resp.json()

        return util.process_brightcove(data)