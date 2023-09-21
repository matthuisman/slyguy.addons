import arrow
from slyguy import plugin, gui, userdata, signals, inputstream, settings
from slyguy.monitor import monitor
from slyguy.constants import ROUTE_LIVE_TAG, PLAY_FROM_TYPES, PLAY_FROM_ASK, PLAY_FROM_LIVE, PLAY_FROM_START

from .api import API
from .language import _
from .constants import *

api = API()

@signals.on(signals.BEFORE_DISPATCH)
def before_dispatch():
    api.new_session()
    plugin.logged_in = api.logged_in

@plugin.route('')
def index(**kwargs):
    folder = plugin.Folder(cacheToDisc=False)

    if not api.logged_in:
        folder.add_item(label=_(_.LOGIN, _bold=True), path=plugin.url_for(login), bookmark=False)
    else:
        if not userdata.get('profile_kids', False):
            folder.add_item(label=_(_.FEATURED, _bold=True), path=plugin.url_for(featured, key='sitemap', title=_.FEATURED))
            folder.add_item(label=_(_.TV, _bold=True), path=plugin.url_for(nav, key='tv', title=_.TV))
            folder.add_item(label=_(_.MOVIES, _bold=True), path=plugin.url_for(nav, key='movies', title=_.MOVIES))

            if not settings.getBool('hide_sport', False):
                folder.add_item(label=_(_.SPORT, _bold=True), path=plugin.url_for(nav, key='sport', title=_.SPORT))

        folder.add_item(label=_(_.KIDS, _bold=True), path=plugin.url_for(nav, key='kids', title=_.KIDS))
        folder.add_item(label=_(_.MY_LIST, _bold=True), path=plugin.url_for(my_list))
        folder.add_item(label=_(_.CONTINUE_WATCHING, _bold=True), path=plugin.url_for(continue_watching))
        folder.add_item(label=_(_.SEARCH, _bold=True), path=plugin.url_for(search))

        if settings.getBool('bookmarks', True):
            folder.add_item(label=_(_.BOOKMARKS, _bold=True), path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        if not userdata.get('kid_lockdown', False):
            folder.add_item(label=_.SELECT_PROFILE, path=plugin.url_for(select_profile), art={'thumb': userdata.get('profile_icon')}, info={'plot': userdata.get('profile_name')}, _kiosk=False, bookmark=False)

        folder.add_item(label=_.LOGOUT, path=plugin.url_for(logout), _kiosk=False, bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

@plugin.route()
def login(**kwargs):
    options = [
        [_.DEVICE_CODE, _device_code],
       # [_.EMAIL_PASSWORD, _email_password],
    ]

    index = 0 if len(options) == 1 else gui.context_menu([x[0] for x in options])
    if index == -1 or not options[index][1]():
        return

    _select_profile()
    gui.refresh()

@plugin.route()
def _email_password(**kwargs):
    username = gui.input(_.ASK_EMAIL, default=userdata.get('username', '')).strip()
    if not username:
        return

    userdata.set('username', username)

    password = gui.input(_.ASK_PASSWORD, hide_input=True).strip()
    if not password:
        return

    api.login(username=username, password=password)
    return True

def _device_code():
    code, url = api.device_code()
    timeout = 600

    with gui.progress(_(_.DEVICE_LINK_STEPS, url=ACTIVATE_URL, code=code), heading=_.DEVICE_CODE) as progress:
        for i in range(timeout):
            if progress.iscanceled() or monitor.waitForAbort(1):
                return

            progress.update(int((i / float(timeout)) * 100))

            if i % 6 == 0 and api.device_login(url):
                return True

@plugin.route()
def my_list(**kwargs):
    folder = plugin.Folder(_.MY_LIST)

    data = api.watchlist()

    for row in data['entries']:
        if row['programType'] == 'series':
            folder.add_item(
                label = row['title'],
                art = {'thumb': _art(row['images']), 'fanart': _art(row['images'], 'fanart')},
                path = plugin.url_for(series, series_id=row['programId']),
            )
        elif row['programType'] == 'movie':
            folder.add_item(
                label = row['title'],
                art = {'thumb': _art(row['images']), 'fanart': _art(row['images'], 'fanart')},
                path = plugin.url_for(play, program_id=row['programId']),
                playable = True,
            )

    return folder

@plugin.route()
def continue_watching(**kwargs):
    folder = plugin.Folder(_.CONTINUE_WATCHING)

    data = api.history()

    for row in data['entries']:
        if row['completed'] or not row['position']:
            continue

        if row['programType'] == 'movie':
            folder.add_item(
                label = row['title'],
                resume_from = row['position'],
                art = {'thumb': _art(row['images']), 'fanart': _art(row['images'], 'fanart')},
                path = plugin.url_for(play, program_id=row['programId']),
                playable = True,
            )
        elif row['programType'] == 'episode':
            folder.add_item(
                label = row['title'],
                resume_from = row['position'],
                art = {'thumb': _art(row['images']), 'fanart': _art(row['images'], 'fanart')},
                info = {'tvshowtitle': row['seriesTitle'], 'mediatype': 'episode', 'season': row['tvSeasonNumber'], 'episode': row['tvSeasonEpisodeNumber']},
                context = ((_(_.GOTO_SERIES, series=row['seriesTitle']), 'Container.Update({})'.format(plugin.url_for(series, series_id=row['seriesId']))),),
                path = plugin.url_for(play, program_id=row['programId']),
                playable = True,
            )

    return folder

@plugin.route()
@plugin.login_required()
def select_profile(**kwargs):
    if userdata.get('kid_lockdown', False):
        return

    _select_profile()
    gui.refresh()

def _select_profile():
    profiles = api.profiles()

    options = []
    values = []
    default = -1
    for index, profile in enumerate(profiles):
        values.append(profile)
        options.append(plugin.Item(label=profile['name'], art={'thumb': profile['iconImage']['url']}))

        if profile['id'] == userdata.get('profile_id'):
            default = index

    index = gui.select(_.SELECT_PROFILE, options=options, preselect=default, useDetails=True)
    if index < 0:
        return

    _set_profile(values[index])

def _set_profile(profile, notify=True):
    api.set_profile(profile['id'])

    if settings.getBool('kid_lockdown', False) and profile['isKidsProfile']:
        userdata.set('kid_lockdown', True)

    if notify:
        gui.notification(_.PROFILE_ACTIVATED, heading=userdata.get('profile_name'), icon=userdata.get('profile_icon'))

@plugin.route()
def nav(key, title, **kwargs):
    folder = plugin.Folder(title)

    rows = api.nav_items(key)
    if not rows:
        return folder

    folder.add_item(
        label = _.FEATURED,
        path = plugin.url_for(featured, key=key, title=title),
    )

    for row in rows:
        folder.add_item(
            label = row['title'],
            #art = {'thumb': row['image']},
            path = plugin.url_for(parse, url=row['url'], title=row['title']),
        )

    return folder

@plugin.route()
@plugin.pagination()
def parse(url, title=None, page=1, **kwargs):
    if not url.lower().startswith('http'):
        data = api.page(url, page=page)
    else:
        data = api.url(url, page=page)

    folder = plugin.Folder(title or data.get('title'))

    if data.get('type') == 'section':
        for row in data['entries']:
            if row['type'] != 'hero' and not row.get('hideTitle', False):
                folder.add_item(
                    label = row['title'],
                    #art = {'thumb': row['thumbnail']},
                    path = plugin.url_for(parse, url=row['url'], title=row['title']),
                )

        return folder

    if data.get('type') == 'single_list':
        data = api.url(data['entries'][0]['url'])

    items = _process_entries(data['entries'])
    folder.add_items(items)

    return folder, data.get('next')

@plugin.route()
def featured(key, title, **kwargs):
    folder = plugin.Folder(title)

    data = api.page(key)

    for row in data['entries']:
        if row['type'] in ('posters', 'landscapes') and not row.get('hideTitle', False):
            folder.add_item(
                label = row['title'],
                #art = {'thumb': row.get('thumbnail')},
                path = plugin.url_for(parse, url=row['url'], title=row['title']),
            )

    return folder

@plugin.route()
@plugin.search()
def search(query, page, **kwargs):
    data = api.search(query, page=page, limit=50)
    return _process_entries(data['entries']), False

def _art(images, type='thumb'):
    if type == 'fanart':
        keys = ['Banner-L0', 'Banner-L1', 'Banner-L2']
    elif type == 'episode':
        keys = ['Cast in Character', 'Scene Still', 'Poster Art', 'Box Art']
    else:
        keys = ['Landscape', 'Poster Art', 'Box Art', 'Scene Still', 'Cast in Character']

    for key in keys:
        if key in images:
            return images[key]['url']

    return None

def _process_entries(entries):
    items = []

    now = arrow.now()
    play_type = settings.getEnum('live_play_type', PLAY_FROM_TYPES, default=PLAY_FROM_ASK)

    for row in entries:
        if row.get('type') in ('posters', 'landscapes'):
            if row.get('hideTitle'):
                row['title'] = row['title'].replace('More In:', '').strip()

            items.append(plugin.Item(
                label = row['title'],
                #art = {'thumb': row.get('thumbnail')},
                path = plugin.url_for(parse, url=row['url'], title=row['title']),
            ))
        elif row.get('type') == 'link':
            items.append(plugin.Item(
                label = row['title'],
                art = {'thumb': _art(row['images']), 'fanart': _art(row['images'], 'fanart')},
                path = plugin.url_for(parse, url=row['path'], title=row['title']),
            ))
        elif row.get('programType') == 'series':
            items.append(plugin.Item(
                label = row['title'],
                art = {'thumb': _art(row['images']), 'fanart': _art(row['images'], 'fanart')},
                info = {
                    'plot': row.get('description'),
                    'year': row.get('releaseYear'),
                    'tvshowtitle': row['title'],
                    'mediatype': 'tvshow',
                },
                path = plugin.url_for(series, series_id=row['id']),
            ))


        elif row.get('liveStartDate'):
            is_live = False
            start_date = arrow.get(int(row['liveStartDate'])/1000)

            item = plugin.Item(
                info = {
                    'duration': row['runtime'],
                    'mediatype': 'video',
                },
                art = {'thumb': _art(row['images']), 'fanart': _art(row['images'], 'fanart')},
                playable = True,
                path = _get_play_path(program_id=row['id']),
            )

            if row.get('liveEndDate'):
                end_date = arrow.get(int(row['liveEndDate']/1000))
                if not item.info['duration']:
                    item.info['duration'] = (end_date-start_date).total_seconds()
            else:
                end_date = now.shift(hours=2)

            item.label = row['title']
            item.info['plot'] = u'[B]{}[/B]\n\n{}'.format(start_date.to('local').format('MMM Do h:mm A'), row.get('description'))
            if now < start_date:
                item.label += u' [B][{}][/B]'.format(start_date.humanize())
            elif now > start_date and now < end_date:
                is_live = True
                item.label += u' [B][LIVE][/B]'

            if 'episode' in row:
                program_id = row['episode']['id']
                if row['episode'].get('bonusFeature'):
                    item.info['duration'] = None
            else:
                program_id = row['id']

            item.path = _get_play_path(program_id=program_id, play_type=play_type, _is_live=is_live)

            if is_live:
                item.context.append((_.PLAY_FROM_LIVE, "PlayMedia({})".format(
                    _get_play_path(program_id=row['id'], play_type=PLAY_FROM_LIVE, _is_live=is_live)
                )))

                item.context.append((_.PLAY_FROM_START, "PlayMedia({})".format(
                    _get_play_path(program_id=row['id'], play_type=PLAY_FROM_START, _is_live=is_live)
                )))

            items.append(item)

        elif row.get('programType') == 'movie':
            item = plugin.Item(
                label = row['title'],
                info = {
                    'plot': row.get('description'),
                    'year': row.get('releaseYear'),
                    'duration': row.get('runtime'),
                    'mediatype': 'movie',
                },
                art = {'thumb': _art(row['images']), 'fanart': _art(row['images'], 'fanart')},
                playable = True,
                path = _get_play_path(program_id=row['id']),
            )
            items.append(item)

    return items

@plugin.route()
def series(series_id, **kwargs):
    data = api.program(series_id)

    fanart = _art(data['images'], 'fanart')
    folder = plugin.Folder(data['title'], fanart=fanart)

    for row in sorted(data['seasons'], key=lambda x: x['seasonNumber']):
        if row.get('bonusFeature'):
            row['title'] = _.TRAILERS_EXTRAS

        folder.add_item(
            label = row['title'],
            info = {
                'tvshowtitle': data['title'],
                'mediatype': 'season',
            },
            art = {'thumb': _art(data['images'])},
            path = plugin.url_for(episodes, url=row['url'], show_title=data['title'], fanart=fanart),
        )

    return folder

def _get_play_path(**kwargs):
    profile_id = userdata.get('profile_id', '')
    if profile_id:
        kwargs['profile_id'] = profile_id

    return plugin.url_for(play, **kwargs)

@plugin.route()
def episodes(url, show_title, fanart, **kwargs):
    data = api.url(url)

    extras = data.get('bonusFeature', False)

    folder = plugin.Folder(show_title, fanart=fanart)
    for row in data['entries']:
        if row['programType'] == 'episode':
            if not row['images']:
                try: row = api.url(row['url'])
                except: pass

            folder.add_item(
                label = row['title'],
                info = {
                    'plot': row.get('description'),
                    'year': row.get('releaseYear'),
                    'duration': row.get('runtime'),
                    'season': row['tvSeasonNumber'] if not extras else None,
                    'episode': row['tvSeasonEpisodeNumber'] if not extras else None,
                    'mediatype': 'episode',
                    'tvshowtitle': show_title,
                },
                art = {'thumb': _art(row['images'], type='episode')},
                playable = True,
                path = _get_play_path(program_id=row['id']),
            )

    return folder

@plugin.route()
def play(program_id, play_type=PLAY_FROM_LIVE, **kwargs):
    play_type = int(play_type)
    is_live = ROUTE_LIVE_TAG in kwargs

    resume_from = None
    if is_live:
        if play_type == PLAY_FROM_START:
            resume_from = 1
        elif play_type == PLAY_FROM_ASK:
            resume_from = plugin.live_or_start()
            if resume_from == -1:
                return

    program_data, play_data = api.play(program_id)

    headers = {
        'dt-custom-data': play_data['drm']['customData'],
    }
    headers.update(HEADERS)

    item = plugin.Item(
        path = play_data['videoUrl'],
        headers = headers,
        inputstream = inputstream.Widevine(
            license_key = play_data['drm']['licenseServerUrl'],
            license_data = play_data['drm']['init_data'],
            response = 'JBlicense',
        ),
        resume_from = resume_from,
    )

    for row in play_data.get('captions', []):
        item.subtitles.append([row['url'], row['language']])

    # for chapter in program_data.get('chapters', []):
    #     if chapter['name'] == 'Intro':
    #         item.resume_from = str(chapter['end']/1000 - 1)
    #     elif chapter['name'] == 'Credits':
    #         item.play_next = {'time': chapter['start']/1000}

    return item

@plugin.route()
def logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO):
        return

    api.logout()
    userdata.delete('kid_lockdown')
    gui.refresh()
