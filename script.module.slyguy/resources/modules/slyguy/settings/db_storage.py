import os
import time
from copy import deepcopy
from collections import defaultdict

import peewee
from kodi_six import xbmc

from slyguy import database, log, _
from slyguy.util import load_json
from slyguy.constants import COMMON_ADDON_ID, COMMON_ADDON, ADDON_ID


class Settings(database.Model):
    addon_id = peewee.CharField(index=True)
    key = peewee.CharField(index=True)
    value = database.JSONField()

    class Meta:
        primary_key = peewee.CompositeKey('addon_id', 'key')
        table_name = 'settings'


profile_path = xbmc.translatePath(COMMON_ADDON.getAddonInfo('profile'))
try:
    json_settings = load_json(os.path.join(profile_path, 'settings.json'))
    db_path = json_settings['db_path']
except:
    db_path = os.path.join(profile_path, 'settings.db')
db = database.init([Settings], db_path)


class DBStorage():
    NO_ENTRY = object()

    def __init__(self, cache=defaultdict(dict)):
        self._cache = cache

    def get(self, addon_id, key, inherit=True):
        if not self._cache:
            start = time.time()
            for row in Settings.select().where(Settings.addon_id.in_((ADDON_ID, COMMON_ADDON_ID))):
                self._cache[row.addon_id][row.key] = (row.addon_id, row.value)
            log.debug("Settings cache load time: {}".format(time.time() - start))

        try:
            return deepcopy(self._cache[addon_id][key])
        except KeyError:
            pass

        if inherit and addon_id != COMMON_ADDON_ID:
            try:
                return deepcopy(self._cache[COMMON_ADDON_ID][key])
            except KeyError:
                pass

        return (addon_id, DBStorage.NO_ENTRY)

    def set(self, addon_id, key, value):
        if self._cache[addon_id].get(key) == (addon_id, value):
            return

        Settings.replace(addon_id=addon_id, key=key, value=value).execute()
        self._cache[addon_id][key] = (addon_id, value)

    def delete(self, addon_id, key):
        Settings.delete_where(Settings.addon_id == addon_id, Settings.key == key)
        self._cache[addon_id].pop(key, None)

    def delete_all(self, addon_id):
        Settings.delete_where(Settings.addon_id == addon_id)
        self._cache.pop(addon_id, None)

    def get_addon_ids(self):
        return [x.addon_id for x in Settings.select(Settings.addon_id).where(Settings.addon_id != COMMON_ADDON_ID).distinct()]

    def reset(self):
        self._cache.clear()
