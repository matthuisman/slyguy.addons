from slyguy.settings import CommonSettings
from slyguy.settings.types import Bool, Text

from .language import _


class Settings(CommonSettings):
    FUNCTION = Text('function', _.FUNCTION, default='Reboot')
    SILENT = Bool('silent', _.SILENT, default=False)


settings = Settings()
