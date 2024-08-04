from slyguy.settings import CommonSettings
from slyguy.settings.types import Bool

from .language import _


class Settings(CommonSettings):
    HIDE_PUBLIC = Bool('hide_public', _.HIDE_PUBLIC, default=False)
    HIDE_CUSTOM = Bool('hide_custom', _.HIDE_CUSTOM, default=False)
    HIDE_MY_CHANNELS = Bool('hide_my_channels', _.HIDE_MY_CHANNELS, default=False)
    STREMIUM_FAVORITES = Bool('stremium_favourites', _.STREMIUM_FAVORITES, default=False)
    REMOVE_NUMBERS = Bool('remove_numbers', _.REMOVE_NUMBERS, default=True)
    SHOW_PROVIDERS = Bool('show_providers', _.SHOW_PROVIDERS, default=True)


settings = Settings()
