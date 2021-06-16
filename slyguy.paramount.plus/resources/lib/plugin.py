import time
import codecs
from xml.sax.saxutils import escape

import arrow
from kodi_six import xbmc

from slyguy import plugin, gui, settings, userdata, signals, inputstream
from slyguy.exceptions import PluginError

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
        folder.add_item(label=_(_.LOGIN, _bold=True), path=plugin.url_for(login))
    else:
        # folder.add_item(label=_(_.FEATURED, _bold=True), path=plugin.url_for(featured))
        folder.add_item(label=_(_.SHOWS, _bold=True), path=plugin.url_for(shows))
        # folder.add_item(label=_(_.MOVIES, _bold=True), path=plugin.url_for(movies))
        folder.add_item(label=_(_.LIVE_TV, _bold=True), path=plugin.url_for(live_tv))
        # folder.add_item(label=_(_.BRANDS, _bold=True), path=plugin.url_for(brands))
        # folder.add_item(label=_(_.NEWS, _bold=True), path=plugin.url_for(news))
        folder.add_item(label=_(_.SEARCH, _bold=True), path=plugin.url_for(search))

        if settings.getBool('bookmarks', True):
            folder.add_item(label=_(_.BOOKMARKS, _bold=True),  path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        folder.add_item(label=_.SELECT_PROFILE, path=plugin.url_for(select_profile), art={'thumb': _image(userdata.get('profile_img'))}, info={'plot': userdata.get('profile_name')}, _kiosk=False, bookmark=False)
        folder.add_item(label=_.LOGOUT, path=plugin.url_for(logout), _kiosk=False, bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

@plugin.route()
def search(query=None, **kwargs):
    if not query:
        query = gui.input(_.SEARCH, default=userdata.get('search', '')).strip()
        if not query:
            return

        userdata.set('search', query)

    folder = plugin.Folder(_(_.SEARCH_FOR, query=query))

    for row in api.search(query):
        if row['term_type'] == 'show':
            folder.add_item(
                label = row['title'],
                info = {
                    'mediatype': 'tvshow',
                },
                art = {'thumb': _image(row['showAssets']['filepath_show_browse_poster']), 'fanart': _image(row['showAssets']['filepath_brand_hero'], 'w1920-q80')},
                path = plugin.url_for(show, show_id=row['show_id']),
            )

    return folder

@plugin.route()
def shows(group_id=None, **kwargs):
    if group_id:
        group = api.show_group(group_id)

        folder = plugin.Folder(group['title'])
        items = _process_shows(group['showGroupItems'])
        folder.add_items(items)

        return folder
    else:
        folder = plugin.Folder(_.SHOWS)

        for row in api.show_groups():
            folder.add_item(
                label = row['title'],
                path = plugin.url_for(shows, group_id=row['id']),
            )

        return folder

def _process_shows(rows):
    items = []

    for row in rows:
        plot = _(_.EPISODE_COUNT, count=row['episodeVideoCount']['totalEpisodes'])
        if row['episodeVideoCount']['totalClips']:
            plot += '\n'+ _(_.CLIPS_COUNT, count=row['episodeVideoCount']['totalClips'])

        item = plugin.Item(
            label = row['title'],
            info = {
                'genre': row['category'],
                'mediatype': 'tvshow',
                'plot': plot,
            },
            art = {'thumb': _image(row['showAssets']['filepath_show_browse_poster']), 'fanart': _image(row['showAssets']['filepath_brand_hero'], 'w1920-q80')},
            path = plugin.url_for(show, show_id=row['showId']),
        )

        items.append(item)

    return items

@plugin.route()
def show(show_id, **kwargs):
    show = api.show(show_id)

    folder = plugin.Folder(show['show']['results'][0]['title'], thumb=_image(show['showAssets']['filepath_show_browse_poster']), fanart=_image(show['showAssets']['filepath_brand_hero'], 'w1920-q80'))

    plot = show['show']['results'][0]['about'] + '\n\n'

    clip_count = 0
    for row in sorted(api.seasons(show_id), key=lambda x: int(x['seasonNum'])):
        clip_count += row['clipsCount']
        if not row['totalCount']:
            continue

        folder.add_item(
            label = _(_.SEASON, season=row['seasonNum']),
            info = {
                'plot': plot + _(_.EPISODE_COUNT, count=row['totalCount']),
                'mediatype': 'season',
                'tvshowtitle': show['show']['results'][0]['title'],
            },
            path = plugin.url_for(season, show_id=show_id, season=row['seasonNum']),
        )

    # if clip_count:
    #     folder.add_item(
    #         label = _.CLIPS,
    #         info = {
    #             'plot': plot + _(_.CLIPS_COUNT, count=clip_count),
    #         }
    #     )

    return folder

@plugin.route()
def season(show_id, season, **kwargs):
    show = api.show(show_id)

    folder = plugin.Folder(show['show']['results'][0]['title'], fanart=_image(show['showAssets']['filepath_brand_hero'], 'w1920-q80'))

    for row in sorted(api.episodes(show_id, season), key=lambda x: int(x['episodeNum'])):
        folder.add_item(
            label = row['label'].strip() or row['title'].strip(),
            info = {
                'aired': row['_airDateISO'],
                'dateadded': row['_pubDateISO'],
                'plot': row['description'],
                'season': row['seasonNum'],
                'episode': row['episodeNum'],
                'duration': row['duration'],
                'genre': row['topLevelCategory'],
                'mediatype': 'episode',
                'tvshowtitle': show['show']['results'][0]['title'],
            },
            art = {'thumb': _thumbnail(row['thumbnail'])},
            path = plugin.url_for(play, video_id=row['contentId']),
            playable = True,
        )

    return folder

@plugin.route()
def live_tv(**kwargs):
    folder = plugin.Folder(_.LIVE_TV)

    now = arrow.utcnow()

    for row in api.live_channels():
        if not row['currentListing'] or (not row['dma'] and not row['currentListing'][-1]['contentCANVideo'].get('liveStreamingUrl')):
            continue

        plot = u''
        for listing in row['currentListing']:
            start = arrow.get(listing['startTimestamp'])
            end = arrow.get(listing['endTimestamp'])
            if (now > start and now < end) or start > now:
                plot += u'[{} - {}]\n{}\n'.format(start.to('local').format('h:mma'), end.to('local').format('h:mma'), listing['title'])

        folder.add_item(
            label = row['channelName'],
            info = {
                'plot': plot.strip('\n'),
            },
            art = {'thumb': _image(row['filePathLogoSelected'])},
            path = plugin.url_for(play_channel, slug=row['slug'], _is_live=True),
            playable = True,
        )

    return folder

@plugin.route()
def login(**kwargs):
    if gui.yes_no(_.LOGIN_WITH, yeslabel=_.DEVICE_LINK, nolabel=_.EMAIL_PASSWORD):
        result = _device_link()
    else:
        result = _email_password()

    if not result:
        return

    _select_profile()
    gui.refresh()

def _email_password():
    username = gui.input(_.ASK_USERNAME, default=userdata.get('username', '')).strip()
    if not username:
        return

    userdata.set('username', username)

    password = gui.input(_.ASK_PASSWORD, hide_input=True).strip()
    if not password:
        return

    api.login(username=username, password=password)

    return True

def _device_link():
    start = time.time()
    data = api.device_code()
    monitor = xbmc.Monitor()

    poll_time = int(data['retryInterval']/1000)
    max_time = int(data['retryDuration']/1000)
    device_token = data['deviceToken']
    code = data['activationCode']

    with gui.progress(_(_.DEVICE_LINK_STEPS, url=DEVICE_LINK_URL, code=code), heading=_.DEVICE_LINK) as progress:
        while (time.time() - start) < max_time:
            for i in range(poll_time):
                if progress.iscanceled() or monitor.waitForAbort(1):
                    return

                progress.update(int(((time.time() - start) / max_time) * 100))

            result = api.device_login(code, device_token)
            if result:
                return True

            elif result == -1:
                return False

@plugin.route()
def select_profile(**kwargs):
    _select_profile()
    gui.refresh()

def _image(image_name, dimensions='w400'):
    return IMG_URL.format(dimensions=dimensions, file=image_name[6:]) if image_name else None

def _thumbnail(image_url, dimensions='h243'):
    return image_url.replace('https://thumbnails.cbsig.net/', 'https://thumbnails.cbsig.net/_x/{}/'.format(dimensions))

def _select_profile():
    profiles = api.user()['accountProfiles']

    values = []
    options = []
    default = -1
    for index, profile in enumerate(profiles):
        values.append(profile['id'])
        options.append(plugin.Item(label=profile['name'], art={'thumb': _image(profile['profilePicPath'])}))
        if profile['id'] == userdata.get('profile_id'):
            default = index

    index = gui.select(_.SELECT_PROFILE, options=options, preselect=default, useDetails=True)
    if index < 0:
        return

    api.set_profile(values[index])
    gui.notification(_.PROFILE_ACTIVATED, heading=userdata.get('profile_name'), icon=_image(userdata.get('profile_img')))

@plugin.route()
@plugin.login_required()
def play(video_id, **kwargs):
    url, license_url, token = api.play(video_id)

    headers = {
        'authorization': 'Bearer {}'.format(token),
    }

    return plugin.Item(
        path = url,
        headers = headers,
        inputstream = inputstream.Widevine(
            license_key = license_url,
        ),
    )

@plugin.route()
@plugin.login_required()
def play_channel(slug, **kwargs):
    channels = api.live_channels()
    
    for row in channels:
        if row['slug'] == slug:
            if row['dma']:
                play_path = row['dma']['playback_url']
            elif row['currentListing']:
                play_path = row['currentListing'][0]['contentCANVideo']['liveStreamingUrl']
            else:
                raise Exception('No url found for this channel')

            return plugin.Item(
                label = row['channelName'],
                info = {
                    'plot': row['description'],
                },
                art = {'thumb': _image(row['filePathLogoSelected'])},
                path = play_path,
                inputstream = inputstream.HLS(live=True),
            )

    raise Exception('Unable to find that channel')

@plugin.route()
def logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO):
        return

    api.logout()
    gui.refresh()

@plugin.route()
@plugin.merge()
def playlist(output, **kwargs):
    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'#EXTM3U\n')

        for row in api.live_channels():
            if not row['currentListing'] or len(row['currentListing']) > 1:
                continue

            f.write(u'#EXTINF:-1 tvg-id="{id}" tvg-name="{name}" tvg-logo="{logo}",{name}\n{path}\n'.format(
                id=row['slug'], name=row['channelName'], logo=_image(row['filePathLogoSelected']), path=plugin.url_for(play_channel, slug=row['slug'], _is_live=True)))

@plugin.route()
@plugin.merge()
def epg(output, **kwargs):
    channels = api.live_channels()
    now = arrow.now()
    until = now.shift(days=settings.getInt('epg_days', 3))

    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'<?xml version="1.0" encoding="utf-8" ?><tv>')

        for channel in api.live_channels():
            if not channel['currentListing'] or (not channel['dma'] and not channel['currentListing'][-1]['contentCANVideo'].get('liveStreamingUrl')):
                continue

            f.write(u'<channel id="{id}"></channel>'.format(id=channel['slug']))

            page = 1
            stop = now
            while stop < until:
                rows = api.epg(channel['slug'], rows=100, page=page)
                page += 1
                if not rows:
                    break

                for row in rows:
                    start = arrow.get(row['startTimestamp'])
                    stop = arrow.get(row['endTimestamp'])

                    icon = u'<icon src="{}"/>'.format(_image(row['filePathThumb'])) if row['filePathThumb'] else ''
                    desc = u'<desc>{}</desc>'.format(escape(row['description'])) if row['description'] else ''

                    f.write(u'<programme channel="{id}" start="{start}" stop="{stop}"><title>{title}</title>{desc}{icon}</programme>'.format(
                        id=channel['slug'], start=start.format('YYYYMMDDHHmmss Z'), stop=stop.format('YYYYMMDDHHmmss Z'), title=escape(row['title']), desc=desc, icon=icon,
                    ))

        f.write(u'</tv>')
