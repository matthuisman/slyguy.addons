import os
import threading
import socket

from six.moves.BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from six.moves.socketserver import ThreadingMixIn
from six.moves.urllib.parse import unquote_plus

from kodi_six import xbmcvfs

from slyguy.log import log
from slyguy import router, userdata, settings
from slyguy.constants import CHUNK_SIZE
from slyguy.util import check_port

HOST = '0.0.0.0'
DEFAULT_PORT = 52104

PLAYLIST_URL = 'playlist.m3u8'
EPG_URL = 'epg.xml'

class RequestHandler(BaseHTTPRequestHandler):
    def __init__(self, request, client_address, server):
        try: BaseHTTPRequestHandler.__init__(self, request, client_address, server)
        except (IOError, OSError) as e: pass

    def log_message(self, format, *args):
        return

    def do_GET(self):
        if self.path.lower() == '/'+PLAYLIST_URL.lower():
            path = router.url_for('run_merge', type='playlist', refresh=int(settings.getBool('http_force_merge', True)))
            content_type = 'application/vnd.apple.mpegurl'
        elif self.path.lower() == '/'+EPG_URL.lower():
            path = router.url_for('run_merge', type='epg', refresh=int(settings.getBool('http_force_merge', True)))
            content_type = 'text/xml'
        else:
            return

        log.debug('PLUGIN REQUEST: {}'.format(path))
        dirs, files = xbmcvfs.listdir(path)
        result, msg = int(files[0][0]), unquote_plus(files[0][1:])
        if not result:
            raise Exception(msg)

        if not os.path.exists(msg):
            raise Exception('File not found: {}'.format(msg))

        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.end_headers()

        with open(msg, 'rb') as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                self.wfile.write(chunk)

    def do_HEAD(self):
        return

    def do_POST(self):
        return

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

userdata.set('_playlist_url', '')
userdata.set('_epg_url', '')

class HTTP(object):
    started = False

    def start(self):
        if self.started:
            return

        port = check_port(DEFAULT_PORT)
        if not port:
            port = check_port()

        self._server = ThreadedHTTPServer((HOST, port), RequestHandler)
        self._server.allow_reuse_address = True
        self._httpd_thread = threading.Thread(target=self._server.serve_forever)
        self._httpd_thread.start()
        self.started = True
        log.info("API Started: {}:{}".format(HOST, port))

        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
        except:
            local_ip = HOST

        userdata.set('_playlist_url', 'http://{}:{}/{}'.format(local_ip, port, PLAYLIST_URL))
        userdata.set('_epg_url', 'http://{}:{}/{}'.format(local_ip, port, EPG_URL))

    def stop(self):
        if not self.started:
            return

        self._server.shutdown()
        self._server.server_close()
        self._server.socket.close()
        self._httpd_thread.join()
        self.started = False
        log.debug("API: Stopped")
        userdata.set('_playlist_url', '')
        userdata.set('_epg_url', '')
