from slyguy.settings import CommonSettings
from slyguy.settings.types import Bool, Enum
from slyguy.constants import *

from .language import _


class Region:
    NSW = 'nsw'
    VIC = 'vic'
    QLD = 'qld'
    SA = 'sa'
    ACT = 'act'
    NT = 'nt'
    WA = 'wa'
    TAS = 'tas'
    GCQ = 'gold-coast'
    NLM = 'lismore' # Norther Rivers
    NEW = 'newcastle'


class Settings(CommonSettings):
    REGION = Enum('region', _.REGION, default=Region.NSW,
                    options=[[_.NSW, Region.NSW], [_.VIC, Region.VIC], [_.QLD, Region.QLD], [_.SA, Region.SA],
                        [_.ACT, Region.ACT], [_.NT, Region.NT], [_.WA, Region.WA], [_.TAS, Region.TAS], [_.GCQ, Region.GCQ],
                        [_.NLM, Region.NLM], [_.NEW, Region.NEW]])
    FLATTEN_SINGLE_SEASON = Bool('flatten_single_season', _.FLATTEN_SINGLE_SEASON, default=True)
    HIDE_SUGGESTED = Bool('hide_suggested', _.HIDE_SUGGESTED, default=False)


settings = Settings()
