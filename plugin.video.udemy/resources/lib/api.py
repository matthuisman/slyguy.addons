import hashlib
import hmac
import datetime

from slyguy import userdata
from slyguy.session import Session
from slyguy.exceptions import Error

from .constants import HEADERS, API_URL, DEFAULT_HOST, PAGE_SIZE, MAX_PAGE_SIZE
from .language import _
from .settings import settings


class APIError(Error):
    pass


class API(object):
    def new_session(self):
        self.logged_in = False

        host = settings.get('business_host') if settings.getBool('business_account', False) else DEFAULT_HOST
        if host != userdata.get('host', DEFAULT_HOST):
            userdata.delete('access_token')
            userdata.set('host', host)

        self._session = Session(HEADERS, base_url=API_URL.format(host))
        self._set_authentication()

    def _set_authentication(self):
        token = userdata.get('access_token')
        if not token:
            return

        self._session.headers.update({'Authorization': 'Bearer {}'.format(token)})
        self.logged_in = True

    def search(self, query, page=1):
        params = {
            'p': page,
            'subs_filter_type': 'subs_only', #purchasable_only
            'skip_price': True,
            'q': query,
        }
        return self._session.get('search-courses/', params=params, headers={'referer':'https://www.udemy.com/courses/search/'}).json()

    def collections(self):
        return self._session.get('users/me/subscribed-courses-collections/').json()

    def add_collection_course(self, list_id, course_id):
        payload = {
            'course': course_id,
        }
        return self._session.post('users/me/subscribed-courses-collections/{}/courses/'.format(list_id), json=payload).ok

    def del_collection_course(self, list_id, course_id):
        return self._session.delete('users/me/subscribed-courses-collections/{}/courses/{}/'.format(list_id, course_id)).ok

    def collection(self, list_id, page=1):
        params = {
            'page': page,
            'page_size': PAGE_SIZE,
            'fields[user_has_subscribed_courses_collection]': '@all',
            'course_limit': 0,
            'fields[course]': 'id,title,image_480x270,image_750x422,headline',
        }
        return self._session.get('users/me/subscribed-courses-collections/{}/courses/'.format(list_id), params=params).json()

    def purchased(self, page=1):
        params = {
            'page': page,
            'page_size': PAGE_SIZE,
            'fields[course]': 'id,title,image_480x270,image_750x422,headline',
        }
        return self._session.get('users/me/subscribed-courses/', params=params).json()

    def chapters(self, course_id, page=1):
        params = {
            'page': page,
            'page_size': MAX_PAGE_SIZE,
            'fields[course]': 'image_480x270',
            'fields[chapter]': 'description,object_index,title,course,lecture',
            'fields[lecture]': 'id,asset,is_published',
            'fields[practice]': 'id',
            'fields[quiz]': 'id',
        }

        r = self._session.get('courses/{}/subscriber-curriculum-items/'.format(course_id), params=params)
        data = r.json()
        if not r.ok:
            raise APIError(data.get('detail'))

        chapters = []
        chapter = None
        for row in data['results']:
            if row['_class'] == 'chapter':
                chapter = row
                chapter['lectures'] = []

            elif chapter and row['_class'] == 'lecture' and row['is_published'] and row['asset']['asset_type'] in ('Video', 'Audio'):
                chapter['lectures'].append(row)
                if chapter not in chapters:
                    chapters.append(chapter)

        return chapters, data['next']

    def lectures(self, course_id, page=1):
        params = {
            'page': page,
            'page_size': MAX_PAGE_SIZE,
            'fields[course]': 'image_480x270,title',
            'fields[chapter]': 'id,title,object_index',
            'fields[lecture]': 'title,object_index,description,is_published,course,id,asset',
            'fields[asset]': 'asset_type,length,status',
            'fields[practice]': 'id',
            'fields[quiz]': 'id',
        }

        r = self._session.get('courses/{}/subscriber-curriculum-items/'.format(course_id), params=params)
        data = r.json()
        if not r.ok:
            raise APIError(data.get('detail'))

        lectures = []
        chapter = None
        for row in data['results']:
            if row['_class'] == 'chapter':
                chapter = row

            elif chapter and row['_class'] == 'lecture' and row['is_published'] and row['asset']['asset_type'] in ('Video', 'Audio'):
                row['chapter'] = chapter
                lectures.append(row)

        return lectures, data['next']

    def get_stream_data(self, asset_id):
        params = {
            'fields[asset]': 'asset_type,length,media_license_token,course_is_drmed,media_sources,captions,thumbnail_sprite,slides,slide_urls,download_urls,external_url',
        }

        data = self._session.get('assets/{}'.format(asset_id), params=params).json()
        if 'detail' in data:
            raise APIError(data['detail'])

        return data

    def login(self, username, password):
        data = {
            'email': username,
            'password': password,
            'upow': self._get_upow(username, 'login')
        }

        params = {
            'fields[user]': 'title,image_100x100,name,access_token',
        }

        r = self._session.post('auth/udemy-auth/login/3.0/', params=params, data=data)
        try:
            data = r.json()
        except:
            raise APIError(_(_.LOGIN_ERROR, msg=r.status_code))

        access_token = data.get('access_token')
        if not access_token:
            raise APIError(_(_.LOGIN_ERROR, msg=data.get('error_message', '')))

        userdata.set('access_token', access_token)
        self._set_authentication()

    def logout(self):
        userdata.delete('access_token')
        self.new_session()

    def _get_upow(self, message, secret):
        date = datetime.datetime.today().strftime('%Y%m%d')

        def get_token(email, date, secret):
            message = email + date
            i = 0

            for x in range(0, 20):
                i3 = i * 50

                while True:
                    i2 = i + 1
                    if i3 >= i2 * 50:
                        break

                    i4 = i3 * 1000
                    i3 += 1
                    token = hash_calc(i4, i3 * 1000, message, secret)
                    if token:
                        return token

                i = i2

            return None

        def m26785a(i):
            f19175e = ""
            while i >= 0:
                f19175e += chr(((i % 26) + 65))
                i = int(i / 26) - 1
            return f19175e[::-1]

        def hash_calc(i, i2, message, password):
            a = m26785a(i)
            _bytes = bytearray(message + a, 'utf8')
            password = password.encode()

            while i < i2:
                _i = i
                if (_i % 26 == 0):
                    _bytes = bytearray(message + m26785a(_i), 'utf8')
                else:
                    _bytes[len(_bytes) - 1] = (_bytes[len(_bytes) - 1] + 1)

                doFinal = hmac.new(password, _bytes, digestmod=hashlib.sha256).hexdigest()
                if doFinal[0:2] == '00' and doFinal[2:4] == '00':
                    return m26785a(i)

                i += 1

            return None

        return date + get_token(message, date, secret)
