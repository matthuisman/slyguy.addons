# coding: utf-8
# Created on: 04.01.2018
# Author: Roman Miroshnychenko aka Roman V.M. (roman1972@gmail.com)
"""
Wrappers around Kodi Python API that normalize byte and Unicode string handling
"""

from __future__ import absolute_import
from .utils import PY2, py2_encode, py2_decode, encode_decode

__all__ = ['PY2', 'py2_encode', 'py2_decode', 'encode_decode']
