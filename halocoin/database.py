import os
import sys
from io import BytesIO

import plyvel
import yaml
from simplekv import KeyValueStore, CopyMixin
from simplekv._compat import imap, text_type
from sqlalchemy import Table, Column, String, LargeBinary, select, exists

from halocoin import tools, custom
from halocoin.service import Service, sync


class DatabaseService(Service):
    def __init__(self, engine, dbname):
        Service.__init__(self, name='database')
        self.engine = engine
        self.dbname = dbname
        self.DB = None
        self.iterator = None
        self.snapshot = None
        self.salt = None
        self.req_count = 0
        self.log = set()
        self.set_state(Service.INIT)

    def on_register(self):
        try:
            db_location = os.path.join(self.engine.working_dir, self.dbname)
            DB = plyvel.DB(db_location, create_if_missing=True)
            self.DB = DB.prefixed_db(custom.version.encode())
            self.iterator = self.DB.iterator
        except Exception as e:
            tools.log(e)
            sys.stderr.write('Database connection cannot be established!\n')
            return False
        return True

    @sync
    def get(self, key):
        """gets the key in args[0] using the salt"""
        try:
            return yaml.load(self.DB.get(str(key).encode()).decode())
        except Exception as e:
            return None

    @sync
    def put(self, key, value):
        """
        Puts the val in args[1] under the key in args[0] with the salt
        prepended to the key.
        """
        try:
            encoded_value = yaml.dump(value).encode()
            self.DB.put(str(key).encode(), encoded_value)
            if self.snapshot is not None:
                self.log.add(str(key).encode())
            return True
        except Exception as e:
            return False

    @sync
    def exists(self, key):
        """
        Checks if the key in args[0] with the salt prepended is
        in the database.
        """
        result = self.get(key)
        return result is not None

    @sync
    def delete(self, key):
        """
        Removes the entry in the database under the the key in args[0]
        with the salt prepended.
        """
        try:
            self.DB.delete(str(key).encode())
            if self.snapshot is not None:
                self.log.add(str(key).encode())
            return True
        except:
            return False

    @sync
    def simulate(self):
        if self.snapshot is not None:
            tools.log('There is already an ongoing simulation!')
            raise Exception('There is already an ongoing simulation!')
            # return False
        try:
            self.snapshot = self.DB.snapshot()
            return True
        except:
            return False

    @sync
    def commit(self):
        """
        Commit simply erases the earlier snapshot.
        :return:
        """
        if self.snapshot is None:
            tools.log('There isn\'t any ongoing simulation')
            return False
        self.snapshot = None
        self.log = set()
        return True

    @sync
    def rollback(self):
        if self.snapshot is None:
            tools.log('There isn\'t any ongoing simulation')
            return False
        for key in self.log:
            value = self.snapshot.get(key)
            if value is not None:
                self.DB.put(key, value)
            else:
                self.DB.delete(key)
        self.log = set()
        self.snapshot = None
        return True


class SQLSimulationStore(KeyValueStore, CopyMixin):
    """
    This is a copy of SQLAlchemyStore with transaction no commit support(simulation).
    """

    def __init__(self, bind, metadata, tablename):
        from sqlalchemy.orm import sessionmaker
        self.bind = bind

        self.table = Table(tablename, metadata,
                           # 250 characters is the maximum key length that we guarantee can be
                           # handled by any kind of backend
                           Column('key', String(250), primary_key=True),
                           Column('value', LargeBinary, nullable=False),
                           extend_existing=True
                           )
        Session = sessionmaker()
        Session.configure(bind=bind)
        self.session = Session()

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()

    def _has_key(self, key):
        return self.bind.execute(
            select([exists().where(self.table.c.key == key)])
        ).scalar()

    def _delete(self, key):
        self.bind.execute(
            self.table.delete(self.table.c.key == key)
        )

    def _get(self, key):
        rv = self.session.execute(
            select([self.table.c.value], self.table.c.key == key).limit(1)
        ).scalar()

        if not rv:
            raise KeyError(key)

        return rv

    def _open(self, key):
        return BytesIO(self._get(key))

    def _copy(self, source, dest):
        data = self.session.execute(
            select([self.table.c.value], self.table.c.key == source).limit(1)
        ).scalar()
        if not data:
            raise KeyError(source)

        # delete the potential existing previous key
        self.session.execute(self.table.delete(self.table.c.key == dest))
        self.session.execute(self.table.insert({
            'key': dest,
            'value': data,
        }))
        return dest

    def _put(self, key, data):
        # delete the old
        self.session.execute(self.table.delete(self.table.c.key == key))

        # insert new
        self.session.execute(self.table.insert({
            'key': key,
            'value': data
        }))

        return key

    def _put_file(self, key, file):
        return self._put(key, file.read())

    def iter_keys(self, prefix=u""):
        query = select([self.table.c.key])
        if prefix != "":
            query = query.where(self.table.c.key.like(prefix + '%'))
        return imap(lambda v: text_type(v[0]),
                    self.session.execute(query))
