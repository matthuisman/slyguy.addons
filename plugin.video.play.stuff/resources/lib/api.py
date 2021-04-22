from slyguy import userdata, util
from slyguy.session import Session
from slyguy.exceptions import Error
from slyguy.mem_cache import cached

from .language import _
from .constants import API_URL, HEADERS, UUID, APPID, LOCALE, BRIGHTCOVE_URL, BRIGHTCOVE_ACCOUNT, BRIGHTCOVE_KEY

class APIError(Error):
    pass

class API(object):
    def new_session(self):
        self._session = Session(HEADERS, base_url=API_URL)

    def search(self, query, page=1, pagesize=15):
        params = {
            'uuid':   UUID,
            'appId':  APPID,
            'locale': LOCALE,
            'text': query,
            'pageSize': pagesize,
            'pageNumber': page,
            'sortBy': 'name',
            'sortOrder': 'asc',
        }

        data = self._session.get('/search', params=params).json()

        for row in data.get('item', []):
            row['attribs'] = {}

            for row2 in row['attributes']:
                row['attribs'][row2['key']] = row2['value']

            row.pop('attributes', None)

        return data

    @cached(60*30)
    def page(self, id):
        params = {
            'uuid':   UUID,
            'appId':  APPID,
            'locale': LOCALE,
        }

        data = self._session.get('/page/{}'.format(id), params=params).json()

        items = {}
        for row in data['item']:
            row['attribs'] = {}

            for row2 in row['attributes']:
                row['attribs'][row2['key']] = row2['value']

            row.pop('attributes', None)
            items[row['id']] = row

        containers = {}
        for row in data['container']:
            row['attribs'] = {}
            row['items']   = []

            for row2 in row['attributes']:
                row['attribs'][row2['key']] = row2['value']

            for item_id in row.get('itemId', []):
                item = items[item_id]
                row['items'].append(item)

            row.pop('itemId', None)
            row.pop('attributes', None)

            containers[row['id']] = row

        page = data['page']
        page['attribs'] = {}
        page['containers'] = []

        for row2 in page['attributes']:
            page['attribs'][row2['key']] = row2['value']

        for container_id in page['containerId']:
            container = containers[container_id]
            if container['items']:
                page['containers'].append(container)

        page.pop('containerId', None)
        page.pop('attributes', None)

        return page

    def get_brightcove_src(self, referenceID):
        brightcove_url = BRIGHTCOVE_URL.format(BRIGHTCOVE_ACCOUNT, referenceID)
        
        resp = self._session.get(brightcove_url, headers={'BCOV-POLICY': BRIGHTCOVE_KEY})
        data = resp.json()

        return util.process_brightcove(data)