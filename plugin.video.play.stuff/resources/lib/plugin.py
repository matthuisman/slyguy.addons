import math

from slyguy import plugin, gui, userdata, signals, inputstream, settings
from slyguy.constants import ADDON_PATH

from .api import API
from .language import _

api = API()

@signals.on(signals.BEFORE_DISPATCH)
def before_dispatch():
    api.new_session()

@plugin.route('')
def home(**kwargs):
    folder = plugin.Folder()

    folder.add_item(label=_(_.HOME, _bold=True),          path=plugin.url_for(page, page_id='5e795ffe1de1c4001d3d2184'))
    folder.add_item(label=_(_.NEWS, _bold=True),          path=plugin.url_for(page, page_id='news'))
    folder.add_item(label=_(_.SPORT, _bold=True),         path=plugin.url_for(page, page_id='5d54ce0ba6f547001cde19bc'))
    folder.add_item(label=_(_.ENTERTAINMENT, _bold=True), path=plugin.url_for(page, page_id='5d54ce4223eec6001dc2d819'))
    folder.add_item(label=_(_.LIFE, _bold=True),          path=plugin.url_for(page, page_id='5d54ce8023eec6001d24040b'))
    folder.add_item(label=_(_.DOCOS, _bold=True),         path=plugin.url_for(page, page_id='5d54cf8d23eec6001d240410'))
    folder.add_item(label=_(_.CHANNELS, _bold=True),      path=plugin.url_for(page, page_id='channels'))
    folder.add_item(label=_(_.GENRES, _bold=True),        path=plugin.url_for(page, page_id='genres'))
    folder.add_item(label=_(_.SERIES, _bold=True),        path=plugin.url_for(page, page_id='series'))
    folder.add_item(label=_(_.SEARCH, _bold=True),        path=plugin.url_for(search))

    if settings.getBool('bookmarks', True):
        folder.add_item(label=_(_.BOOKMARKS, _bold=True),  path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

def _process_items(rows):
    items = []

    for row in rows:
        attribs = row['attribs']

        if row['typeId'] == 'go-item-video':
            item = plugin.Item(
                label = attribs['title'],
                info  = {
                    'plot': attribs['description'],
                    'duration': int(attribs['video-duration']) / 1000,
                },
                art = {'thumb': attribs['image-background-small']},
                path = plugin.url_for(play, id=attribs['assetId']),
                playable = True,
            )
        elif row['typeId'] == 'go-item-navigation':
            item = plugin.Item(
                label = attribs['title'],
                info  = {
                    'plot': attribs.get('description'),
                },
                art = {'thumb': attribs['image-background-small']},
                path = plugin.url_for(page, page_id=attribs['pageId']),
            )

        items.append(item)

    return items

@plugin.route()
def search(query=None, page=1, **kwargs):
    page = int(page)

    if not query:
        query = gui.input(_.SEARCH, default=userdata.get('search', '')).strip()
        if not query:
            return

        userdata.set('search', query)

    data        = api.search(query=query, page=page)
    rows        = data.get('item', [])
    page_number = data['paginationMetadata']['pageNumber']
    page_size   = data['paginationMetadata']['pageSize']
    total_items = data['paginationMetadata'].get('totalCount', 0)
    total_pages = int(math.ceil(float(total_items) / page_size))

    folder = plugin.Folder(_(_.SEARCH_FOR, query=query, page=page_number, total_pages=total_pages))

    items = _process_items(rows)
    folder.add_items(items)

    if total_pages > page_number:
        folder.add_item(
            label = _(_.NEXT_PAGE, next=page_number+1, total_pages=total_pages, _bold=True),
            path  = plugin.url_for(search, query=query, page=page_number+1),
        )

    return folder

@plugin.route()
def page(page_id, container_id=None, **kwargs):
    data = api.page(page_id)

    folder = plugin.Folder(data['title'])

    if container_id:
        for container in data['containers']:
            if container['id'] == container_id:
                items = _process_items(container['items'])
                folder.add_items(items)

        return folder

    if len(data['containers']) == 1:
        container = data['containers'][0]
        items = _process_items(container['items'])
        folder.add_items(items)
        return folder

    for container in data['containers']:
        if container['templateId'] == 'go-container-hero':
            folder.add_item(
                label = _.FEATURED,
                path  = plugin.url_for(page, page_id=page_id, container_id=container['id']),
            )
        elif 'buttonPage' not in container:
            folder.add_item(
                label = container['title'].title(),
                path  = plugin.url_for(page, page_id=page_id, container_id=container['id']),
            )
        else:
            folder.add_item(
                label = container['title'].title(),
                path  = plugin.url_for(page, page_id=container['buttonPage']),
            )

    return folder

@plugin.route()
def play(id, **kwargs):
    return api.get_brightcove_src(id)