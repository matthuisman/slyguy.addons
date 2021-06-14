# -*- coding: utf-8 -*-
import sys
import time
from datetime import datetime

is_64bits = sys.maxsize > 2 ** 32
_MAX_TIMESTAMP = (
    time.mktime(datetime(3000, 1, 1, 23, 59, 59, 999999).timetuple())
    if is_64bits
    else time.mktime(datetime(2038, 1, 1, 23, 59, 59, 999999).timetuple())
)

MAX_TIMESTAMP = _MAX_TIMESTAMP
MAX_TIMESTAMP_MS = MAX_TIMESTAMP * 1000
MAX_TIMESTAMP_US = MAX_TIMESTAMP * 1000000
