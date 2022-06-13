from slyguy import util, mem_cache
from slyguy.session import Session

from .constants import HEADERS, API_URL, BRIGHTCOVE_URL, BRIGHTCOVE_KEY, BRIGHTCOVE_ACCOUNT

class API(object):
    def __init__(self):
        self._session = Session(HEADERS, base_url=API_URL)
        #x-tvnz-active-profile-id (profile support)

    @mem_cache.cached(60*30)
    def _category(self, slug):
        return self._session.get('/api/v2/android/play/page/categories/{}'.format(slug)).json()

    def category(self, slug):
        shows = []

        data = self._category(slug)

        for module in data['layout']['slots']['main']['modules']:
            items = module.get('items', [])

            for section in module.get('sections', []):
                items.extend(section.get('items', []))

            for item in items:
                item['_embedded'] = data['_embedded'][item['href']]
                shows.append(item)
        
        return data['title'], shows

   # @mem_cache.cached(60*5)
    def featured(self):
        sections = []

        data = self._session.get('/api/v2/android/play/page/').json()
        order = ['hero', 'above', 'main', 'below', '_other']
        for _type in sorted(data['layout']['slots'], key=lambda x: order.index(x) if x in order else order.index('_other')):
            for module in data['layout']['slots'][_type].get('modules', []):
                if module.get('type') != 'featuredContent':
                    continue

                items = module.get('items', [])
                if not items:
                    continue

                sections.append({
                    'name': module['title'],
                    'href': module['id'],
                })

        return sections

    def featured_href(self, href):
        data = self._session.get(href).json()
        for row in data['items']:
            row['_embedded'] = data['_embedded'][row['href']]
        return data

    def a_to_z(self):
        data = self._category('all')

        for section in data['layout']['slots']['main']['modules'][0]['sections']:
            for row in section['items']:
                row['_embedded'] = data['_embedded'][row['href']]

        return data['layout']['slots']['main']['modules'][0]['sections']

    def categories(self):
        data = self._category('all')
        
        for row in data['layout']['slots']['below']['modules'][0]['items']:
            row['_embedded'] = data['_embedded'][row['href']]

        return data['layout']['slots']['below']['modules'][0]['items']

    def show(self, slug):
        data = self._session.get('/api/v2/android/play/page/shows/{}'.format(slug)).json()

        show = data['_embedded'][data['layout']['showHref']]
        sections = data['layout']['slots']['main']['modules'][0].get('sections', [])

        for section in sections:
            section['_embedded'] = data['_embedded'][section['href']]
            
        return show, sections, data['_embedded']

    def video_list(self, href):
        data = self._session.get(href).json()

        for row in data['content']:
            row['_embedded'] = data['_embedded'][row['href']]

        return data['content'], data['nextPage']

    def similar(self, href):
        data = self._session.get(href).json()

        for row in data['layout']['slots']['main']['modules'][0]['items']:
            row['_embedded'] = data['_embedded'][row['href']]

        return data['layout']['slots']['main']['modules'][0]['items']

    def search(self, query):
        params = {
            'q': query.strip(),
            'includeTypes': 'all',
        }

        return self._session.get('/api/v1/android/play/search', params=params).json()['results']

    def channels(self):
        data = self._session.get('/api/v2/android/play/page/livetv/').json()

        for row in data['layout']['slots']['hero']['modules'][1]['items']:
            row['_embedded'] = data['_embedded'][row['href']]

        return data['layout']['slots']['hero']['modules'][1]['items']
    
    def channel(self, slug):
        return self._session.get('/api/v1/android/play/channels/{}'.format(slug)).json()

    def get_brightcove_src(self, referenceID):
        brightcove_url = BRIGHTCOVE_URL.format(BRIGHTCOVE_ACCOUNT, referenceID)
        
        resp = self._session.get(brightcove_url, headers={'BCOV-POLICY': BRIGHTCOVE_KEY})
        data = resp.json()

        return util.process_brightcove(data)
