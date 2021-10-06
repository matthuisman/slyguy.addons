# coding: utf-8
# Created on: 04.01.2018
# Author: Roman Miroshnychenko aka Roman V.M. (roman1972@gmail.com)
"""
General classes and functions for interacting with Kodi
"""

from __future__ import absolute_import
import sys as _sys
from .utils import PY2 as _PY2, ModuleWrapper as _ModuleWrapper

if _PY2:
    import xbmc as _xbmc
    _wrapped_xbmc = _ModuleWrapper(_xbmc)
    _sys.modules[__name__] = _wrapped_xbmc
else:
    from xbmc import *

    try:
        from xbmcvfs import translatePath as newTranslatePath
        translatePath = newTranslatePath
    except ImportError:
        pass