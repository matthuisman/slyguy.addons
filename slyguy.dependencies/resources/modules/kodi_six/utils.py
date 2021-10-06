# coding: utf-8
# Created on: 04.01.2018
# Author: Roman Miroshnychenko aka Roman V.M. (roman1972@gmail.com)
"""
Utility functions for string conversion depending on Python version
"""

import sys
import inspect

__all__ = [
    'PY2',
    'py2_encode',
    'py2_decode',
    'encode_decode',
    'patch_object',
    'ModuleWrapper',
]

PY2 = sys.version_info[0] == 2  #: ``True`` for Python 2


def py2_encode(s, encoding='utf-8', errors='strict'):
    """
    Encode Python 2 ``unicode`` to ``str``

    In Python 3 the string is not changed.
    """
    if PY2 and isinstance(s, unicode):
        s = s.encode(encoding, errors)
    return s


def py2_decode(s, encoding='utf-8', errors='strict'):
    """
    Decode Python 2 ``str`` to ``unicode``

    In Python 3 the string is not changed.
    """
    if PY2 and isinstance(s, str):
        s = s.decode(encoding, errors)
    return s


def encode_decode(func):
    """
    A decorator that encodes all unicode function arguments to UTF-8-encoded
    byte strings and decodes function str return value to unicode.

    This decorator is no-op in Python 3.

    :param func: wrapped function or a method
    :type func: types.FunctionType or types.MethodType
    :return: function wrapper
    :rtype: types.FunctionType
    """
    if PY2:
        def wrapper(*args, **kwargs):
            mod_args = tuple(py2_encode(item) for item in args)
            mod_kwargs = {key: py2_encode(value) for key, value
                          in kwargs.iteritems()}
            return py2_decode(func(*mod_args, **mod_kwargs),
                              errors='replace')
        #wrapper.__name__ = 'wrapped_func_{0}'.format(func.__name__)
        return wrapper
    return func


def _wrap_class(cls):
    class ClassWrapper(cls):
        pass
    #ClassWrapper.__name__ = 'wrapped_class_{0}'.format(cls.__name__)
    return ClassWrapper


def patch_object(obj):
    """
    Applies func:`encode_decode` decorator to an object

    :param obj: object for patching
    :return: patched object
    """
    if inspect.isbuiltin(obj):
        obj = encode_decode(obj)
    elif inspect.isclass(obj):
        # We cannot patch methods of Kodi classes directly.
        obj = _wrap_class(obj)
        for memb_name, member in inspect.getmembers(obj):
            # Do not patch special methods!
            if (inspect.ismethoddescriptor(member) and
                    not memb_name.endswith('__')):
                setattr(obj, memb_name, encode_decode(member))
    return obj


class ModuleWrapper(object):
    """
    Implements lazy patching of Kodi Python API modules

    This class applies func:`encode_decode` decorator to Kodi API functions
    and classes on demand when a function or a class is first used.
    """
    def __init__(self, base_module):
        self._base_module = base_module

    def __getattr__(self, item):
        if not hasattr(self._base_module, item):
            raise AttributeError(
                'Module {0} does not have attribute "{1}"!'.format(
                    self._base_module, item
                )
            )
        obj = getattr(self._base_module, item)
        obj = patch_object(obj)
        setattr(self, item, obj)
        return obj
