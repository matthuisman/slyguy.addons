from slyguy.settings import CommonSettings
from slyguy.settings.types import Bool, Enum
from slyguy.constants import *

from .language import _


class State:
    AUTO = ''
    NSW = 'nsw'
    VIC = 'vic'
    QLD = 'qld'
    WA = 'wa'
    SA = 'sa'

STATES = ['', 'nsw', 'vic', 'qld', 'wa', 'sa']


class Settings(CommonSettings):
    STATE = Enum('state', _.STATE, default=State.AUTO,
        options=[[_.AUTO, State.AUTO], [_.NSW, State.NSW], [_.VIC, State.VIC], [_.QLD, State.QLD], [_.WA, State.WA], [_.SA, State.SA]])
    FLATTEN_SINGLE_SEASON = Bool('flatten_single_season', _.FLATTEN_SEASONS, default=True)
    HIDE_EXTRAS = Bool('hide_extras', _.HIDE_EXTRAS, default=False)


settings = Settings()
