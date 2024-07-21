import os
import json

import peewee
from kodi_six import xbmc
from six.moves import cPickle
from filelock import FileLock

from slyguy import signals
from slyguy.log import log
from slyguy.util import hash_6
from slyguy.constants import DB_PATH, DB_PRAGMAS, DB_TABLENAME, ADDON_DEV


if ADDON_DEV and not int(os.environ.get('QUIET', 0)):
    import logging
    logger = logging.getLogger('peewee')
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.DEBUG)


class HashField(peewee.TextField):
    def db_value(self, value):
        return hash_6(value)


class PickleField(peewee.BlobField):
    def python_value(self, value):
        if value is not None:
            if isinstance(value, peewee.buffer_type):
                value = bytes(value)
            return cPickle.loads(value)

    def db_value(self, value):
        if value is not None:
            pickled = cPickle.dumps(value)
            return self._constructor(pickled)

class JSONField(peewee.TextField):
    def db_value(self, value):
        if value is not None:
            return json.dumps(value, ensure_ascii=False)

    def python_value(self, value):
        if value is not None:
            return json.loads(value)


class Model(peewee.Model):
    @classmethod
    def delete_where(cls, *args, **kwargs):
        return super(Model, cls).delete().where(*args, **kwargs).execute()

    @classmethod
    def exists_or_false(cls, *args, **kwargs):
        try:
            return cls.select().where(*args, **kwargs).exists()
        except peewee.OperationalError:
            return False

    @classmethod
    def set(cls, *args, **kwargs):
        return super(Model, cls).replace(*args, **kwargs).execute()

    @classmethod
    def bulk_create_lazy(cls, to_create, force=False):
        batch_size = max(1, int(999/len(cls._meta.fields)))
        
        if not to_create or (not force and len(to_create) < batch_size):
            return False

        cls.bulk_create(to_create, batch_size=batch_size)

        return True

    @classmethod
    def bulk_create(cls, *args, **kwargs):
        if not kwargs.get('batch_size'):
            kwargs['batch_size'] = max(1, int(999/len(cls._meta.fields)))

        return super(Model, cls).bulk_create(*args, **kwargs)

    @classmethod
    def bulk_update(cls, *args, **kwargs):
        if not kwargs.get('batch_size'):
            kwargs['batch_size'] = max(1, int(999/(len(cls._meta.fields)*2)) - 1)

        return super(Model, cls).bulk_update(*args, **kwargs)

    @classmethod
    def table_name(cls):
        return cls._meta.table_name

    @classmethod
    def truncate(cls):
        return super(Model, cls).delete().execute()

    def to_dict(self):
        data = {}

        for field in self._meta.sorted_fields:
            field_data = self.__data__.get(field.name)
            data[field.name] = field_data

        return data

    def __str__(self):
        return str(self.to_dict())

    def __repr__(self):
        return self.__str__


class KeyStore(Model):
    key = peewee.TextField(unique=True)
    value = peewee.TextField()

    class Meta:
        table_name = DB_TABLENAME


def connect(db=None):
    db = db or get_db()
    if not db:
        return
    if db.database:
        db.connect()


def close(db=None):
    db = db or get_db()
    if not db:
        return

    if db.database:
        log.debug("Closing db: {}".format(db.database))
        try: db.execute_sql('VACUUM')
        except: log.debug('Failed to vacuum db')
        db.close()


def delete(db=None):
    db = db or get_db()
    if not db:
        return
    close(db)
    if os.path.exists(db.database):
        log.info("Deleting db: {}".format(db.database))
        os.remove(db.database)


DBS = {}
def get_db(db_path=DB_PATH):
    return DBS.get(db_path)


class Database(peewee.SqliteDatabase):
    def __init__(self, database, *args, **kwargs):
        self._tables = kwargs.pop('tables', [])
        for table in self._tables:
            table._meta.database = self
        signals.add(signals.ON_CLOSE, lambda db=self: close(db))
        signals.add(signals.AFTER_RESET, lambda db=self: delete(db))
        super(Database, self).__init__(database, *args, **kwargs)

    def register_function(self, fn, name=None, num_params=-1):
        # override this as it breaks db closing on older kodi / linux
        # https://github.com/matthuisman/slyguy.addons/issues/804
        pass

    def connect(self, *args, **kwargs):
        if not self.is_closed():
            return

        lock_file = xbmc.translatePath('special://temp/{}.lock'.format(os.path.basename(self.database)))
        with FileLock(lock_file):
            log.debug("Connecting to db: {}".format(self.database))
            db_dir = os.path.dirname(self.database)
            if not os.path.exists(db_dir):
                os.makedirs(db_dir)

            result = super(Database, self).connect(*args, **kwargs)
            if result and self._tables:
                self.create_tables(self._tables, fail_silently=True)

        return result


def init(tables=None, db_path=DB_PATH):
    if db_path not in DBS:
        DBS[db_path] = Database(db_path, pragmas=DB_PRAGMAS, timeout=10, autoconnect=True, tables=tables)
    return DBS[db_path]
