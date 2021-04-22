from collections import OrderedDict

from bs4 import BeautifulSoup

from slyguy import util, userdata, settings, gui
from slyguy.session import Session
from slyguy.exceptions import Error
from slyguy import mem_cache

from .constants import *
from .language import _

class APIError(Error):
    pass

class API(object):
    def __init__(self):
        self.new_session()

    def new_session(self):
        self.logged_in = True if userdata.get('_cookies') else False
        if not settings.getBool('save_password', False):
            userdata.delete(PASSWORD_KEY)

        if self.logged_in and settings.getBool('save_password', True) and not userdata.get(PASSWORD_KEY):
            self.logout()
            gui.ok(_.SAVE_PASSWORD_RELOGIN)

    def _get(self, url, attempt=1):
        cookies = {'cookie_notice_accepted': 'true'}
        cookies.update(userdata.get('_cookies'))

        r = Session().get(BASE_URL+url, timeout=20, cookies=cookies, headers=HEADERS)

        password = userdata.get(PASSWORD_KEY)
        if 'membersignin' in r.text and password and attempt <= 3:
            self.login(userdata.get('username'), password)
            return self._get(url, attempt=attempt+1)

        if 'membersignin' in r.text:
            raise APIError(_.SESSION_EXPIRED)

        return r

    @mem_cache.cached(RACES_CACHE_TIME)
    def races(self):
        races = OrderedDict()

        r = self._get('superview-videos/')

        if 'Buy now' in r.text:
            raise APIError(_.NOT_PAID)

        elif 'Full Race Replays' not in r.text:
            return races

        split = r.text.split('Full Race Replays')
        upcoming = BeautifulSoup(split[0], 'html.parser')
        replays  = BeautifulSoup(split[1], 'html.parser')

        for elem in upcoming.find_all('span', {'class': 'resultsummary-tabletitle-inner'}):
            race = self._process_race(elem, upcoming=True)
            races[race['slug']] = race

        for elem in reversed(replays.find_all('span', {'class': 'resultsummary-tabletitle-inner'})):
            race = self._process_race(elem)
            if race['slug'] not in races:
                races[race['slug']] = race

        return races

    def _process_race(self, elem, upcoming=False):
        race = {
            'title': elem.get_text(),
            'streams': [],
            'upcoming': upcoming,
        }

        race['slug'] = race['title'].lower().strip().replace(' ', '-')

        rows = elem.parent.find_next_sibling('div', {'class': 'resultsummary-table-wrapper'}).find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 5:
                continue

            elem = cells[4].find('a')

            try:
                slug = elem.attrs['href'].rstrip('/').split('/')[-1]
                live = 'live' in elem.text.lower()
            except:
                slug = None
                live = False

            stream = {
                'label': cells[0].get_text(),
                'date':  cells[1].get_text(),
                'start': cells[2].get_text(),
                'end':   cells[3].get_text(),
                'slug':  slug,
                'live':  live,
            }

            race['streams'].append(stream)

        return race

    def login(self, username, password):
        self.logout()

        s = Session()
        s.headers.update(HEADERS)

        if not password:
            raise APIError(_.LOGIN_ERROR)

        r = s.get(BASE_URL+'superview/', timeout=20)
        soup = BeautifulSoup(r.text, 'html.parser')

        login_form = soup.find(id="membersignin")
        inputs = login_form.find_all('input')

        data = {}
        for elem in inputs:
            if elem.attrs.get('value'):
                data[elem.attrs['name']] = elem.attrs['value']

        data.update({
            'signinusername': username,
            'signinpassword': password,
        })

        r = s.post(BASE_URL+'superview/', data=data, allow_redirects=False, timeout=20)
        if r.status_code != 302:
            raise APIError(_.LOGIN_ERROR)

        if settings.getBool('save_password', False):
            userdata.set(PASSWORD_KEY, password)

        for cookie in r.cookies:
            if cookie.name.startswith('wordpress_logged_in'):
                userdata.set('_cookies', {cookie.name: cookie.value})
                break

    def logout(self):
        userdata.delete(PASSWORD_KEY)
        userdata.delete('expires') #legacy
        userdata.delete('_cookies')

    def play(self, slug):
        r = self._get('superviews/{}/'.format(slug))

        soup = BeautifulSoup(r.text, 'html.parser')

        bc_div = soup.find("div", {"class": "BrightcoveExperience"})
        bc_data = bc_div.find('video')

        bc_accont = bc_data.attrs['data-account']
        referenceID = bc_data.attrs['data-video-id']

        return self.get_brightcove_src(bc_accont, referenceID)

    def get_brightcove_src(self, bc_accont, referenceID):
        headers = {
            'User-Agent': 'Mozilla/5.0 (CrKey armv7l 1.5.16041) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.0 Safari/537.36',
            'Origin': 'https://www.supercars.com',
            'X-Forwarded-For': '18.233.21.73',
            'BCOV-POLICY': BRIGHTCOVE_KEY,
        }

        brightcove_url = BRIGHTCOVE_URL.format(bc_accont, referenceID)
        data = Session().get(brightcove_url, headers=headers).json()
        return util.process_brightcove(data)