import json
import operator
from difflib import SequenceMatcher

from kodi_six import xbmc, xbmcgui

from slyguy import settings
from slyguy.log import log
from slyguy.constants import ADDON, ADDON_VERSION
from slyguy.mem_cache import cached

from .defs import *


LANGUAGE = ADDON.getLocalizedString


class GUI(xbmcgui.WindowXML):
    def __init__(self, *args, **kwargs):
        self.params = kwargs['params']
        self.searchstring = kwargs['searchstring']

    def onInit(self):
        self.clearList()
        self._hide_controls()
        log.debug('script version %s started' % ADDON_VERSION)
        self.nextsearch = False
        self.navback = False
        self.history = {}
        self.menuposition = 0
        self.searchstring = self._clean_string(self.searchstring).strip()
        if self.searchstring == '':
            self._close()
        else:
            self.window_id = xbmcgui.getCurrentWindowId()
            xbmcgui.Window(self.window_id).setProperty('GlobalSearch.SearchString', self.searchstring)
            if not self.nextsearch:
                if self.params == {}:
                    self._load_settings()
                else:
                    self._parse_argv()
                self._get_preferences()
                self._load_favourites()
            self._reset_variables()
            self._init_items()
            self.menu.reset()
            self._set_view()
            self._fetch_items()

    def _hide_controls(self):
        for cid in [SEARCHBUTTON, NORESULTS]:
            self.getControl(cid).setVisible(False)

    def _parse_argv(self):
        for key, value in self.params.items():
            CATEGORIES[key]['enabled'] = self.params[key] == 'true'

    def _load_settings(self):
        for key, value in CATEGORIES.items():
            if key not in ('albumsongs', 'artistalbums', 'tvshowseasons', 'seasonepisodes', 'actormovies', 'directormovies', 'actortvshows'):
                CATEGORIES[key]['enabled'] = settings.getBool(key)

    def _get_preferences(self):
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Settings.GetSettingValue", "params":{"setting":"myvideos.selectaction"}, "id": 1}')
        json_response = json.loads(json_query)
        self.playaction = 1
        if 'result' in json_response and json_response['result'] != None and 'value' in json_response['result']:
            self.playaction = json_response['result']['value']
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Settings.GetSettingValue", "params":{"setting":"musiclibrary.showcompilationartists"}, "id": 1}')
        json_response = json.loads(json_query)
        self.albumartists = "false"
        if 'result' in json_response and json_response['result'] != None and 'value' in json_response['result']:
            if json_response['result']['value'] == "false":
                self.albumartists = "true"

    def _load_favourites(self):
        self.favourites = []
        json_query = xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Favourites.GetFavourites", "params":{"properties":["path", "windowparameter"]}, "id": 1}')
        json_response = json.loads(json_query)
        if 'result' in json_response and json_response['result'] != None and 'favourites' in json_response['result'] and json_response['result']['favourites'] != None:
            for item in json_response['result']['favourites']:
                if 'path' in item:
                    self.favourites.append(item['path'])
                elif 'windowparameter' in item:
                    self.favourites.append(item['windowparameter'])

    def _reset_variables(self):
        self.focusset= 'false'

    def _init_items(self):
        self.Player = MyPlayer()
        self.menu = self.getControl(MENU)
        self.content = {}
        self.oldfocus = 0

    def _set_view(self):
        # no view will be loaded unless we call SetViewMode, might be a bug...
        xbmc.executebuiltin('Container.SetViewMode(0)')
        vid = settings.getInt('view')
        # kodi bug: need to call Container.SetViewMode twice
        xbmc.executebuiltin('Container.SetViewMode(%i)' % vid)

    def _fetch_items(self):
        self.level = 1
        cats = []
        for key, value in sorted(CATEGORIES.items(), key=lambda x: x[1]['order']):
            if CATEGORIES[key]['enabled']:
                self._get_items(CATEGORIES[key], self.searchstring)
                cats.append(CATEGORIES[key])
        self.history[self.level] = {'cats':cats, 'search':self.searchstring}
        self._check_focus()

    @cached(60*5)
    def _cached_json_rpc(self, command):
        return json.loads(xbmc.executeJSONRPC(command))

    def _get_items(self, cat, search):
        if cat['content'] == 'livetv':
            self._fetch_channelgroups(cat)
            return
        if cat['type'] == 'seasonepisodes':
            search = search[0], search[1]
            rule = cat['rule'].format(query0 = search[0], query1 = search[1])
        else:
            rule = cat['rule'].format(query = search)
        self.getControl(SEARCHCATEGORY).setLabel(xbmc.getLocalizedString(cat['label']))
        self.getControl(SEARCHCATEGORY).setVisible(True)

        #TODO: Pagination for faster more responsive results
        json_response = self._cached_json_rpc('{"jsonrpc":"2.0", "method":"%s", "params":{"properties":%s, "sort":{"method":"%s"}, %s}, "id": 1}' % (cat['method'], json.dumps(cat['properties']), cat['sort'], rule))
        listitems = []
        actors = {}
        directors = {}
        if self.level > 1:
            listitem = xbmcgui.ListItem('..', offscreen=True)
            listitem.setArt({'icon':'DefaultFolderBack.png'})
            listitems.append(listitem)
        if 'result' in json_response and(json_response['result'] != None) and cat['content'] in json_response['result']:
            results = json_response['result'][cat['content']]
            if settings.getBool('smart_search', True) and type(search) == str:
                results = sorted(results,
                                 key = lambda x: SequenceMatcher(None,
                                                    search.lower().strip().replace(' ', ''),
                                                    x['label'].lower().strip().replace(' ', '')
                                                ).ratio(),
                                 reverse = True)

            for item in results:
                if cat['type'] == 'actors' or cat['type'] == 'tvactors':
                    for item in item['cast']:
                        if search.lower() in item['name'].lower():
                            name = item['name']
                            if 'thumbnail' in item:
                                thumb = item['thumbnail']
                            else:
                                thumb = cat['icon']
                            val = {}
                            val['thumb'] = thumb
                            if name in actors and 'count' in actors[name]:
                               val['count'] = actors[name]['count'] + 1
                            else:
                               val['count'] = 1
                            actors[name] = val
                elif cat['type'] == 'directors':
                    for item in item['director']:
                        if search.lower() in item.lower():
                            name = item
                            val = {}
                            val['thumb'] = cat['icon']
                            if name in directors and 'count' in directors[name]:
                               val['count'] = directors[name]['count'] + 1
                            else:
                               val['count'] = 1
                            directors[name] = val
                else:
                    listitem = xbmcgui.ListItem(item['label'], offscreen=True)
                    listitem.setArt(self._get_art(item, cat['icon'], cat['media']))
                if cat['streamdetails']:
                    for stream in item['streamdetails']['video']:
                        listitem.addStreamInfo('video', stream)
                    for stream in item['streamdetails']['audio']:
                        listitem.addStreamInfo('audio', stream)
                    for stream in item['streamdetails']['subtitle']:
                        listitem.addStreamInfo('subtitle', stream)
                if cat['type'] != 'actors' and cat['type'] != 'directors' and cat['type'] != 'tvactors':
                    listitem.setProperty('content', cat['content'])
                if cat['content'] == 'tvshows' and cat['type'] != 'tvactors':
                    listitem.setProperty('TotalSeasons', str(item['season']))
                    listitem.setProperty('TotalEpisodes', str(item['episode']))
                    listitem.setProperty('WatchedEpisodes', str(item['watchedepisodes']))
                    listitem.setProperty('UnWatchedEpisodes', str(item['episode'] - item['watchedepisodes']))
                elif cat['content'] == 'seasons':
                    listitem.setProperty('tvshowid', str(item['tvshowid']))
                elif (cat['content'] == 'movies' and cat['type'] != 'actors' and cat['type'] != 'directors') or cat['content'] == 'episodes' or cat['content'] == 'musicvideos':
                    listitem.setProperty('resume', str(int(item['resume']['position'])))
                elif cat['content'] == 'artists' or cat['content'] == 'albums':
                    info, props = self._split_labels(item, cat['properties'], cat['content'][0:-1] + '_')
                    for key, value in props.items():
                        listitem.setProperty(key, value)
                if cat['content'] == 'albums':
                    listitem.setProperty('artistid', str(item['artistid'][0]))
                if cat['content'] == 'songs':
                    listitem.setProperty('artistid', str(item['artistid'][0]))
                    listitem.setProperty('albumid', str(item['albumid']))
                if (cat['content'] == 'movies' and cat['type'] != 'actors' and cat['type'] != 'directors') or (cat['content'] == 'tvshows' and cat['type'] != 'tvactors') or cat['content'] == 'episodes' or cat['content'] == 'musicvideos' or cat['content'] == 'songs':
                    listitem.setPath(item['file'])
                if cat['media']:
                    listitem.setInfo(cat['media'], self._get_info(item, cat['content'][0:-1]))
                    listitem.setProperty('media', cat['media'])
                if cat['content'] == 'tvshows' and cat['type'] != 'tvactors':
                    listitem.setIsFolder(True)
                if cat['type'] != 'actors' and cat['type'] != 'directors' and cat['type'] != 'tvactors':
                    listitems.append(listitem)
            if actors:
                for name, val in sorted(actors.items()):
                    listitem = xbmcgui.ListItem(name, str(val['count']), offscreen=True)
                    listitem.setArt({'icon':cat['icon'], 'thumb':val['thumb']})
                    listitem.setProperty('content', cat['type'])
                    listitems.append(listitem)
            if directors:
                for name, val in sorted(directors.items()):
                    listitem = xbmcgui.ListItem(name, str(val['count']), offscreen=True)
                    listitem.setArt({'icon':cat['icon'], 'thumb':val['thumb']})
                    listitem.setProperty('content', cat['type'])
                    listitems.append(listitem)
        if len(listitems) > 0:
            if self.level > 1:
                numitems = str(len(listitems) - 1)
            else:
                numitems = str(len(listitems))
            if cat['type'] != 'actors' and cat['type'] != 'tvactors':
                menuitem = xbmcgui.ListItem(xbmc.getLocalizedString(cat['label']), numitems, offscreen=True)
            else:
                menuitem = xbmcgui.ListItem(LANGUAGE(cat['label']), numitems, offscreen=True)
            menuitem.setArt({'icon':cat['menuthumb']})
            menuitem.setProperty('type', cat['type'])
            if cat['type'] != 'actors' and cat['type'] != 'directors' and cat['type'] != 'tvactors':
                menuitem.setProperty('content', cat['content'])
            elif cat['type'] == 'actors' or cat['type'] == 'tvactors':
                menuitem.setProperty('content', 'actors')
            elif cat['type'] == 'directors':
                menuitem.setProperty('content', 'directors')
            self.menu.addItem(menuitem)
            if self.navback:
                self.menu.selectItem(self.history[self.level]['menuposition'])
            self.content[cat['type']] = listitems
            if self.navback and self.focusset == 'false':
                if self.history[self.level]['menutype'] == cat['type']:
                    if cat['type'] != 'actors' and cat['type'] != 'directors' and cat['type'] != 'tvactors':
                        self.setContent(cat['content'])
                    elif cat['type'] == 'actors' or cat['type'] == 'tvactors':
                        self.setContent('actors')
                    elif cat['type'] == 'directors':
                        self.setContent('directors')
                    self.addItems(listitems)
                    # wait for items to be added before we can set focus
                    xbmc.sleep(100)
                    self.setCurrentListPosition(self.history[self.level]['containerposition'])
                    self.menutype = cat['type']
                    self.focusset = 'true'
            elif self.focusset == 'false':
                if cat['type'] != 'actors' and cat['type'] != 'directors' and cat['type'] != 'tvactors':
                    self.setContent(cat['content'])
                elif cat['type'] == 'actors' or cat['type'] == 'tvactors':
                    self.setContent('actors')
                elif cat['type'] == 'directors':
                    self.setContent('directors')
                self.addItems(listitems)
                # wait for items to be added before we can set focus
                xbmc.sleep(100)
                self.setFocusId(self.getCurrentContainerId())
                self.menutype = cat['type']
                self.focusset = 'true'

    def _fetch_channelgroups(self, cat):
        self.getControl(SEARCHCATEGORY).setLabel(xbmc.getLocalizedString(19069))
        self.getControl(SEARCHCATEGORY).setVisible(True)
        channelgrouplist = []
        json_response = self._cached_json_rpc('{"jsonrpc":"2.0", "method":"PVR.GetChannelGroups", "params":{"channeltype":"tv"}, "id":1}')
        if('result' in json_response) and(json_response['result'] != None) and('channelgroups' in json_response['result']):
            for item in json_response['result']['channelgroups']:
                channelgrouplist.append(item['channelgroupid'])
            if channelgrouplist:
                self._fetch_channels(cat, channelgrouplist)

    def _fetch_channels(self, cat, channelgrouplist):
        # get all channel id's
        channellist = []
        for channelgroupid in channelgrouplist:
            json_response = self._cached_json_rpc('{"jsonrpc":"2.0", "method":"PVR.GetChannels", "params":{"channelgroupid":%i, "properties":["channel", "thumbnail"]}, "id":1}' % channelgroupid)
            if('result' in json_response) and(json_response['result'] != None) and('channels' in json_response['result']):
                for item in json_response['result']['channels']:
                    channellist.append(item)
        if channellist:
            # remove duplicates
            channels = [dict(tuples) for tuples in set(tuple(item.items()) for item in channellist)]
            # sort
            channels.sort(key=operator.itemgetter('channelid'))
            self._fetch_livetv(cat, channels)

    def _fetch_livetv(self, cat, channels):
        listitems = []
        # get all programs for every channel id
        for channel in channels:
            channelid = channel['channelid']
            channelname = channel['label']
            channelthumb = channel['thumbnail']
            json_response = self._cached_json_rpc('{"jsonrpc":"2.0", "method":"PVR.GetBroadcasts", "params":{"channelid":%i, "properties":["starttime", "endtime", "runtime", "genre", "plot"]}, "id":1}' % channelid)
            if('result' in json_response) and(json_response['result'] != None) and('broadcasts' in json_response['result']):
                for item in json_response['result']['broadcasts']:
                    broadcastname = item['label']
                    livetvmatch = re.search('.*' + self.searchstring + '.*', broadcastname, re.I)
                    if livetvmatch:
                        broadcastid = item['broadcastid']
                        duration = item['runtime']
                        genre = item['genre'][0]
                        plot = item['plot']
                        starttime = item['starttime']
                        endtime = item['endtime']
                        listitem = xbmcgui.ListItem(label=broadcastname, offscreen=True)
                        listitem.setArt({'icon':'DefaultFolder.png', 'thumb':channelthumb})
                        listitem.setProperty("icon", channelthumb)
                        listitem.setProperty("genre", genre)
                        listitem.setProperty("plot", plot)
                        listitem.setProperty("starttime", starttime)
                        listitem.setProperty("endtime", endtime)
                        listitem.setProperty("duration", str(duration))
                        listitem.setProperty("channelname", channelname)
                        listitem.setProperty("dbid", str(channelid))
                        listitems.append(listitem)
        if len(listitems) > 0:
            menuitem = xbmcgui.ListItem(xbmc.getLocalizedString(cat['label']), offscreen=True)
            menuitem.setArt({'icon':cat['menuthumb']})
            menuitem.setProperty('type', cat['type'])
            menuitem.setProperty('content', cat['content'])
            self.menu.addItem(menuitem)
            self.content[cat['type']] = listitems
            if self.focusset == 'false':
                self.setContent(cat['content'])
                self.addItems(listitems)
                # wait for items to be added before we can set focus
                xbmc.sleep(100)
                self.setFocusId(self.getCurrentContainerId())
                self.focusset = 'true'

    def _update_list(self, item, content):
        self.clearList()
        # we need some sleep, else the correct container layout won't be loaded
        xbmc.sleep(2)
        self.setContent(content)
        xbmc.sleep(2)
        self.addItems(self.content[item])

    def _get_info(self, labels, item):
        labels['mediatype'] = item
        labels['dbid'] = labels['%sid' % item]
        del labels['%sid' % item]
        if item == 'season' or item == 'artist':
            labels['title'] = labels['label']
        del labels['label']
        if item != 'artist' and item != 'album' and item != 'song' and item != 'livetv':
            del labels['art']
        elif item == 'artist' or item == 'album' or item == 'song':
            del labels['art']
            del labels['thumbnail']
            del labels['fanart']
        else:
            del labels['thumbnail']
            del labels['fanart']
        if item == 'movie' or item == 'tvshow' or item == 'episode' or item == 'musicvideo':
            labels['duration'] = labels['runtime']
            labels['path'] = labels['file']
            del labels['file']
            del labels['runtime']
            if item != 'tvshow':
                del labels['streamdetails']
                del labels['resume']
            else:
                del labels['watchedepisodes']
        if item == 'season' or item == 'episode':
            labels['tvshowtitle'] = labels['showtitle']
            del labels['showtitle']
            if item == 'season':
                del labels['tvshowid']
                del labels['watchedepisodes']
            else:
                labels['aired'] = labels['firstaired']
                del labels['firstaired']
        if item == 'album':
            labels['album'] = labels['title']
            del labels['artistid']
        if item == 'song':
            labels['tracknumber'] = labels['track']
            del labels['track']
            del labels['file']
            del labels['artistid']
            del labels['albumid']
        for key, value in labels.items():
            if isinstance(value, list):
                if key == 'artist' and item == 'musicvideo':
                    continue
                value = " / ".join(value)
            labels[key] = value
        return labels

    def _get_art(self, labels, icon, media):
        if media == 'video':
            art = labels['art']
            if labels.get('poster'):
                art['thumb'] = labels['poster']
            elif labels.get('banner'):
                art['thumb'] = labels['banner']
            # needed for seasons and episodes
            elif art.get('tvshow.fanart'):
               art['fanart'] = art['tvshow.fanart']
        else:
            art = labels['art']
            # needed for albums and songs
            art['thumb'] = labels['thumbnail']
            art['fanart'] = labels['fanart']
        art['icon'] = icon
        return art

    def _split_labels(self, item, labels, prefix):
        props = {}
        for label in labels:
            if label == 'thumbnail' or label == 'fanart' or label == 'art' or label == 'rating' or label == 'userrating' or label == 'title' or label == 'file' or label == 'artistid' or label == 'albumid' or label == 'songid' or (prefix == 'album_' and (label == 'artist' or label == 'genre' or label == 'year')):
                continue
            if isinstance(item[label], list):
                item[label] = " / ".join(item[label])
            if label == 'albumlabel':
                props[prefix + 'label'] = item['albumlabel']
            else:
                props[prefix + label] = item[label]
            del item[label]
        return item, props

    def _clean_string(self, string):
        return string.replace('(', '[(]').replace(')', '[)]').replace('+', '[+]')

    def _get_allitems(self, key, listitem):
        if key == 'tvshowseasons':
            search = listitem.getVideoInfoTag().getDbId()
        elif key == 'seasonepisodes':
            tvshow = listitem.getProperty('tvshowid')
            season = listitem.getVideoInfoTag().getSeason()
            search = [tvshow, season]
        elif key == 'artistalbums':
            search = listitem.getMusicInfoTag().getDbId()
        elif key == 'albumsongs':
            search = listitem.getMusicInfoTag().getDbId()
        elif key == 'actormovies' or key == 'directormovies' or key == 'actortvshows':
            search = listitem.getLabel()
        self._reset_variables()
        self._hide_controls()
        self.clearList()
        self.menu.reset()
        self.oldfocus = 0
        self.level += 1
        self.history[self.level - 1]['menuposition']  = self.menuposition
        self.history[self.level - 1]['menutype']  = self.menutype
        self.history[self.level - 1]['containerposition']  = self.containerposition
        self.history[self.level] = {'cats':[CATEGORIES[key]], 'search':search,}
        self._get_items(CATEGORIES[key], search)
        self._check_focus()

    def _play_item(self, key, value, listitem=None):
        if key == 'file':
            xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Player.Open", "params":{"item":{"%s":"%s"}}, "id":1}' % (key, value))
        elif key == 'albumid' or key == 'songid':
            xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Player.Open", "params":{"item":{"%s":%d}}, "id":1}' % (key, int(value)))
        else:
            resume = int(listitem.getProperty('resume'))
            selected = False
            if self.playaction == 0:
                labels = ()
                functions = ()
                if int(resume) > 0:
                    m, s = divmod(resume, 60)
                    h, m = divmod(m, 60)
                    val = '%d:%02d:%02d' % (h, m, s)
                    labels += (LANGUAGE(32212) % val,)
                    functions += ('resume',)
                    labels += (xbmc.getLocalizedString(12021),)
                    functions += ('play',)
                else:
                    labels += (xbmc.getLocalizedString(208),)
                    functions += ('play',)
                labels += (xbmc.getLocalizedString(22081),)
                functions += ('info',)
                selection = xbmcgui.Dialog().contextmenu(labels)
                if selection >= 0:
                    selected = True
                    if functions[selection] == 'play':
                        self.playaction = 1
                    elif functions[selection] == 'resume':
                        self.playaction = 2
                    elif functions[selection] == 'info':
                        self.playaction = 3
            if self.playaction == 3:
                self._show_info(listitem)
            elif self.playaction == 1 or self.playaction == 2:
                if self.playaction == 1 and not selected:
                    if int(resume) > 0:
                        labels = ()
                        functions = ()
                        m, s = divmod(resume, 60)
                        h, m = divmod(m, 60)
                        val = '%d:%02d:%02d' % (h, m, s)
                        labels += (LANGUAGE(32212) % val,)
                        functions += ('resume',)
                        labels += (xbmc.getLocalizedString(12021),)
                        functions += ('play',)
                        selection = xbmcgui.Dialog().contextmenu(labels)
                        if functions[selection] == 'resume':
                            self.playaction = 2
                if self.playaction == 2:
                    self.Player.resume = resume
                xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Player.Open", "params":{"item":{"%s":%d}}, "id":1}' % (key, int(value)))

    def _check_focus(self):
        self.getControl(SEARCHCATEGORY).setVisible(False)
        self.getControl(SEARCHBUTTON).setVisible(True)
        if self.focusset == 'false':
            self.getControl(NORESULTS).setVisible(True)
            self.setFocus(self.getControl(SEARCHBUTTON))

    def _context_menu(self, controlId, listitem):
        labels = ()
        functions = ()
        media = ''
        if listitem.getProperty('media') == 'video':
            media = listitem.getVideoInfoTag().getMediaType()
        elif listitem.getProperty('media') == 'music':
            media = listitem.getMusicInfoTag().getMediaType()
        if media == 'movie':
            labels += (xbmc.getLocalizedString(13346),)
            functions += ('info',)
            path = listitem.getVideoInfoTag().getTrailer()
            if path:
                labels += (LANGUAGE(32205),)
                functions += ('play',)
        elif media == 'tvshow':
            labels += (xbmc.getLocalizedString(20351), LANGUAGE(32207), LANGUAGE(32208),)
            functions += ('info', 'tvshowseasons', 'tvshowepisodes',)
        elif media == 'episode':
            labels += (xbmc.getLocalizedString(20352),)
            functions += ('info',)
        elif media == 'musicvideo':
            labels += (xbmc.getLocalizedString(20393),)
            functions += ('info',)
        elif media == 'artist':
            labels += (xbmc.getLocalizedString(21891), LANGUAGE(32209), LANGUAGE(32210),)
            functions += ('info', 'artistalbums', 'artistsongs',)
        elif media == 'album':
            labels += (xbmc.getLocalizedString(13351),)
            functions += ('info',)
            labels += (xbmc.getLocalizedString(208),)
            functions += ('play',)
        elif media == 'song':
            labels += (xbmc.getLocalizedString(658),)
            functions += ('info',)
        if listitem.getProperty('type') != 'livetv':
            if listitem.getProperty('content') in ('movies', 'episodes', 'musicvideos', 'songs'):
                path = listitem. getPath()
            elif listitem.getProperty('content') == 'tvshows':
                dbid = listitem.getVideoInfoTag().getDbId()
                path = "videodb://tvshows/titles/%s/" % dbid
            elif listitem.getProperty('content') == 'seasons':
                dbid = listitem.getVideoInfoTag().getSeason()
                tvshowid = listitem.getProperty('tvshowid')
                path = "videodb://tvshows/titles/%s/%s/?tvshowid=%s" % (tvshowid, dbid, tvshowid)
            elif listitem.getProperty('content') == 'artists':
                dbid = listitem.getMusicInfoTag().getDbId()
                path = "musicdb://artists/%s/?albumartistsonly=%s" % (dbid, self.albumartists)
            elif listitem.getProperty('content') == 'albums':
                dbid = listitem.getMusicInfoTag().getDbId()
                artistid = listitem.getProperty('artistid')
                path = "musicdb://artists/%s/%s/?albumartistsonly=%s&artistid=%s" % (artistid, dbid, self.albumartists, artistid)
            if path in self.favourites:
                labels += (xbmc.getLocalizedString(14077),)
            else:
                labels += (xbmc.getLocalizedString(14076),)
            functions += ('favourite',)
        if labels:
            selection = xbmcgui.Dialog().contextmenu(labels)
            if selection >= 0:
                if functions[selection] == 'info':
                    self._show_info(listitem)
                elif functions[selection] == 'play':
                    if media != 'album':
                        self._play_item('file', path)
                    else:
                        self._play_item('albumid', dbid)
                elif functions[selection] == 'favourite':
                    self._add_favourite(listitem)
                else:
                    self._get_allitems(functions[selection], listitem)

    def _show_info(self, listitem):
        xbmcgui.Dialog().info(listitem)

    def _add_favourite(self, listitem):
        label = listitem.getLabel()
        thumbnail = listitem.getArt('poster')
        if not thumbnail:
            thumbnail = listitem.getArt('banner')
        if not thumbnail:
            thumbnail = listitem.getArt('thumb')
        if not thumbnail:
            thumbnail = listitem.getArt('icon')
        if listitem.getProperty('content') in ('movies', 'episodes', 'musicvideos', 'songs'):
            path = listitem. getPath()
            xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Favourites.AddFavourite", "params":{"type":"media", "title":"%s", "path":"%s", "thumbnail":"%s"}, "id": 1}' % (label, path, thumbnail))
        elif listitem.getProperty('content') == 'tvshows':
            dbid = listitem.getVideoInfoTag().getDbId()
            xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Favourites.AddFavourite", "params":{"type":"window", "window":"10025", "windowparameter":"videodb://tvshows/titles/%s/", "title":"%s", "thumbnail":"%s"}, "id": 1}' % (dbid, label, thumbnail))
        elif listitem.getProperty('content') == 'seasons':
            dbid = listitem.getVideoInfoTag().getSeason()
            tvshowid = listitem.getProperty('tvshowid')
            xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Favourites.AddFavourite", "params":{"type":"window", "window":"10025", "windowparameter":"videodb://tvshows/titles/%s/%s/?tvshowid=%s", "title":"%s", "thumbnail":"%s"}, "id": 1}' % (tvshowid, dbid, tvshowid, label, thumbnail))
        elif listitem.getProperty('content') == 'artists':
            dbid = listitem.getMusicInfoTag().getDbId()
            xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Favourites.AddFavourite", "params":{"type":"window", "window":"10502", "windowparameter":"musicdb://artists/%s/?albumartistsonly=%s", "title":"%s", "thumbnail":"%s"}, "id": 1}' % (dbid, self.albumartists, label, thumbnail))
        elif listitem.getProperty('content') == 'albums':
            dbid = listitem.getMusicInfoTag().getDbId()
            artistid = listitem.getProperty('artistid')
            xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Favourites.AddFavourite", "params":{"type":"window", "window":"10502", "windowparameter":"musicdb://artists/%s/%s/?albumartistsonly=%s&artistid=%s", "title":"%s", "thumbnail":"%s"}, "id": 1}' % (artistid, dbid, self.albumartists, artistid, label, thumbnail))
        self._load_favourites()

    def _nav_back(self):
        self._reset_variables()
        self._hide_controls()
        self.clearList()
        self.menu.reset()
        self.oldfocus = 0
        cats = self.history[self.level]['cats']
        search = self.history[self.level]['search']
        self.navback = True
        for cat in cats:
            self._get_items(cat, search)
        self.navback = False

    def _new_search(self):
        self.searchstring = search()
        if self.searchstring:
            self.menu.reset()
            self.oldfocus = 0
            self.clearList()
            self.onInit()
        return self.searchstring

    def onClick(self, controlId):
        if controlId == self.getCurrentContainerId():
            self.containerposition = self.getCurrentListPosition()
            listitem = self.getListItem(self.getCurrentListPosition())
            media = ''
            if listitem.getLabel() == '..':
                self.level -= 1
                self._nav_back()
                return
            if listitem.getVideoInfoTag().getMediaType():
                media = listitem.getVideoInfoTag().getMediaType()
            elif listitem.getMusicInfoTag().getMediaType():
                media = listitem.getMusicInfoTag().getMediaType()
            elif xbmc.getCondVisibility('Container.Content(actors)'):
                media = 'actors'
            elif xbmc.getCondVisibility('Container.Content(directors)'):
                media = 'directors'
            if media == 'movie':
                movieid = listitem.getVideoInfoTag().getDbId()
                self._play_item('movieid', movieid, listitem)
            elif media == 'tvshow':
                dbid = listitem.getVideoInfoTag().getDbId()
                path = "videodb://tvshows/titles/%s/" % dbid
                xbmc.executebuiltin('ReplaceWindow(Videos,{},return)'.format(path))
            elif media == 'season':
                self._get_allitems('seasonepisodes', listitem)
            elif media == 'episode':
                episodeid = listitem.getVideoInfoTag().getDbId()
                self._play_item('episodeid', episodeid, listitem)
            elif media == 'musicvideo':
                musicvideoid = listitem.getVideoInfoTag().getDbId()
                self._play_item('musicvideoid', musicvideoid, listitem)
            elif media == 'artist':
                self._get_allitems('artistalbums', listitem)
            elif media == 'album':
                self._get_allitems('albumsongs', listitem)
            elif media == 'song':
                songid = listitem.getMusicInfoTag().getDbId()
                self._play_item('songid', songid)
            elif media == 'actors':
                content = listitem.getProperty('content')
                if content == 'actors':
                    self._get_allitems('actormovies', listitem)
                if content == 'tvactors':
                    self._get_allitems('actortvshows', listitem)
            elif media == 'directors':
                self._get_allitems('directormovies', listitem)
        elif controlId == MENU:
            item = self.menu.getSelectedItem().getProperty('type')
            content = self.menu.getSelectedItem().getProperty('content')
            self.menuposition = self.menu.getSelectedPosition()
            self.menutype = self.menu.getSelectedItem().getProperty('type')
            self._update_list(item, content)
        elif controlId == SEARCHBUTTON:
            self._new_search()

    def onAction(self, action):
        if action.getId() in ACTION_EXIT:
            self._close()

        elif action.getId() in ACTION_BACK:
            if self.level <= 1:
                self._close()
            else:
                self.level -= 1
                self._nav_back()

        elif action.getId() in ACTION_CONTEXT_MENU or action.getId() in ACTION_SHOW_INFO:
            controlId = self.getFocusId()
            if controlId == self.getCurrentContainerId():
                listitem = self.getListItem(self.getCurrentListPosition())
                if action.getId() in ACTION_CONTEXT_MENU:
                    self._context_menu(controlId, listitem)
                elif action.getId() in ACTION_SHOW_INFO:
                    media = ''
                    if listitem.getVideoInfoTag().getMediaType():
                        media = listitem.getVideoInfoTag().getMediaType()
                    elif listitem.getMusicInfoTag().getMediaType():
                        media = listitem.getMusicInfoTag().getMediaType()
                    if media != '' and media != 'season':
                        self._show_info(listitem)

        elif self.getFocusId() == MENU and action.getId() in (1, 2, 3, 4, 107):
            item = self.menu.getSelectedItem().getProperty('type')
            content = self.menu.getSelectedItem().getProperty('content')
            self.menuposition = self.menu.getSelectedPosition()
            self.menutype = self.menu.getSelectedItem().getProperty('type')
            if self.oldfocus and item != self.oldfocus:
                self.oldfocus = item
                self._update_list(item, content)
            else:
                self.oldfocus = item

    def _close(self):
        settings.setInt('view', self.getCurrentContainerId())
        xbmcgui.Window(self.window_id).clearProperty('GlobalSearch.SearchString')
        self.close()
        log.debug('script stopped')


class MyPlayer(xbmc.Player):
    def __init__(self, *args, **kwargs):
        xbmc.Player.__init__(self)
        self.resume = 0

    def onAVStarted(self):
        if self.resume > 0:
            self.seekTime(float(self.resume))

def search():
    searches = settings.getJSON('searches', [])

    history_length = settings.getInt('history_length', 10)
    searches = searches[:history_length]

    searchstring = ''
    if searches:
        options = [u'[B]{}[/B]'.format(LANGUAGE(32299))]
        options.extend(searches)
        index = xbmcgui.Dialog().select(xbmc.getLocalizedString(137), options)
        if index == -1:
            return False

        if index > 0:
            searchstring = options[index]

    if not searchstring:
        keyboard = xbmc.Keyboard('', LANGUAGE(32101), False)
        keyboard.doModal()
        if (keyboard.isConfirmed()):
            searchstring = keyboard.getText()

    if not searchstring:
        return False

    if searchstring in searches:
        searches.remove(searchstring)

    searches.insert(0, searchstring)
    settings.setJSON('searches', searches)
    return searchstring
