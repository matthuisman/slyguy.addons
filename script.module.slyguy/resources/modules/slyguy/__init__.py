import sys

from slyguy.log import log
from slyguy.settings import is_donor, check_donor, set_drm_level
from slyguy.constants import ADDON_ID, COMMON_ADDON_ID, DEPENDENCIES_ADDON_ID, NEW_SETTINGS


log.debug('sys.path: {}'.format(sys.path))
if ADDON_ID not in sys.path[0]:
    paths = [None, None, None]
    for path in sys.path:
        if COMMON_ADDON_ID in path and 'modules' in path:
            paths[1] = path
        elif DEPENDENCIES_ADDON_ID in path and 'modules' in path:
            paths[2] = path
        elif ADDON_ID in path:
            paths[0] = path
    sys.path = [x for x in paths if x] + [x for x in sys.path if x not in paths]
    log.debug('Fixed sys.path: {}'.format(sys.path))


if NEW_SETTINGS:
    log.info("Using new settings system")
    from slyguy.settings import settings
    settings.common_settings = settings
else:
    from slyguy.settings import legacy_settings as settings
    from slyguy.settings import settings as common_settings
    settings.common_settings = common_settings
