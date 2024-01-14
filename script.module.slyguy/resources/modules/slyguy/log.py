import logging

from kodi_six import xbmc

from .constants import LOG_ID, LOG_FORMAT

class Logger(logging.Logger):
    def __call__(self, *args, **kwargs):
        self.debug(*args, **kwargs)

class LoggerHandler(logging.StreamHandler):
    LEVELS = {
        logging.NOTSET   : xbmc.LOGNONE,
        logging.DEBUG    : xbmc.LOGDEBUG,
        logging.INFO     : xbmc.LOGINFO,
        logging.WARNING  : xbmc.LOGWARNING,
        logging.ERROR    : xbmc.LOGERROR,
        logging.CRITICAL : xbmc.LOGFATAL,
    }

    def emit(self, record):
        msg   = self.format(record)
        level = self.LEVELS.get(record.levelno, xbmc.LOGDEBUG)
        xbmc.log(msg, level)

logging.setLoggerClass(Logger)

formatter = logging.Formatter(LOG_FORMAT)

handler = LoggerHandler()
handler.setFormatter(formatter)

log = logging.getLogger(LOG_ID)
log.handlers = [handler]
log.setLevel(logging.DEBUG)
