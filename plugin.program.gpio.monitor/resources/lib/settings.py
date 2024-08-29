from slyguy.settings import CommonSettings
from slyguy.settings.types import Bool, Action

from .language import _


class Settings(CommonSettings):
    AUTO_RELOAD_SERVICE = Bool('auto_reload', _.AUTO_RELOAD_SERVICE, default=True)
    INSTALL_SERVICE = Action('RunPlugin(plugin://$ID/?_=install_service)', _.INSTALL_SERVICE)


settings = Settings()
