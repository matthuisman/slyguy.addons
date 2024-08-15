import sys
import traceback
from contextlib import contextmanager

from kodi_six import xbmcgui, xbmc

from slyguy import _
from slyguy.util import get_system_arch
from slyguy.constants import *


def make_heading(heading=None):
    return heading if heading else ADDON_NAME


def exception(heading=None):
    if not heading:
        system, arch = get_system_arch()
        heading = '{addon_name} ({addon_version}/{common_version}) ({kodi_version} {system} {arch})'.format(
            addon_name = ADDON_NAME,
            addon_version = ADDON_VERSION,
            common_version = COMMON_ADDON.getAddonInfo('version'),
            kodi_version = xbmc.getInfoLabel('System.BuildVersion').split(' ')[0],
            system = system,
            arch = arch
        )
        heading = u'{} - {}'.format(heading, _.UNEXPECTED_ERROR)

    exc_type, exc_value, exc_traceback = sys.exc_info()

    tb = []

    include = [ADDON_ID,  os.path.join(COMMON_ADDON_ID, 'resources', 'modules', 'slyguy'), os.path.join(COMMON_ADDON_ID, 'resources', 'lib')]
    fline = True
    for trace in reversed(traceback.extract_tb(exc_traceback)):
        trace = list(trace)
        if fline:
            trace[0] = os.path.basename(trace[0])
            tb.append(trace)
            fline = False
            continue

        for _id in include:
            if _id in trace[0]:
                trace[0] = os.path.basename(trace[0])
                tb.append(trace)

    error = '{}\n{}'.format(''.join(traceback.format_exception_only(exc_type, exc_value)), ''.join(traceback.format_list(tb)))
    text(error, heading=heading)


class Progress(object):
    def __init__(self, message='', heading=None, percent=0, background=False):
        heading = make_heading(heading)
        self._background = background

        if self._background:
            self._dialog = xbmcgui.DialogProgressBG()
        else:
            self._dialog = xbmcgui.DialogProgress()

        self._dialog.create(heading, *self._get_args(message))
        self.update(percent)

    def update(self, percent=0, message=None):
        self._dialog.update(int(percent), *self._get_args(message))

    def _get_args(self, message):
        if self._background or message is None or KODI_VERSION > 18:
            args = [message]
        else:
            args = message.split('\n')[:3]
            while len(args) < 3:
                args.append(' ')

        return args

    def iscanceled(self):
        if self._background:
            return self._dialog.isFinished()
        else:
            return self._dialog.iscanceled()

    def close(self):
        self._dialog.close()


def progressbg(message='', heading=None, percent=0):
    heading = make_heading(heading)

    dialog = xbmcgui.DialogProgressBG()
    dialog.create(heading, message)
    dialog.update(int(percent))

    return dialog


@contextmanager
def busy():
    xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
    try:
        yield
    finally:
        xbmc.executebuiltin('Dialog.Close(busydialognocancel)')


@contextmanager
def progress(message='', heading=None, percent=0, background=False):
    dialog = Progress(message=message, heading=heading, percent=percent, background=background)

    try:
        yield dialog
    finally:
        dialog.close()


def input(message, default='', hide_input=False, **kwargs):
    if hide_input:
        kwargs['option'] = xbmcgui.ALPHANUM_HIDE_INPUT

    return xbmcgui.Dialog().input(message, default, **kwargs)


def numeric(message, default='', type=0, **kwargs):
    try:
        return int(xbmcgui.Dialog().numeric(type, message, defaultt=str(default), **kwargs))
    except:
        return None


def error(message, heading=None):
    heading = heading or _(_.PLUGIN_ERROR, addon=ADDON_NAME)
    return ok(message, heading)


def ok(message, heading=None):
    heading = make_heading(heading)
    return xbmcgui.Dialog().ok(heading, message)


def text(message, heading=None, **kwargs):
    heading = make_heading(heading)
    return xbmcgui.Dialog().textviewer(heading, message)


def yes_no(message, heading=None, autoclose=None, **kwargs):
    heading = make_heading(heading)

    if autoclose:
        kwargs['autoclose'] = autoclose

    return xbmcgui.Dialog().yesno(heading, message, **kwargs)


def info(item):
    #playing python path via info dialog fixed in 19
    if KODI_VERSION < 19:
        item.path = None
    dialog = xbmcgui.Dialog()
    dialog.info(item.get_li())


def context_menu(options):
    if KODI_VERSION < 17:
        return select(options=options)

    dialog = xbmcgui.Dialog()
    return dialog.contextmenu(options)
