# coding: utf-8
# Created on: 20.01.2019
# Author: Roman Miroshnychenko aka Roman V.M. (roman1972@gmail.com)
"""
A class for working with DRM
"""

from __future__ import absolute_import
import sys as _sys
from .utils import PY2 as _PY2, ModuleWrapper as _ModuleWrapper

if _PY2:
    import xbmcdrm as _xbmcdrm
    _wrapped_xbmcdrm = _ModuleWrapper(_xbmcdrm)
    _sys.modules[__name__] = _wrapped_xbmcdrm
else:
    from xbmcdrm import *
