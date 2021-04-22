import hashlib
import hmac
import datetime

from slyguy import userdata, settings
from slyguy.session import Session
from slyguy.exceptions import Error

from .constants import HEADERS, API_URL, DEFAULT_HOST, PAGE_SIZE
from .language import _

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

    def my_courses(self, page=1, query=None):
        params = {
            'page'            : page,
            'page_size'       : PAGE_SIZE,
            'ordering'        : 'title',
            'fields[course]'  : 'id,title,image_480x270,image_750x422,headline,num_published_lectures,content_info,completion_ratio',
        }

        if query:
            params['search'] = query

        return self._session.get('users/me/subscribed-courses', params=params).json()

    def chapters(self, course_id, page=1):
        params = {
            'page'             : page,
            'page_size'        : PAGE_SIZE,
            'fields[course]'   : 'image_480x270',
            'fields[chapter]'  : 'description,object_index,title,course',
            'fields[lecture]'  : 'id',
            'fields[practice]' : 'id',
            'fields[quiz]'     : 'id',
        }

        data = self._session.get('courses/{}/cached-subscriber-curriculum-items'.format(course_id), params=params).json()
        rows = [r for r in data['results'] if r['_class'] == 'chapter']
        return rows, data['next']

    def lectures(self, course_id, chapter_id, page=1):
        params = {
            'page'             : page,
            'page_size'        : PAGE_SIZE,
            'fields[course]'   : 'image_480x270,title',
            'fields[chapter]'  : 'id',
            'fields[lecture]'  : 'title,object_index,description,is_published,course,id,asset',
            'fields[asset]'    : 'asset_type,length,status',
            'fields[practice]' : 'id',
            'fields[quiz]'     : 'id',
        }

        data = self._session.get('courses/{}/cached-subscriber-curriculum-items'.format(course_id), params=params).json()

        lectures = []
        found = False
        for row in data['results']:
            if not found and row['_class'] == 'chapter' and row['id'] == int(chapter_id):
                found = True

            elif found and row['_class'] == 'lecture' and row['is_published'] and row['asset']['asset_type'] in ('Video', 'Audio'):
                lectures.append(row)

            elif found and row['_class'] == 'chapter':
                break

        return lectures, data['next']

    def get_stream_data(self, asset_id):
        params = {
            'fields[asset]'   : '@all',
        }

        return self._session.get('assets/{0}'.format(asset_id), params=params).json()

    def login(self, username, password):
        data = {
            'email': username,
            'password': password,
            'upow': self._get_upow(username, 'login')
        }

        params = {
            'fields[user]': 'title,image_100x100,name,access_token',
        }

        r = self._session.post('auth/udemy-auth/login/', params=params, data=data)
        try:
            data = r.json()
        except:
            raise APIError(_(_.LOGIN_ERROR, msg=r.status_code))

        access_token = data.get('access_token')
        if not access_token:
            raise APIError(_(_.LOGIN_ERROR, msg=data.get('detail', '')))

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