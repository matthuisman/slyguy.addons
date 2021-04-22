# coding: utf-8
# Created on: 04.01.2018
# Author: Roman Miroshnychenko aka Roman V.M. (roman1972@gmail.com)
"""
Functions to create media contents plugins
"""

from __future__ import absolute_import
import sys as _sys
from .utils import PY2 as _PY2, ModuleWrapper as _ModuleWrapper

if _PY2:
    import xbmcplugin as _xbmcplugin
    _wrapped_xbmcplugin = _ModuleWrapper(_xbmcplugin)
    _sys.modules[__name__] = _wrapped_xbmcplugin
else:
    from xbmcplugin import *
