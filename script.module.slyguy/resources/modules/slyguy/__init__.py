import sys

from .log import log

if 'slyguy.dependencies' in sys.path[-1]:
    new_path = sys.path[-3:] + sys.path[:-3]
    log.debug('Changing Kodi 20+ wrong sys.path (xbmc/issues/22985)\nOld: {}\nNew: {}'.format(sys.path, new_path))
    sys.path = new_path
