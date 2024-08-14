import os
import time
from collections import defaultdict

import peewee
from kodi_six import xbmc

from slyguy import database, log, _
from slyguy.constants import COMMON_ADDON_ID, COMMON_ADDON, ADDON_ID


class Settings(database.Model):
    addon_id = peewee.CharField(index=True)
    key = peewee.CharField(index=True)
    value = database.JSONField()

    class Meta:
        primary_key = peewee.CompositeKey('addon_id', 'key')
        table_name = 'settings'


profile_path = xbmc.translatePath(COMMON_ADDON.getAddonInfo('profile'))
db_path = os.path.join(profile_path, 'settings.db')
db = database.init([Settings], db_path)


class DBStorage():
    SETTINGS = {}
    NO_ENTRY = object()

    def __init__(self, cache=defaultdict(dict), cache_enabled=True):
        self._cache = cache
        self._cache_enabled = cache_enabled

    def get(self, addon_id, key, inherit=True):
        if self._cache_enabled:
            if not self._cache:
                self._preload_cache()

            try:
                return self._cache[addon_id][key]
            except KeyError:
                pass

        try:
            row = Settings.select().where(Settings.addon_id.in_((addon_id, COMMON_ADDON_ID)) if inherit and addon_id != COMMON_ADDON_ID else Settings.addon_id == addon_id, Settings.key == key).order_by(
                peewee.Case(None, [(Settings.addon_id == addon_id, 0)], 1), addon_id).limit(1)[0]
            value = (row.addon_id, row.value)
        except (Settings.DoesNotExist, IndexError):
            value = (addon_id, DBStorage.NO_ENTRY)

        self._cache[addon_id][key] = value
        return value

    def _preload_cache(self):
        start = time.time()
        # order common value first so addons value overrides cache
        query = Settings.select().where(Settings.addon_id.in_((ADDON_ID, COMMON_ADDON_ID))).order_by(
            peewee.Case(None, [(Settings.addon_id == COMMON_ADDON_ID, 0)], 1), COMMON_ADDON_ID)

        rows = defaultdict(list)
        for row in query:
            if row.key not in self.SETTINGS:
                log.info("Deleting removed setting: {}: {}".format(row.addon_id, row.key))
                row.delete_instance()
            else:
                rows[row.key].append(row)

        for setting in self.SETTINGS.values():
            if setting.id not in rows:
                self._cache[COMMON_ADDON_ID][setting.id] = self._cache[ADDON_ID][setting.id] = (setting._owner, DBStorage.NO_ENTRY)
                continue

            for row in rows[setting.id]:
                if not setting._inherit and row.addon_id != ADDON_ID:
                    self._cache[ADDON_ID][setting.id] = (setting._owner, DBStorage.NO_ENTRY)
                else:
                    self._cache[ADDON_ID][setting.id] = (row.addon_id, row.value)
                if row.addon_id == COMMON_ADDON_ID:
                    self._cache[COMMON_ADDON_ID][setting.id] = (row.addon_id, row.value)
        log.debug("Settings cache load time: {}".format(time.time() - start))

    def set(self, addon_id, key, value):
        if self._cache[addon_id].get(key) == (addon_id, value):
            return

        Settings.replace(addon_id=addon_id, key=key, value=value).execute()
        self._cache[addon_id][key] = (addon_id, value)

    def delete(self, addon_id, key):
        Settings.delete_where(Settings.addon_id == addon_id, Settings.key == key)
        self._cache[addon_id][key] = (addon_id, DBStorage.NO_ENTRY)

    def delete_all(self, addon_id):
        Settings.delete_where(Settings.addon_id == addon_id)
        self._cache.pop(addon_id, None)

    def get_addon_ids(self):
        return [x.addon_id for x in Settings.select(Settings.addon_id).where(Settings.addon_id != COMMON_ADDON_ID).distinct()]

    def reset(self):
        self._cache.clear()
