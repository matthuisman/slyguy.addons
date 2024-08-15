import os
import json
import xml.etree.ElementTree as ET

from kodi_six import xbmc, xbmcgui

from slyguy import dialog, log, signals
from slyguy.util import remove_file
from slyguy.language import _
from slyguy.constants import ADDON_ID, COMMON_ADDON_ID, ADDON_PROFILE, ADDON_NAME, COMMON_ADDON

from slyguy.settings.db_storage import DBStorage


USERDATA_KEY_FMT = "userdata_{key}"


class Category(object):
    _categories = {}

    def __init__(self, label, parent=None):
        self.id = len(Category._categories)
        Category._categories[self.id] = self

        self.label = label
        self.parent= parent
        self._children = []
        if parent:
            parent.add(self)

    def add(self, setting):
        self._children.append(setting)

    @property
    def children(self):
        return [x for x in self._children if x.is_visible]

    @property
    def is_visible(self):
        return any(self.children)

    @property
    def settings(self):
        return sorted([x for x in self.children if isinstance(x, Setting)], key=lambda s: s._owner == ADDON_ID, reverse=True)

    @property
    def categories(self):
        return sorted([x for x in self.children if isinstance(x, Category)], key=lambda c: all([s._owner == ADDON_ID for s in c.settings]), reverse=True)

    @classmethod
    def get(cls, category_id):
        return cls._categories[int(category_id)]


class Categories(object):
    ROOT = Category(_.SETTINGS)
    ADDON = Category(ADDON_NAME, parent=ROOT)
    PLAYER = Category(_.PLAYER, parent=ROOT)
    PLAYER_QUALITY = Category(_.QUALITY, parent=PLAYER)
    PLAYER_CODECS = Category(_.CODECS, parent=PLAYER)
    PLAYER_LANGUAGE = Category(_.LANGUAGE, parent=PLAYER)
    PLAYER_ADVANCED = Category(_.ADVANCED, parent=PLAYER)
    NETWORK = Category(_.NETWORK, parent=ROOT)
    INTERFACE = Category(_.INTERFACE, parent=ROOT)
    PVR_LIVE_TV = Category(_.PVR_LIVE_TV, parent=ROOT)
    SYSTEM = Category(_.SYSTEM, parent=ROOT)


USE_DEFAULT = object()
STORAGE = DBStorage()
class Setting(object):
    DEFAULT = None

    def __init__(self, id, label=None, owner=ADDON_ID, default=USE_DEFAULT, visible=True, enable=True, disabled_value=USE_DEFAULT, disabled_reason=None, 
                 override=True, before_save=lambda _: True, default_label=None, inherit=True, category=None, value_str='{value}',
                 confirm_clear=False, after_clear=lambda: True, legacy_ids=None, after_save=lambda _: True, description=None, private_value=False):
        self._id = str(id)
        self._label = label
        self._owner = owner
        self._default_label = default_label
        self._default = self.DEFAULT if default == USE_DEFAULT else default
        self._visible = visible
        self._enable = enable
        self._disabled_value = self._default if disabled_value == USE_DEFAULT else disabled_value
        self._disabled_reason = disabled_reason
        self._override = override  # when False, an addon cant have its own value
        self._inherit = inherit # when False, an addon can only have its own value
        self._before_save = before_save
        self._after_save = after_save
        self._category = category
        self._value_str = value_str
        self._private_value = private_value
        self.confirm_clear = confirm_clear
        self._after_clear = after_clear
        self._legacy_ids = legacy_ids or []
        self._description = description
        if not category:
            category = Categories.ADDON if owner != COMMON_ADDON_ID else Categories.ROOT
        category.add(self)

    def _get_bool_condition(self, value):
        if callable(value):
            value = value()

        if isinstance(value, str):
            value = bool(int(xbmc.getCondVisibility(value)))

        if not isinstance(value, bool):
            raise Exception('enable is not a bool')

        return value

    def matches_id(self, id):
        ids = [self.id.lower(), '_{}'.format(self.id.lower())]
        ids.extend([x.lower() for x in self._legacy_ids])
        return id.lower() in ids

    @property
    def is_default(self):
        return self.value == self._default

    @property
    def is_enabled(self):
        return self._get_bool_condition(self._enable)

    @property
    def is_visible(self):
        return self._get_bool_condition(self._visible)

    @property
    def value(self):
        value = self._get_value_owner()[1]
        return self._default if value == DBStorage.NO_ENTRY else value

    @value.setter
    def value(self, value):
        if not self._before_save(value):
            return
        self._set_value(value)
        self._after_save(value)

    def _get_value_owner(self):
        if self._disabled_value is not None and not self.is_enabled:
            return (self._owner, self._disabled_value)

        owner, value = STORAGE.get(self.owner, self._id, inherit=self._inherit)
        if value == DBStorage.NO_ENTRY:
            owner = self._owner
        return owner, value

    def can_clear(self):
        owner, value = self._get_value_owner()
        if (self._override and owner != ADDON_ID) or (owner == self._owner and value == DBStorage.NO_ENTRY) or not self.is_enabled or not self.is_visible:
            return False
        return True

    def can_bulk_clear(self):
        return self.owner == ADDON_ID and self.can_clear() and not self.confirm_clear

    def _set_value(self, value):
        STORAGE.set(self.owner, self.id, value)

    def clear(self):
        STORAGE.delete(self.owner, self._id)
        self._after_clear()

    @property
    def label(self):
        owner, value = self._get_value_owner()
        if value == DBStorage.NO_ENTRY:
            value = self._default

        if value == self._default and self._default_label:
            value = self._default_label
        else:
            value = self.get_value_label(value)

        if not self.is_enabled:
            value = _(value, _color='gray')
        elif self.can_clear():
            value = _(value, _bold=True)

        if owner == COMMON_ADDON_ID and ADDON_ID != COMMON_ADDON_ID:
            return u'{}: {} {}'.format(self._label, value, _.INHERITED_SETTING)
        else:
            return u'{}: {}'.format(self._label, value)

    @property
    def description(self):
        if not self.is_enabled:
            return self._disabled_reason
        elif self._description:
            return self._description
        else:
            return ''

    def get_value_label(self, value):
        if value is None or value == "":
            return _.NOT_SET
        else:
            return _(self._value_str, value=value)

    @property
    def owner(self):
        owner = self._owner
        if self._override:
            owner = ADDON_ID
        return owner

    @property
    def id(self):
        return self._id

    def __repr__(self):
        return str(self)

    def __str__(self):
        return self._label

    def on_clear(self):
        if not self.can_clear() or (self.confirm_clear and not dialog.yes_no(_.ARE_YOU_SURE, _.RESET_TO_DEFAULT)):
            return

        prev_value = self._get_value_owner()
        self.clear()
        if self._get_value_owner() != prev_value:
            return True

    def on_select(self):
        if not self.is_enabled:
            dialog.ok(self._disabled_reason or _.DISABLED)
            return

        elif not self.is_visible or not hasattr(self, 'select'):
            return

        prev_value = self._get_value_owner()
        self.select()
        if self._get_value_owner() != prev_value:
            return True

    def from_text(self, value):
        return json.loads(value)


class Dict(Setting):
    DEFAULT = {}


class List(Setting):
    DEFAULT = []


class Bool(Setting):
    DEFAULT = False

    def select(self):
        self.value = not self.value

    def get_value_label(self, value):
        if value:
            return _.YES
        else:
            return _.NO

    def from_text(self, value):
        return value == 'true'


class Text(Setting):
    DEFAULT = ""

    def __init__(self, *args, **kwargs):
        self._input_type = kwargs.pop('input_type', xbmcgui.INPUT_ALPHANUM)
        super(Text, self).__init__(*args, **kwargs)

    def select(self):
        value = dialog.input(self._label, default=self.value, type=self._input_type)
        if value:
            self.value = value

    def from_text(self, value):
        return value


class Browse(Text):
    DIRECTORY = 'directory'

    def __init__(self, *args, **kwargs):
        self._type = kwargs.pop('type')
        self._source = kwargs.pop('source', '')
        self._allow_create = kwargs.pop('allow_create', True)
        self._use_default = kwargs.pop('use_default', True)
        super(Browse, self).__init__(*args, **kwargs)

    def select(self):
        if self._type == Browse.DIRECTORY:
            value = xbmcgui.Dialog().browse(3 if self._allow_create else 0, self._label, shares=self._source, defaultt=self.value if self._use_default else None)
            if value:
                self.value = value

    def from_text(self, value):
        return value


class Action(Setting):
    _count = 0

    def __init__(self, action, *args, **kwargs):
        self._action = action
        id = 'action_{}'.format(Action._count)
        Action._count += 1
        super(Action, self).__init__(id, *args, **kwargs)

    @property
    def label(self):
        value = self._label
        if not self.is_enabled:
            value = _(value, _color='gray')
        return value

    def select(self):
        value = self._action
        if callable(value):
            value = value()
        if isinstance(value, str):
            value = value.replace('$ID', ADDON_ID)
            xbmc.executebuiltin(value)


class Number(Setting):
    DEFAULT = 0

    def __init__(self, *args, **kwargs):
        self._lower_limit = kwargs.pop('lower_limit', None)
        self._upper_limit = kwargs.pop('upper_limit', None)
        super(Number, self).__init__(*args, **kwargs)
    
    def select(self):
        value = dialog.numeric(self._label, default=self.value)
        if value is None:
            return

        value = int(value)
        if self._lower_limit is not None and value < self._lower_limit:
            value = self._lower_limit
        if self._upper_limit is not None and value > self._upper_limit:
            value = self._upper_limit
        self.value = value

    def from_text(self, value):
        return int(float(value))


class Enum(Setting):
    def __init__(self, *args, **kwargs):
        self._options = kwargs.pop('options', [])
        self._loop = kwargs.pop('loop', False)
        super(Enum, self).__init__(*args, **kwargs)
    
    def select(self):
        from slyguy import gui
        current = [x[1] for x in self._options].index(self.value)

        if self._loop:
            index = current + 1
            if index > len(self._options) - 1:
                index = 0
        else:
            index = gui.select(self._label, options=[x[0] for x in self._options], preselect=current)

        if index != -1:
            self.value = self._options[index][1]

    @property
    def value_label(self):
        return self.get_value_label(self.value)

    def get_value_label(self, value):
        return [x[0] for x in self._options if x[1] == value][0]

    def from_text(self, value):
        return self._options[int(value)][1]


def migrate(settings):
    settings_path = os.path.join(ADDON_PROFILE, 'settings.xml')
    if settings.MIGRATED.value:
        if os.path.exists(settings_path) and remove_file(settings_path):
            log.info("Removed old settings.xml: '{}'".format(settings_path))
        return

    old_settings = {}
    if os.path.exists(settings_path):
        try:
            tree = ET.parse(settings_path)
            for elem in tree.findall('setting'):
                if 'id' in elem.attrib:
                    value = elem.text or elem.attrib.get('value')
                    if value:
                        old_settings[elem.attrib['id']] = value
        except Exception as e:
            log.error("Failed to parse old settings: {} ({})".format(settings_path, e))

    default_overrides = {
        'max_bandwidth': 7,
        'epg_days': 3,
        'pagination_multiplier': 1,
    }

    new_settings = [x for x in settings.SETTINGS.values() if x.owner == ADDON_ID]

    count = 0
    for key in old_settings:
        xml_val = old_settings[key]

        setting = None
        for check in new_settings:
            if check.matches_id(key):
                setting = check

        if not setting:
            log.info("Migrate: Ignoring '{}' as no new setting found".format(key))
            continue

        try:
            value = setting.from_text(xml_val)
            if key in default_overrides and default_overrides[key] == value:
                value = setting._default

            if value != setting._default:
                setting._set_value(value)
                log.info("Migrate: '{}' -> '{}' -> '{}'".format(key, setting.id, value))
                count += 1
            else:
                log.info("Migrate: Ignoring '{}' as is default value '{}'".format(setting.id, value))
        except Exception as e:
            log.error("Migrate: Error '{}' -> '{}' ({})".format(key, setting.id, e))

    BaseSettings.MIGRATED.value = True
    log.info("{}/{} old settings have been migrated the new SlyGuy settings system!".format(count, len(old_settings)))


def migrate_userdata(settings):
    legacy_userdata = settings.USERDATA.value
    if not legacy_userdata:
        return

    for key in legacy_userdata:
        value = legacy_userdata[key]
        if not value:
            continue

        new_key = USERDATA_KEY_FMT.format(key=key)
        log.info("Migrate Userdata: '{}' -> '{}'".format(key, new_key))
        settings.set(new_key, value=value)

    settings.USERDATA.clear()
    log.info("Migrated Userdata")


class BaseSettings(object):
    MIGRATED = Bool('migrated', visible=False, override=False, inherit=False)
    USERDATA = Dict('userdata', visible=False, override=False, inherit=False) #LEGACY
    BOOKMARKS_DATA = List('bookmarks_data', visible=False, override=False, inherit=False)
    SETTINGS = {}

    def __init__(self, addon_id=ADDON_ID):
        self._load_settings()
        self._migrated = False

    def _load_settings(self, attr_used={}):
        for cls in self.__class__.mro():
            if cls is object:
                continue

            for name in cls.__dict__:
                setting = cls.__dict__[name]
                if not isinstance(setting, Setting):
                    continue

                if name in attr_used:
                    if attr_used[name] != cls:
                        raise Exception("Name '{}' already used by '{}'".format(name, attr_used[name].__name__))
                    continue

                if setting.id in self.SETTINGS:
                    if self.SETTINGS[setting.id] != setting:
                        raise Exception("Setting ID '{}' already used by '{}'".format(setting.id, self.SETTINGS[setting.id]._owner))
                    continue

                if setting._label is None:
                    # try get matching language
                    setting._label = getattr(_, name, name.upper())

                attr_used[name] = cls
                self.SETTINGS[setting.id] = setting

    def get_settings(self):
        return [self.SETTINGS[x] for x in self.SETTINGS]

    def getEnum(self, key, choices=None, default=None):
        return self.get(key, default=default)

    def get(self, key, default=None):
        return self.get_setting(key, default).value
    getDict = getInt = getBool = getFloat = get

    def set(self, key, value):
        self.get_setting(key).value = value
    setDict = setInt = setBool = setFloat = set

    def remove(self, key):
        self.get_setting(key).clear()
    delete = remove

    def pop(self, key, default=None):
        value = self.get(key, default)
        self.remove(key)
        return value

    def get_setting(self, key, default=None):
        if not self._migrated:
            self._migrated = True
            migrate(self)
            migrate_userdata(self)

        for setting in self.SETTINGS.values():
            if setting.matches_id(key):
                return setting

        setting = Dict(key, owner=ADDON_ID, default=default, override=False, inherit=False, visible=False)
        self.SETTINGS[key] = setting
        log.debug("Setting '{}' not found. Created on-the-fly.".format(key))
        return setting

    def reset(self):
        reset()


@signals.on(signals.BEFORE_DISPATCH)
def reset():
    STORAGE.reset()
