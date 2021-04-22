import time

from slyguy.session import Session
from slyguy.log import log
from slyguy.mem_cache import cached

from .constants import *

class API(object):
    def new_session(self):
        self._session = Session(HEADERS)

    @cached(60*10)
    def all_stations(self):
        return self._session.gz_json(STATIONS_URL)