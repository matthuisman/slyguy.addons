# coding: utf-8
# Created on: 04.01.2018
# Author: Roman Miroshnychenko aka Roman V.M. (roman1972@gmail.com)
"""
A class for accessing addon properties
"""

from __future__ import absolute_import
import sys as _sys
from .utils import PY2 as _PY2, ModuleWrapper as _ModuleWrapper

if _PY2:
    import xbmcaddon as _xbmcaddon
    _wrapped_xbmcaddon = _ModuleWrapper(_xbmcaddon)
    _sys.modules[__name__] = _wrapped_xbmcaddon
else:
    from xbmcaddon import *
