from slyguy import mem_cache
from slyguy.settings import CommonSettings
from slyguy.settings.types import Bool, Enum
from slyguy.constants import *

from .language import _


class Region:
    AUTO = 0 # Find by IP
    MEL = 26 # Melbourne
    SYD = 4 # Sydney
    BRI = 27 # Brisbane
    PER = 29 # Perth
    ADE = 28 # Adelaide
    CNS = 5 # Cairns
    MKY = 6 # Mackay
    SSC = 7 # Sunshine Coast
    RKY = 8 # Rockhampton
    TWB = 9 # Toowoomba
    TSV = 10 # Townsville
    WBY = 32 # Wide Bay


class Settings(CommonSettings):
    FLATTEN_SINGLE_SEASON = Bool('flatten_single_season', _.FLATTEN_SINGLE_SEASON, default=True)
    HIDE_SUGGESTED = Bool('hide_suggested', _.HIDE_SUGGESTED, default=False)
    HIDE_CLIPS = Bool('hide_clips', _.HIDE_CLIPS, default=False)
    REGION = Enum('region', _.REGION, default=Region.AUTO,
                    options=[[_.AUTO, Region.AUTO], [_.MEL, Region.MEL], [_.SYD, Region.SYD], [_.BRI, Region.BRI],
                        [_.PER, Region.PER], [_.ADE, Region.ADE], [_.CNS, Region.CNS], [_.MKY, Region.MKY], [_.SSC, Region.SSC],
                        [_.RKY, Region.RKY], [_.TWB, Region.TWB], [_.TSV, Region.TSV], [_.WBY, Region.WBY]])


settings = Settings()
