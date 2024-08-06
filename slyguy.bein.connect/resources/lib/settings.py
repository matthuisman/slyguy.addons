from slyguy.settings import CommonSettings
from slyguy.settings.types import Enum
from slyguy.constants import *

from .language import _


class Login:
    MULTI_IP = 'multi_ip'
    MULTI_DEVICE = 'multi_device'
    PASSWORD = 'password'


class Settings(CommonSettings):
    LOGIN_TYPE = Enum('login_type', _.LOGIN_TYPE, default=Login.MULTI_IP,
                    options=[[_.LOGIN_MULTI_IP, Login.MULTI_IP], [_.LOGIN_MULTI_DEVICE, Login.MULTI_DEVICE], [_.LOGIN_PASSWORD, Login.PASSWORD]])


settings = Settings()
