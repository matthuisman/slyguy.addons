import arrow
from slyguy import plugin, gui, settings, userdata, signals, inputstream
from slyguy.constants import ROUTE_LIVE_TAG

from .api import API
from .language import _
from .constants import *

api = API()

@signals.on(signals.BEFORE_DISPATCH)
def before_dispatch():
    api.new_session()
    plugin.logged_in = api.logged_in

@plugin.route('')
def home(**kwargs):
    folder = plugin.Folder(cacheToDisc=False)

    if not api.logged_in:
        folder.add_item(label=_(_.LOGIN, _bold=True), path=plugin.url_for(login), bookmark=False)
    else:
        folder.add_item(label=_(_.FEATURED, _bold=True), path=plugin.url_for(featured))
        folder.add_item(label=_(_.VIDEOS, _bold=True), path=plugin.url_for(videos))
        folder.add_item(label=_(_.CREATORS, _bold=True), path=plugin.url_for(creators))
        folder.add_item(label=_(_.PODCASTS, _bold=True), path=plugin.url_for(podcast_creators))
        folder.add_item(label=_(_.MY_VIDEOS, _bold=True), path=plugin.url_for(my_videos))
        folder.add_item(label=_(_.MY_CREATORS, _bold=True), path=plugin.url_for(my_creators))
        folder.add_item(label=_(_.SEARCH, _bold=True), path=plugin.url_for(search))

        if settings.getBool('bookmarks', True):
            folder.add_item(label=_(_.BOOKMARKS, _bold=True),  path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        folder.add_item(label=_.LOGOUT, path=plugin.url_for(logout), _kiosk=False, bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

@plugin.route()
def featured(index=None, **kwargs):
    folder = plugin.Folder(_.FEATURED)
    index = int(index) if index else None

    for count, row in enumerate(api.featured()):
        if row['type'] == 'heroes':
            continue

        if index is None:
            folder.add_item(
                label = row['title'],
                path = plugin.url_for(featured, index=count),
            )

        elif count == index:
            folder = plugin.Folder(row['title'])

            if row['type'] in ('latest_videos',):
                items = _parse_videos(row['items'])
                folder.add_items(items)

            elif row['type'] in ('podcast_channels',):
                items = _parse_podcast_creators(row['items'])
                folder.add_items(items)

            elif row['type'] in ('featured_creators','video_channels'):
                items = _parse_creators(row['items'])
                folder.add_items(items)

    return folder

@plugin.route()
@plugin.pagination()
def videos(category=None, title=None, page=1, **kwargs):
    page = int(page)
    page_size = settings.getInt('page_size', 50)

    if category is None:
        folder = plugin.Folder(_.VIDEOS)

        folder.add_item(
            label = _.EVERYTHING,
            path = plugin.url_for(videos, category='', title=_.EVERYTHING),
        )

        for row in api.categories():
            folder.add_item(
                label = row['title'],
                art = {'thumb': row['assets']['avatar-big-light']},
                path = plugin.url_for(videos, category=row['slug'], title=row['title']),
            )

        return folder, False

    folder = plugin.Folder(title)
    data = api.videos(category=category, page=page, page_size=page_size)
    items = _parse_videos(data['results'])
    folder.add_items(items)
    return folder, data['next']

@plugin.route()
@plugin.pagination()
def podcast_creators(category=None, title=None, page=1, **kwargs):
    page = int(page)
    page_size = settings.getInt('page_size', 50)

    if category is None:
        folder = plugin.Folder(_.PODCASTS)

        folder.add_item(
            label = _.EVERYTHING,
            path = plugin.url_for(podcast_creators, category='', title=_.EVERYTHING),
        )

        for row in api.podcast_categories():
            folder.add_item(
                label = row['title'],
                art = {'thumb': row['assets']['avatar-big-light']},
                path = plugin.url_for(podcast_creators, category=row['slug'], title=row['title']),
            )

        return folder, False

    folder = plugin.Folder(title)
    data = api.podcast_creators(category=category, page=page, page_size=page_size)
    items = _parse_podcast_creators(data['results'])
    folder.add_items(items)
    return folder, data['next']

@plugin.route()
@plugin.pagination()
def creators(category=None, title=None, page=1, **kwargs):
    page = int(page)
    page_size = settings.getInt('page_size', 50)

    if category is None:
        folder = plugin.Folder(_.CREATORS)

        folder.add_item(
            label = _.EVERYTHING,
            path = plugin.url_for(creators, category='', title=_.EVERYTHING),
        )

        for row in api.categories():
            folder.add_item(
                label = row['title'],
                art = {'thumb': row['assets']['avatar-big-light']},
                path = plugin.url_for(creators, category=row['slug'], title=row['title']),
            )

        return folder, False

    folder = plugin.Folder(title)
    data = api.creators(category=category, page=page, page_size=page_size)
    items = _parse_creators(data['results'])
    folder.add_items(items)
    return folder, data['next']

def _parse_creators(rows, following=False):
    items = []

    for row in rows:
        item = plugin.Item(
            label = row['title'],
            info = {'plot': row['description']},
            art = {'thumb': row['assets']['avatar']['512']['original'], 'fanart': row['assets']['banner']['1920']['original']},
            path = plugin.url_for(creator_videos, slug=row['slug']),
        )

        if following:
            item.context.append((_(_.UNFOLLOW_CREATOR, creator=row['title']), 'RunPlugin({})'.format(plugin.url_for(unfollow_creator, slug=row['slug'], title=row['title'], icon=row['assets']['avatar']['512']['original']))))
        else:
            item.context.append((_(_.FOLLOW_CREATOR, creator=row['title']), 'RunPlugin({})'.format(plugin.url_for(follow_creator, slug=row['slug'], title=row['title'], icon=row['assets']['avatar']['512']['original']))))

        items.append(item)

    return items

def _parse_podcast_creators(rows):
    items = []

    for row in rows:
        item = plugin.Item(
            label = row['title'],
            info = {'plot': _(_.POCAST_CREATOR, creator=row['creator'], description=row['description']).strip()},
            art = {'thumb': row['assets']['regular']},
            path = plugin.url_for(podcasts, slug=row['slug']),
        )

        items.append(item)

    return items

def _parse_videos(rows, creator_page=False, following=False):
    items = []
    for row in rows:
        is_live = False
        published = arrow.get(row['published_at'])

        try:
            thumb = row['assets']['thumbnail']['720']['original']
        except:
            thumb = row['assets']['thumbnail']['720']

        item = plugin.Item(
            label = row['title'],
            info = {
                'duration': row['duration'],
                'plot': _(_.VIDE_PLOT, creator=row['channel_title'], published=published.humanize(), description=row['short_description'] or row['description']).strip(),
                #'season': row.get('season'),
                #'episode': row.get('episode'),
                'tvshowtitle': row['channel_title'],
                'aired': str(published),
                'mediatype': 'episode',
            },
            art = {'thumb': thumb, 'fanart': row['assets']['channel_avatar']['512']['original']},
            path = plugin.url_for(play, slug=row['slug'], _is_live=is_live),
            playable = True,
        )

        if following:
            item.context.append((_(_.UNFOLLOW_CREATOR, creator=row['channel_title']), 'RunPlugin({})'.format(plugin.url_for(unfollow_creator, slug=row['channel_slug'], title=row['channel_title'], icon=row['assets']['channel_avatar']['512']['original']))))
        else:
            item.context.append((_(_.FOLLOW_CREATOR, creator=row['channel_title']), 'RunPlugin({})'.format(plugin.url_for(follow_creator, slug=row['channel_slug'], title=row['channel_title'], icon=row['assets']['channel_avatar']['512']['original']))))

        if not creator_page:
            item.context.append((_(_.CREATOR_CHANNEL, creator=row['channel_title']), 'Container.Update({})'.format(plugin.url_for(creator_videos, slug=row['channel_slug'], title=row['channel_title'], icon=row['assets']['channel_avatar']['512']['original']))))

        items.append(item)

    return items

def _parse_podcasts(rows):
    items = []
    for row in rows:
        is_live = False
        published = arrow.get(row['published_at'])

        item = plugin.Item(
            label = row['title'],
            info = {
                'duration': row['duration'],
                'plot': row['description'].strip(),
                'aired': str(published),
            },
            art = {'thumb': row['assets']['regular']},
            path = plugin.url_for(play_podcast, channel=row['channel_slug'], episode=row['slug'], _is_live=is_live),
            playable = True,
        )

        items.append(item)

    return items

@plugin.route()
@plugin.pagination()
def my_videos(page=1, **kwargs):
    page = int(page)
    page_size = settings.getInt('page_size', 50)
    data = api.my_videos(page=page, page_size=page_size)

    folder = plugin.Folder(_.MY_VIDEOS)
    items = _parse_videos(data['results'], following=True)
    folder.add_items(items)
    return folder, data['next']

@plugin.route()
@plugin.pagination()
def my_creators(page=1, **kwargs):
    page = int(page)
    page_size = settings.getInt('page_size', 50)
    data = api.my_creators(page=page, page_size=page_size)

    folder = plugin.Folder(_.MY_CREATORS)
    items = _parse_creators(data['results'], following=True)
    folder.add_items(items)
    return folder, data['next']

@plugin.route()
@plugin.pagination()
def podcasts(slug, page=1, **kwargs):
    page = int(page)
    page_size = settings.getInt('page_size', 50)
    data = api.podcasts(slug, page=page, page_size=page_size)

    folder = plugin.Folder(data['details']['title'])
    items = _parse_podcasts(data['episodes']['results'])
    folder.add_items(items)
    return folder, data['episodes']['next']

@plugin.route()
@plugin.pagination()
def creator_videos(slug, page=1, **kwargs):
    page = int(page)
    page_size = settings.getInt('page_size', 50)
    data = api.creator(slug, page=page, page_size=page_size)

    folder = plugin.Folder(data['details']['title'], fanart=data['details']['assets']['avatar']['512']['original'])
    items = _parse_videos(data['episodes']['results'], creator_page=True)
    folder.add_items(items)
    return folder, data['episodes']['next']

@plugin.route()
def follow_creator(slug, title, icon, **kwargs):
    api.follow_creator(slug)
    gui.notification(_(_.FOLLOWED_CREATOR, creator=title), icon=icon)

@plugin.route()
def unfollow_creator(slug, title, icon, **kwargs):
    api.unfollow_creator(slug)
    gui.notification(_(_.UNFOLLOWED_CREATOR, creator=title), icon=icon)
    gui.refresh()

@plugin.route()
@plugin.search()
def search(query, page, **kwargs):
    page_size = settings.getInt('page_size', 50)

    items = []
    if page == 1:
        data = api.search_creators(query=query)
        items = _parse_creators(data['results'])

        data = api.search_podcasts(query=query)
        items.extend(_parse_podcast_creators(data['results']))

    data = api.search_videos(query=query, page=page, page_size=page_size)
    items.extend(_parse_videos(data['results']))

    return items, data['next']

@plugin.route()
def login(**kwargs):
    username = gui.input(_.ASK_USERNAME, default=userdata.get('username', '')).strip()
    if not username:
        return

    userdata.set('username', username)

    password = gui.input(_.ASK_PASSWORD, hide_input=True).strip()
    if not password:
        return

    api.login(username, password)
    gui.refresh()

@plugin.route()
@plugin.login_required()
def play(slug, **kwargs):
    data = api.play(slug)

    item = plugin.Item(
        path = data['manifest'],
        inputstream = inputstream.HLS(live=ROUTE_LIVE_TAG in kwargs, force=True),
    )
    ## subs seem to be included in manifest now
    # for idx, row in enumerate(data.get('subtitles', [])):
    #     item.subtitles.append([row['url'], row['language_code']])
    return item

@plugin.route()
@plugin.login_required()
def play_podcast(channel, episode, **kwargs):
    data = api.play_podcast(channel, episode)

    item = plugin.Item(
        label = data['title'],
        info = {
            'plot': data['description'],
        },
        art = {'thumb': data['assets']['regular']},
        path = data['episode_url'],
    )

    return item

@plugin.route()
def logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO):
        return

    api.logout()
    gui.refresh()
