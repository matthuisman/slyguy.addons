import os
import json
import codecs

import peewee
from six.moves import cPickle

from . import userdata, signals
from .log import log
from .util import hash_6
from .constants import DB_PATH, DB_PRAGMAS, DB_MAX_INSERTS, DB_TABLENAME, ADDON_DEV

path = os.path.dirname(DB_PATH)
if not os.path.exists(path):
    os.makedirs(path)

db = peewee.SqliteDatabase(DB_PATH, pragmas=DB_PRAGMAS, timeout=10)

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
        ctx = db.get_sql_context()
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

    class Meta:
        database = db

class KeyStore(Model):
    key     = peewee.TextField(unique=True)
    value   = peewee.TextField()

    class Meta:
        table_name = DB_TABLENAME

tables = [KeyStore]
def check_tables():
    with db.atomic():
        for table in tables:
            key      = table.table_name()
            checksum = table.get_checksum()

            if KeyStore.exists_or_false(KeyStore.key == key, KeyStore.value == checksum):
                continue

            db.drop_tables([table])
            db.create_tables([table])

            KeyStore.set(key=key, value=checksum)

@signals.on(signals.AFTER_RESET)
def delete():
    close()
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

@signals.on(signals.ON_CLOSE)
def close():
    try:  db.execute_sql('VACUUM')
    except: log.debug('Failed to vacuum db')
    db.close()

@signals.on(signals.BEFORE_DISPATCH)
def connect():
    db.connect(reuse_if_open=True)
    check_tables()