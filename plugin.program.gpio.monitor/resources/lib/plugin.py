from kodi_six import xbmc

from slyguy import plugin, gui, settings, database, signals, userdata
from slyguy.constants import ADDON_ID
from slyguy.util import set_kodi_string, get_kodi_string

from . import gpio
from .language import _
from .models import Button
from .constants import FUNCTION_DELIMETER, AUTO_RELOAD_SETTING

@plugin.route('')
def home(**kwargs):
    folder = plugin.Folder(cacheToDisc=False)

    if not gpio.INSTALLED:
        folder.add_item(
            label = _(_.INSTALL_SERVICE, _bold=True),
            path  = plugin.url_for(install_service),
            info  = {'plot': _.INSTALL_SERVICE_DESC},
            bookmark = False,
        )

    if gpio.SYSTEM == 'mock':
        if not userdata.get('_warning'):
            gui.ok(_.SYSTEM_UNSUPPORTED)
            userdata.set('_warning', True)

        folder.title = _(_.SIMULATION, _color='red')

    btns = list(Button.select())

    for btn in btns:
        label, description = btn.label()

        item = plugin.Item(
            label = label,
            info  = {'plot': description},
            path  = plugin.url_for(view_btn, id=btn.id),
        )

        item.context.append((_.DELETE_BTN, 'RunPlugin({})'.format(plugin.url_for(delete_btn, id=btn.id))))

        if btn.when_pressed:
            item.context.append((_.TEST_PRESS, 'RunPlugin({})'.format(plugin.url_for(test_btn, id=btn.id, method='when_pressed'))))

        if btn.when_released:
            item.context.append((_.TEST_RELEASE, 'RunPlugin({})'.format(plugin.url_for(test_btn, id=btn.id, method='when_released'))))

        if btn.when_held:
            item.context.append((_.TEST_HOLD, 'RunPlugin({})'.format(plugin.url_for(test_btn, id=btn.id, method='when_held'))))

        folder.add_items([item])

    folder.add_item(
        label = _(_.ADD_BTN, _bold=True),
        path  = plugin.url_for(add_btn),
        info  = {'plot': _.ADD_BTN_DESC},
    )

    if not settings.getBool(AUTO_RELOAD_SETTING, False):
        folder.add_item(
            label = _.RELOAD_SERVICE,
            path  = plugin.url_for(reload_service),
            info  = {'plot': _.RELOAD_SERVICE_DESC},
        )

    if settings.getBool('bookmarks', True):
        folder.add_item(label=_(_.BOOKMARKS, _bold=True), path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

@plugin.route()
def add_btn(**kwargs):
    btn = Button(enabled=True)
    if not btn.select_pin():
        return

    btn.save()
    _on_btn_change()

@plugin.route()
def test_btn(id, method, **kwargs):
    btn = Button.get_by_id(id)
    gpio.callback(getattr(btn, method))

@plugin.route()
def view_btn(id, **kwargs):
    btn = Button.get_by_id(id)

    folder = plugin.Folder(title=btn.pin_label, cacheToDisc=False)

    folder.add_item(
        label = _(_.BTN_OPTION, option=_.BTN_PIN,  value=btn.pin_label),
        path  = plugin.url_for(edit_btn, id=btn.id, method='select_pin'),
        info  = {'plot': _.BTN_PIN_DESC},
    )

    folder.add_item(
        label   = _(_.BTN_OPTION, option=_.BTN_WHEN_PRESSED, value=btn.when_pressed),
        path    = plugin.url_for(edit_btn, id=btn.id, method='select_when_pressed'),
        info    = {'plot': _(_.BTN_WHEN_PRESSED_DESC, delimiter=FUNCTION_DELIMETER)},
        context = [(_.TEST_PRESS, 'RunPlugin({})'.format(plugin.url_for(test_btn, id=btn.id, method='when_pressed')))] if btn.when_pressed else None,
    )

    folder.add_item(
        label   = _(_.BTN_OPTION, option=_.BTN_WHEN_RELEASED, value=btn.when_released),
        path    = plugin.url_for(edit_btn, id=btn.id, method='select_when_released'),
        info    = {'plot': _(_.BTN_WHEN_RELEASED_DESC, delimiter=FUNCTION_DELIMETER)},
        context = [(_.TEST_RELEASE, 'RunPlugin({})'.format(plugin.url_for(test_btn, id=btn.id, method='when_released')))] if btn.when_released else None,
    )

    folder.add_item(
        label   = _(_.BTN_OPTION, option=_.BTN_WHEN_HELD, value=btn.when_held),
        path    = plugin.url_for(edit_btn, id=btn.id, method='select_when_held'),
        info    = {'plot': _(_.BTN_WHEN_HELD_DESC, delimiter=FUNCTION_DELIMETER)},
        context = [(_.TEST_HOLD, 'RunPlugin({})'.format(plugin.url_for(test_btn, id=btn.id, method='when_held')))] if btn.when_held else None,
    )

    folder.add_item(
        label = _(_.BTN_OPTION, option=_.BTN_NAME, value=btn.name),
        path  = plugin.url_for(edit_btn, id=btn.id, method='select_name'),
        info  = {'plot': _.BTN_NAME_DESC},
    )

    folder.add_item(
        label = _(_.BTN_OPTION, option=_.BTN_ENABLED, value=btn.enabled),
        path  = plugin.url_for(edit_btn, id=btn.id, method='toggle_enabled'),
        info  = {'plot': _.BTN_ENABLED_DESC},
    )

    folder.add_item(
        label = _(_.BTN_OPTION, option=_.BTN_PULLUP, value=btn.pull_up),
        path  = plugin.url_for(edit_btn, id=btn.id, method='toggle_pull_up'),
        info  = {'plot': _.BTN_PULLUP_DESC},
    )

    folder.add_item(
        label = _(_.BTN_OPTION, option=_.BTN_BOUNCE_TIME, value=btn.bounce_time),
        path  = plugin.url_for(edit_btn, id=btn.id, method='select_bounce_time'),
        info  = {'plot': _.BTN_BOUNCE_TIME_DESC},
    )

    folder.add_item(
        label = _(_.BTN_OPTION, option=_.BTN_HOLD_TIME, value=btn.hold_time),
        path  = plugin.url_for(edit_btn, id=btn.id, method='select_hold_time'),
        info  = {'plot': _.BTN_HOLD_TIME_DESC},
    )

    folder.add_item(
        label = _(_.BTN_OPTION, option=_.BTN_HOLD_REPEAT, value=btn.hold_repeat),
        path  = plugin.url_for(edit_btn, id=btn.id, method='toggle_hold_repeat'),
        info  = {'plot': _.BTN_HOLD_REPEAT_DESC},
    )

    if not settings.getBool(AUTO_RELOAD_SETTING, False):
        folder.add_item(
            label = _.RELOAD_SERVICE,
            path  = plugin.url_for(reload_service),
            info  = {'plot': _.RELOAD_SERVICE_DESC},
        )

    label, desc = btn.status_label()
    folder.add_item(
        label = _(_.BTN_OPTION, option=_.BTN_STATUS, value=label,),
        is_folder = False,
        info  = {'plot': desc},
    )

    return folder

@plugin.route()
def edit_btn(id, method, **kwargs):
    btn = Button.get_by_id(id)
    if getattr(btn, method)():
        btn.save()
        _on_btn_change()

@plugin.route()
def delete_btn(id, **kwargs):
    btn = Button.get_by_id(id)
    if gui.yes_no(_.CONFIRM_DELETE_BTN) and btn.delete_instance():
        _on_btn_change()

@plugin.route()
def reload_service(**kwargs):
    _reload_service()

@plugin.route()
def install_service(**kwargs):
    with gui.progress(_.INSTALL_SERVICE, percent=100) as progress:
        restart_required = gpio.install()

    if restart_required and gui.yes_no(_.RESTART_REQUIRED):
        plugin.reboot()

    gui.refresh()

@plugin.route()
def set_state(pin, state, **kwargs):
    gpio.set_state(pin, state)

def _on_btn_change():
    if settings.getBool(AUTO_RELOAD_SETTING, False):
        _reload_service()

    gui.refresh()

@signals.on(signals.AFTER_RESET)
def _reload_service():
    database.close()

    with gui.progress(_.RELOAD_SERVICE, percent=100) as progress:
        set_kodi_string('_gpio_reload', '1')

        for i in range(5):
            xbmc.sleep(1000)
            if not get_kodi_string('_gpio_reload'):
                break