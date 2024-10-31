import os
import json

import time
import peewee
from six.moves import cPickle

from slyguy import signals
from slyguy.log import log
from slyguy.util import hash_6, makedirs
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
    def db_value(self, value):
        pickled = cPickle.dumps(value)
        return self._constructor(pickled)

    def python_value(self, value):
        # value can be None when doing joins
        if value is not None:
            if isinstance(value, peewee.buffer_type):
                value = bytes(value)
            return cPickle.loads(value)


class JSONField(peewee.TextField):
    def db_value(self, value):
        return json.dumps(value, ensure_ascii=False)

    def python_value(self, value):
        # value can be None when doing joins
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
    if db:
        db.connect()


def close(db=None):
    db = db or get_db()
    if db:
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
        signals.add(signals.ON_EXIT, lambda db=self: close(db))
        super(Database, self).__init__(database, *args, **kwargs)

    def register_function(self, fn, name=None, num_params=-1):
        # override this as it breaks db closing on older kodi / linux
        # https://github.com/matthuisman/slyguy.addons/issues/804
        pass

    def close(self, *args, **kwargs):
        if self.is_closed():
            return

        log.debug("Closing db: {}".format(self.database))
        self.execute_sql('VACUUM')
        super(Database, self).close(*args, **kwargs)

    def connect(self, *args, **kwargs):
        if not self.is_closed():
            return

        log.debug("Connecting to db: {}".format(self.database))
        makedirs(os.path.dirname(self.database))
        timeout = time.time() + 5
        result = False
        exception = ''
        while time.time() < timeout:
            try:
                result = super(Database, self).connect(*args, **kwargs)
                if self._tables:
                    self.create_tables(self._tables, fail_silently=True)
            except Exception as e:
                exception = str(e)
                pass
            else:
                break
            time.sleep(0.1)
        else:
            raise TimeoutError("Failed to create db: '{}' within 5s due to: '{}'".format(self.database, exception))
        return result


def init(tables=None, db_path=DB_PATH, delete_on_reset=True):
    db = DBS[db_path] = Database(db_path, pragmas=DB_PRAGMAS, timeout=10, autoconnect=True, tables=tables)
    if delete_on_reset:
        signals.add(signals.AFTER_RESET, lambda db=db: delete(db))
    return db
