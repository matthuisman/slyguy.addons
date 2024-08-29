from slyguy.settings import CommonSettings
from slyguy.settings.types import Bool, Text

from .language import _


class Settings(CommonSettings):
    BUSINESS_ACCOUNT = Bool('business_account', _.BUSINESS_ACCOUNT, default=False)
    BUSINESS_NAME = Text('business_host', _.BUSINESS_NAME, default='business.udemy.com', visible=lambda: Settings.BUSINESS_ACCOUNT.value)


settings = Settings()
