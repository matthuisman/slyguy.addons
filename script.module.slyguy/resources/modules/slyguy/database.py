import os
import json

import peewee
from six.moves import cPickle

from . import signals
from .log import log
from .util import hash_6
from .constants import DB_PATH, DB_PRAGMAS, DB_TABLENAME, ADDON_DEV


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
    field_type = 'JSON'

    def db_value(self, value):
        if value is not None:
            return json.dumps(value, ensure_ascii=False)

    def python_value(self, value):
        if value is not None:
            return json.loads(value)


class Model(peewee.Model):
    checksum = ''

    @classmethod
    def get_checksum(cls):
        ctx = cls._meta.database.get_sql_context()
        query = cls._schema._create_table()
        return hash_6([cls.checksum, ctx.sql(query).query(), cls._meta.indexes])

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


def check_tables(db, tables):
    tables.insert(0, KeyStore)
    KeyStore._meta.database = db
    with db.atomic():
        for table in tables:
            key = table.table_name()
            checksum = table.get_checksum()

            if KeyStore.exists_or_false(KeyStore.key == key, KeyStore.value == checksum):
                continue

            db.drop_tables([table])
            db.create_tables([table])

            KeyStore.set(key=key, value=checksum)


def connect(db=None, tables=None):
    db = db or get_db()
    if not db:
        return
    log.info("Connecting to db: {}".format(db.database))
    db.connect(reuse_if_open=True)
    if tables:
        check_tables(db, tables)


def close(db=None):
    db = db or get_db()
    if not db:
        return
    if db.database:
        log.info("Closing db: {}".format(db.database))
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


def init(tables=None, db_path=DB_PATH):
    if db_path in DBS:
        return DBS[db_path]

    path = os.path.dirname(db_path)
    if not os.path.exists(path):
        os.makedirs(path)

    db = peewee.SqliteDatabase(db_path)
    tables = tables or []
    for table in tables:
        table._meta.database = db

    signals.add(signals.BEFORE_DISPATCH, lambda db=db, tables=tables: connect(db, tables))
    signals.add(signals.ON_CLOSE, lambda db=db: close(db))
    signals.add(signals.AFTER_RESET, lambda db=db: delete(db))
    DBS[db_path] = db
