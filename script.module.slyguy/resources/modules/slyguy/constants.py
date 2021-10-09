import os

from kodi_six import xbmc, xbmcaddon

##### ADDON ####
ADDON          = xbmcaddon.Addon(os.environ.get('ADDON_ID', ''))
ADDON_ID       = ADDON.getAddonInfo('id')
ADDON_VERSION  = ADDON.getAddonInfo('version')
ADDON_NAME     = ADDON.getAddonInfo('name')
ADDON_PATH     = xbmc.translatePath(ADDON.getAddonInfo('path'))
ADDON_PROFILE  = xbmc.translatePath(ADDON.getAddonInfo('profile'))
ADDON_ICON     = ADDON.getAddonInfo('icon')
ADDON_FANART   = ADDON.getAddonInfo('fanart')
ADDON_DEV      = bool(int(os.environ.get('SLYGUY_DEV', '0')))
#################

COMMON_ADDON_ID = 'script.module.slyguy'
COMMON_ADDON    = xbmcaddon.Addon(COMMON_ADDON_ID)

try:
    KODI_VERSION = int(xbmc.getInfoLabel("System.BuildVersion").split('.')[0])
except:
    KODI_VERSION = 16

#### DATABASE #####
DB_PATH         = os.path.join(ADDON_PROFILE, 'data.db')
DB_MAX_INSERTS  = 100
DB_PRAGMAS      = {
    'journal_mode': 'wal',
    'cache_size': -1 * 10000,  #10MB
    'foreign_keys': 1,
    'ignore_check_constraints': 0,
    'synchronous': 0
}
DB_TABLENAME = '_db'
###################

##### USERDATA ####
USERDATA_KEY = '_userdata'
###############

##### CACHE #####
CACHE_TABLENAME      = '_cache'
CACHE_CHECKSUM       = ADDON_VERSION # Recreates cache when new addon version
CACHE_EXPIRY         = (60*60*24) # 24 Hours
CACHE_CLEAN_INTERVAL = (60*60*4)  # 4 Hours
CACHE_CLEAN_KEY      = '_cache_cleaned'
#################

IPTV_MERGE_ID        = 'plugin.program.iptv.merge'

#### ROUTING ####
ROUTE_TAG              = '_'
ROUTE_RESET            = '_reset'
ROUTE_SETTINGS         = '_settings'
ROUTE_IA_SETTINGS      = '_ia_settings'
ROUTE_SETUP_MERGE      = '_setup_merge'
ROUTE_IA_INSTALL       = '_ia_install'
ROUTE_CLEAR_CACHE      = '_clear_cache'
ROUTE_SERVICE          = '_service'
ROUTE_SERVICE_INTERVAL = (60*5)
NO_RESUME_TAG          = '_noresume'
NO_RESUME_SUFFIX       = '.pvr'
ROUTE_URL_TAG          = '_url'
ROUTE_LIVE_TAG         = '_is_live'
ROUTE_LIVE_TAG_LEGACY  = '_l'
ROUTE_RESUME_TAG       = '_resume'
FORCE_RUN_FLAG         = '_force_run'
ROUTE_AUTOPLAY_TAG     = '_autoplay'
ROUTE_MIGRATE_DONE     = '_migrated'
ROUTE_ADD_BOOKMARK     = '_add_bookmark'
ROUTE_DEL_BOOKMARK     = '_del_bookmark'
ROUTE_BOOKMARKS        = '_bookmarks'
ROUTE_MOVE_BOOKMARK    = '_move_bookmark'
ROUTE_RENAME_BOOKMARK  = '_name_bookmark'
#################

#### INPUTSTREAM ADAPTIVE #####
IA_ADDON_ID = 'inputstream.adaptive'
IA_VERSION_KEY = '_version'
IA_HLS_MIN_VER = '2.0.0'
IA_PR_MIN_VER = '2.2.19'
IA_MPD_MIN_VER = '2.2.19'
IA_WV_MIN_VER = '2.2.27'
IA_MODULES_URL = 'https://k.slyguy.xyz/.decryptmodules/modules.json.gz'
IA_CHECK_EVERY = 86400 #24 hours
IA_LINUX_PACKAGE = 'kodi-inputstream-adaptive'
###################

#### MISC #####
NOARG = object()
#################

#### LOG #####
LOG_ID = ADDON_ID
LOG_FORMAT = u'%(name)s - %(message)s'
#################

## QUALITY ##
QUALITY_ASK = -1
QUALITY_BEST = -2
QUALITY_LOWEST = -3
QUALITY_SKIP = -4
QUALITY_CUSTOM = -5
QUALITY_DISABLED = -6
QUALITY_TYPES = [QUALITY_ASK, QUALITY_BEST, QUALITY_LOWEST, QUALITY_SKIP, QUALITY_CUSTOM, QUALITY_DISABLED]
QUALITY_TAG = '_quality'

## PLAY FROM ##
PLAY_FROM_ASK = 0
PLAY_FROM_LIVE = 1
PLAY_FROM_START = 2
PLAY_FROM_TYPES = [PLAY_FROM_ASK, PLAY_FROM_LIVE, PLAY_FROM_START]

WIDEVINE_UUID = bytearray([237, 239, 139, 169, 121, 214, 74, 206, 163, 200, 39, 220, 213, 29, 33, 237])
WIDEVINE_PSSH = bytearray([112, 115, 115, 104])

#DEFAULT_USERAGENT = xbmc.getUserAgent()
DEFAULT_USERAGENT = 'okhttp/3.4.1'
DEFAULT_WORKERS = 5

#### BOOKMARKS #####
BOOKMARK_FILE = os.path.join(ADDON_PROFILE, 'bookmarks.json')

CHUNK_SIZE = 64 * 1024
LIVE_HEAD = 12*60*60
NEWS_MAX_TIME = 432000 #5 Days
MAX_SEARCH_HISTORY = 10
MAX_QUALITY_HISTORY = 10

MIDDLEWARE_CONVERT_SUB = 'convert_sub'
MIDDLEWARE_REGEX = 'regex'
MIDDLEWARE_PLUGIN = 'plugin'

DONOR_URL = 'https://d.mjh.nz/donors/{id}'
