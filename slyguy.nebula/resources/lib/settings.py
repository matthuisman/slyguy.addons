from slyguy.settings import CommonSettings


HEADERS = {
    'user-agent': 'Dalvik/2.1.0 (Zype Android; Linux; U; Android 5.0.2; One X Build/LRX22G)',
}

BASE_URL = 'https://content.watchnebula.com{}'
PAGE_SIZE = 50


class Settings(CommonSettings):
    pass


settings = Settings()
