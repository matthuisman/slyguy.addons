# coding: utf-8
# Created on: 04.01.2018
# Author: Roman Miroshnychenko aka Roman V.M. (roman1972@gmail.com)
"""
Functions and classes to work with files and folders
"""

from __future__ import absolute_import
import sys as _sys
from .utils import PY2 as _PY2, ModuleWrapper as _ModuleWrapper

if _PY2:
    import xbmcvfs as _xbmcvfs
    _wrapped_xbmcvfs = _ModuleWrapper(_xbmcvfs)
    _sys.modules[__name__] = _wrapped_xbmcvfs
else:
    from xbmcvfs import *
