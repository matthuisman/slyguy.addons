import hashlib

import arrow

from slyguy import userdata
from slyguy.session import Session
from slyguy.exceptions import Error

from .language import _
from .constants import *

class APIError(Error):
    pass

class API(object):
    def new_session(self):
        self._session = Session(HEADERS, base_url=API_URL)
        self.logged_in = userdata.get('nllinktoken') != None

    def login(self, username, password):
        self.logout()
        
        data = {
            'username': username,
            'password': password,
            'cookielink': 'true',
            'format': 'json',
        }

        r = self._session.post('/secure/authenticate', data=data)

        data = r.json()
        nllinktoken = r.cookies.get_dict().pop('nllinktoken', None)
        code = data.get('code') or _.UNKNOWN_ERROR

        if code != 'loginsuccess' or not nllinktoken:
            if code == 'failedgeo':
                raise APIError(_.GEO_ERROR)
            else:
                raise APIError(_(_.LOGIN_ERROR, code=code))

        userdata.set('nllinktoken', nllinktoken)
        self.new_session()

    def deviceid(self):
        return hashlib.sha1(userdata.get('username').encode('utf8')).hexdigest()[:8]

    def play(self, media_id, media_type, start=None, duration=None):
        payload = {
            'id': media_id,
            'nt': 1,
            'type': media_type,
            'format': 'json',
            'drmtoken': True,
            'deviceid': self.deviceid(),
        }

        if start:
            payload['st'] = '{}000'.format(start)

        if duration:
            payload['dur'] = '{}000'.format(duration)

        login_cookies = {'nllinktoken': userdata.get('nllinktoken'), 'UserName': userdata.get('username')}
        data = self._session.post('/service/publishpoint', data=payload, cookies=login_cookies).json()
        
        if 'path' not in data:
            code = data.get('code') or _.UNKNOWN_ERROR
            if code == 'failedgeo':
                raise APIError(_.GEO_ERROR)
            else:
                raise APIError(_(_.PLAYBACK_ERROR, code=code))

        return data

    def schedule(self, date):
        schedule = []

        data = self._session.get(SCHEDULE_URL.format(date=date.format('YYYY/MM/DD'))).json()
        for channel in data:
            for event in channel['items']:
                start     = arrow.get(event['su'])
                stop      = start.shift(seconds=event['ds'])
                duration  = int(event['ds'])
                title     = event.get('e')
                desc      = event.get('ed')
                schedule.append({'channel': channel['channelId'], 'start': start, 'stop': stop, 'duration': duration, 'title': title, 'desc': desc})

        return sorted(schedule, key=lambda channel: channel['start'])

    def logout(self):
        # self._session.post('service/logout', data={'format': 'json'})
        userdata.delete('nllinktoken')
        self.new_session()

    def highlights(self, page=1, pagesize=100):
        params = {
            'type': '0',
            'format': 'json',
            'ps': pagesize,
            'pn': page,
        }

        data = self._session.get('/service/search', params=params).json()
        
        try:
            code = data.get('code')
        except:
            code = None

        if code:
            if code == 'failedgeo':
                raise APIError(_.GEO_ERROR)
            else:
                raise APIError(_(_.PLAYBACK_ERROR, code=code or _.UNKNOWN_ERROR))

        return data

    def channels(self):
        params = {
            'format': 'json',
        }

        data = self._session.get('/channels', params=params).json()

        try:
            code = data.get('code')
        except:
            code = None

        if code:
            if code == 'failedgeo':
                raise APIError(_.GEO_ERROR)
            else:
                raise APIError(_(_.PLAYBACK_ERROR, code=code or _.UNKNOWN_ERROR))

        return data