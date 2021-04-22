from difflib import SequenceMatcher

from slyguy.session import Session
from slyguy import util, mem_cache

from .constants import HEADERS, API_URL, BRIGHTCOVE_URL, BRIGHTCOVE_KEY, BRIGHTCOVE_ACCOUNT, SEARCH_MATCH_RATIO

class API(object):
    def __init__(self):
        self._session = Session(HEADERS, base_url=API_URL)

    @mem_cache.cached(60*10)
    def _shows(self):
        return self._session.get('shows').json()

    def shows(self):
        return self._shows()['shows']

    def show(self, id):
        return self._session.get('shows/{}'.format(id)).json()['show']

    def channels(self):
        return self._shows()['channels']

    def live(self):
        return self._session.get('live-epg').json()['channels']

    def genres(self):
        genres = self.channels()
        genres.extend(self._shows()['genres'])
        return genres

    def genre(self, genre):
        shows = []
        
        for show in self.shows():
            if genre in show['genres'] or genre == show['channel']:
                shows.append(show)

        return shows

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