from kodi_six import xbmc

from slyguy import plugin, log
from slyguy.util import kodi_rpc

from .settings import settings


@plugin.route('')
def index(**kwargs):
    plugin.redirect(plugin.url_for(plugin.ROUTE_SETTINGS))


def service():
    monitor = xbmc.Monitor()

    actions = {
        'VideoLibrary.Scan': ['VideoLibrary.GetRecentlyAddedMovies', 'VideoLibrary.GetRecentlyAddedEpisodes'],
        'AudioLibrary.Scan': ['AudioLibrary.GetRecentlyAddedAlbums', 'AudioLibrary.GetRecentlyAddedSongs'],
    }
    prev_latest = {key: {} for key in actions}

    while not monitor.waitForAbort(settings.getInt('poll_time', 10)):
        for update_action in actions:
            if monitor.abortRequested():
                break

            run_update = False
            for recent_action in actions[update_action]:
                if monitor.abortRequested():
                    break

                try:
                    latest = kodi_rpc(recent_action, {'limits': {'start': 0, 'end': 1 }})
                    #log.debug('RPC: "{}": {}'.format(recent_action, latest))
                except Exception as e:
                    log.error('Failed RPC "{}": {}'.format(recent_action, e))
                    continue

                if recent_action in prev_latest[update_action] and prev_latest[update_action][recent_action] != latest:
                    run_update = True

                prev_latest[update_action][recent_action] = latest
                if run_update:
                    break

            if run_update:
                log.info('Detected library change. Running "{}"'.format(update_action))
                kodi_rpc(update_action, {'directory': '/service.recently.added.refresh', 'showdialogs': False})
