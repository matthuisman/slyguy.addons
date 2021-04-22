from slyguy import userdata, settings
from slyguy.session import Session
from slyguy.exceptions import Error

from .constants import HEADERS
from .language import _

class APIError(Error):
    pass

class API(object):
    def new_session(self):
        self.logged_in = False

        self._session = Session(HEADERS)
        self.set_authentication()

    def set_authentication(self):
        ob_session = userdata.get('ob_session')
        if not ob_session:
            return

        self._session.headers.update({'X-OB-Channel': 'I', 'X-OB-SESSION': ob_session})

        self._session.cookies.clear()
        self._session.cookies.update({'OB-SESSION': ob_session, 'OB-PERSIST': '1'})

        self.logged_in = True

    def login(self, username, password):
        self.logout()

        data = {
            "username": username,
            "password": password
        }

        r = self._session.post('https://auth.tab.co.nz/identity-service/api/v1/assertion/by-credentials', json=data)

        if r.status_code == 403:
            raise APIError(_.GEO_ERROR)
        elif r.status_code != 201:
            raise APIError(_.LOGIN_ERROR)

        userdata.set('ob_session', self._session.cookies['OB-SESSION'])

        if settings.getBool('save_password', False):
            userdata.set('pswd', password)
        else:
            userdata.set('ob_tgt', self._session.cookies['OB-TGT'])

        self.set_authentication()

        return r.json()['data']['ticket']

    def _set_ob_token(self):
        password = userdata.get('pswd')
        
        if password:
            ticket = self.login(userdata.get('username'), password)
        else:
            resp = self._session.post('https://auth.tab.co.nz/identity-service/api/v1/assertion/by-token', cookies={'OB-TGT': userdata.get('ob_tgt')})
            
            if resp.status_code == 403:
                raise APIError(_.GEO_ERROR)
            elif resp.status_code != 201:
                raise APIError(_.AUTH_ERROR)
            else:
                ticket = resp.json()['data']['ticket']

        resp = self._session.get('https://api.tab.co.nz/account-service/api/v1/account/header', headers={'Authentication': ticket})

        if 'OB-TOKEN' not in self._session.cookies:
            raise APIError(_.AUTH_ERROR)

        userdata.set('ob_session', self._session.cookies['OB-SESSION'])

    def access(self, type, id):
        self._set_ob_token()

        url = 'https://api.tab.co.nz/sports-service/api/v1/streams/access/{}/{}'.format(type, id)
        r   = self._session.post(url)

        if r.status_code == 403:
            raise APIError(_.GEO_ERROR)

        data = r.json()

        if data['errors']:
            raise APIError(data['errors'][0]['text'])

        return data['data'][0]['streams'][0]['accessInfo']['contentUrl']

    def live_events(self):
        r = self._session.get('https://content.tab.co.nz/content-service/api/v1/q/event-list?liveNow=true&hasLiveStream=true')

        if r.status_code == 403:
            raise APIError(_.GEO_ERROR)

        return r.json()['data']['events']

    def logout(self):
        userdata.delete('ob_session')
        userdata.delete('ob_tgt')
        self.new_session()