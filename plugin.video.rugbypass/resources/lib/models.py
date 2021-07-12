import arrow
import peewee

from slyguy import database, settings

from .constants import IMG_URL
from .language import _

class Game(database.Model):
    FULL = 1
    CONDENSED = 8

    UPCOMING = 0   #Not yet played
    LIVE = 1       #Live
    PROCESSING = 2 #Can re-watch entire live stream
    PLAYED = 3     #Can watch full and condensend game

    id     = peewee.IntegerField(primary_key=True)
    slug   = peewee.TextField(unique=True, index=True)
    state  = peewee.IntegerField(index=True)
    start  = peewee.IntegerField()
    end    = peewee.IntegerField()
    info   = database.JSONField()

    @property
    def result(self):
        home = self.info['home']
        away = self.info['away']

        if home['score'] == '' or away['score'] == '':
            return None
        if int(home['score']) == int(away['score']):
            return _(_.A_DRAW, win_team=home['name'], win_score=home['score'], lose_team=away['name'], lose_score=away['score'])
        elif int(home['score']) > int(away['score']):
            return _(_.X_WINS, win_team=home['name'], win_score=home['score'], lose_team=away['name'], lose_score=away['score'])
        else:
            return _(_.X_WINS, win_team=away['name'], win_score=away['score'], lose_team=home['name'], lose_score=home['score'])

    @property
    def aired(self):
        return arrow.get(self.start).to('local').isoformat()

    @property
    def description(self):
        home = self.info['home']
        away = self.info['away']
        show_hours = settings.getInt('show_hours') if settings.getBool('show_score') else -1

        result = ''
        if home['score'] and away['score'] and show_hours != -1 and arrow.now() > arrow.get(self.start).shift(hours=show_hours):
            result = self.result

        return _(_.GAME_DESC, home_team=home['name'], away_team=away['name'], kick_off=self.kickoff, result=result)

    @property
    def kickoff(self):
        return _(_.KICK_OFF, date_time=arrow.get(self.start).to('local').format('h:mmA D/M/YY'))

    @property
    def duration(self):
        if self.end == 0: 
            return None
        return self.end - self.start

    @property
    def playable(self):
        return self.state in (Game.LIVE, Game.PROCESSING, Game.PLAYED)

    @property
    def title(self):
        return _(_.GAME_TITLE, home_team=self.info['home']['name'], away_team=self.info['away']['name'])

    @property
    def image(self):
        return IMG_URL.format('/teams/{}_ph_eb.png'.format(self.info['home']['code']))

database.tables.append(Game)