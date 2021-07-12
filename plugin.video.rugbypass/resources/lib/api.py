import arrow

from slyguy import settings, userdata
from slyguy.session import Session
from slyguy.exceptions import Error
from slyguy.language import _

from .constants import HEADERS, API_URL
from .models import Game
from .language import _

class APIError(Error):
    pass

class API(object):
    def new_session(self):
        self._session = Session(HEADERS, base_url=API_URL)
        self.logged_in = userdata.get('token') != None

    def login(self, username, password):
        data = {
            'username': username,
            'password': password,
            'cookielink': 'true',
            'format': 'json',
        }

        r     = self._session.post('/secure/authenticate', data=data)
        data  = r.json()
        token = r.cookies.get('nllinktoken')

        if not token:
            raise APIError(data.get('code'))

        userdata.set('token', token)

    def get_play_url(self, game, game_type):
        params = {
            'id': game.id,
            'gs': game.state,
            'gt': game_type,
            'type': 'game',
            'format': 'json',
        }

        if game.state == Game.PROCESSING:
            params['st']  = game.start * 1000
            params['dur'] = game.duration * 1000

        cookies = {'nllinktoken': userdata.get('token'), 'RugbyLoggedIn': userdata.get('username')}

        resp = self._session.get('/service/publishpoint', params=params, cookies=cookies)
        if not resp.ok:
            data = self._session.get('/game/{}'.format(game.slug), params={'format':'json', 'purchases': True}, cookies=cookies).json()
            if data.get('noAccess'):
                raise APIError(_.NO_ACCESS)
            elif 'blackout' in data:
                raise APIError(_.GEO_ERROR, heading=_.GEO_HEADING)
            else:
                raise APIError(_.PLAY_ERROR)

        return resp.json()['path']

    def _parse_game(self, item):
        def get_timestamp(key):
            if key in item:
                return arrow.get(item[key]).timestamp
            else:
                return 0

        info = {'home': item['homeTeam'], 'away': item['awayTeam']}
        game = Game(id=int(item['id']), state=int(item['gameState']), start=get_timestamp('dateTimeGMT'), 
                end=get_timestamp('endDateTimeGMT'), slug=str(item['seoName']), info=info)

        return game

    def update_games(self):
        to_create = []

        data = self._session.get('/scoreboard', params={'format':'json'}).json()
        if 'games' not in data:
            if data.get('code') == 'failedgeo':
                raise APIError(_.GEO_ERROR, heading=_.GEO_HEADING)
            else:
                raise APIError(_.GAMES_ERROR)

        for row in data['games']:
            game = self._parse_game(row)
            to_create.append(game)

        Game.truncate()
        Game.bulk_create(to_create, batch_size=100)

    def fetch_game(self, slug):
        data = self._session.get('/game/{}'.format(slug), params={'format':'json'}).json()
        return self._parse_game(data)

    def channels(self):
        return self._session.get('/channels', params={'format':'json'}).json()

    def search(self, cat_id, query, page=1):
        params = {
            'param': '*{}*'.format(query), 
            'fq': 'catId2:{}'.format(cat_id), 
            'pn': page,
            'format':'json',
        }

        return self._session.get('/search', params=params).json()

    def logout(self):
        userdata.delete('token')
        self.new_session()
