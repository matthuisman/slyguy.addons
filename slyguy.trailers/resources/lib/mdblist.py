from slyguy.session import Session

from .constants import MDBLIST_API_KEY, MDBLIST_API_URL


class API(object):
    def __init__(self):
        self._session = Session(base_url=MDBLIST_API_URL)

    def _get_media_type(self, mediatype):
        mediatype = mediatype.lower()
        if mediatype in ('tvshow', 'show'):
            return 'show'
        elif mediatype in ('movie',):
            return 'movie'
        return None

    def _get_id_type(self, id_type):
        id_type = id_type.lower()
        if id_type.endswith('id'):
            return id_type[:-2]
        else:
            return id_type

    def search_media(self, mediatype, title, year, limit=10):
        mediatype = self._get_media_type(mediatype)

        params = {
            'query': title,
            'year': year,
            'limit': limit,
            'apikey': MDBLIST_API_KEY,
        }
        return self._session.get('/search/{}'.format(mediatype), params=params).json()['search']

    def get_media(self, mediatype, id, id_type=None):
        mediatype = self._get_media_type(mediatype)

        id_types = []
        if not id_type:
            if 'tt' in id.lower():
                id_types = ['imdb']
            elif mediatype == 'movie':
                id_types = ['tmdb']
            else:
                # can be tvdb or tmdb for shows
                id_types = ['tvdb', 'tmdb']
        else:
            id_types = [self._get_id_type(id_type)]

        params = {
            'apikey': MDBLIST_API_KEY,
        }
        for id_type in id_types:
            data = self._session.get('/{}/{}/{}'.format(id_type, mediatype, id), params=params).json()
            if data.get('title'):
                return data

        return {}
