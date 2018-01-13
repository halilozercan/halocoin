import os
import sys
from io import BytesIO

import yaml
from simplekv import KeyValueStore, CopyMixin
from simplekv._compat import imap, text_type
from simplekv.db.sql import SQLAlchemyStore
from sqlalchemy import Table, Column, String, LargeBinary, select, exists
from sqlalchemy.exc import OperationalError

from halocoin import tools, custom
from halocoin.service import Service, sync


class DatabaseService(Service):
    def __init__(self, engine, dbname):
        Service.__init__(self, name='database')
        self.engine = engine
        self.dbname = dbname
        self.DB = None
        self.simulation = None
        self.salt = None
        self.req_count = 0
        self.set_state(Service.INIT)

    def on_register(self):
        try:
            from sqlalchemy import create_engine, MetaData
            db_location = os.path.join(self.engine.working_dir, self.dbname)
            self.dbengine = create_engine('sqlite:///' + db_location)
            #from sqlalchemy.pool import StaticPool
            #self.dbengine = create_engine('sqlite://',
            #                              connect_args={'check_same_thread': False},
            #                              poolclass=StaticPool)
            self.metadata = MetaData(bind=self.dbengine)
            self.DB = SQLAlchemyStore(self.dbengine, self.metadata, 'kvstore')
            self.DB.table.create()
        except OperationalError as e:
            pass
        except Exception as e:
            tools.log(e)
            sys.stderr.write('Database connection cannot be established!\n')
            return False

        self.salt = custom.version
        return True

    @sync
    def get(self, key):
        if self.simulation is None:
            return self._get(self.DB, key)
        else:
            return self._get(self.simulation, key)

    @sync
    def put(self, key, value):
        if self.simulation is None:
            return self._put(self.DB, key, value)
        else:
            return self._put(self.simulation, key, value)

    @sync
    def exists(self, key):
        if self.simulation is None:
            return self._exists(self.DB, key)
        else:
            return self._exists(self.simulation, key)

    @sync
    def delete(self, key):
        if self.simulation is None:
            return self._delete(self.DB, key)
        else:
            return self._delete(self.simulation, key)

    def _get(self, db, key):
        """gets the key in args[0] using the salt"""
        try:
            return yaml.load(db.get(self.salt + str(key)).decode())
        except Exception as e:
            return None

    def _put(self, db, key, value):
        """
        Puts the val in args[1] under the key in args[0] with the salt
        prepended to the key.
        """
        try:
            db.put(self.salt + str(key), yaml.dump(value).encode())
            return True
        except Exception as e:
            return False

    def _exists(self, db, key):
        """
        Checks if the key in args[0] with the salt prepended is
        in the database.
        """
        try:
            return (self.salt + str(key)) in db
        except KeyError:
            return False

    def _delete(self, db, key):
        """
        Removes the entry in the database under the the key in args[0]
        with the salt prepended.
        """
        try:
            db.delete(self.salt + str(key))
            return True
        except:
            return False

    @sync
    def simulate(self):
        if self.simulation is not None:
            tools.log('There is already an ongoing simulation!')
            return False
        try:
            self.simulation = SQLSimulationStore(self.dbengine, self.metadata, 'kvstore')
            return True
        except:
            return False

    @sync
    def commit(self):
        if self.simulation is None:
            tools.log('There isn\'t any ongoing simulation')
            return False
        self.simulation.commit()
        self.simulation = None
        return True

    @sync
    def rollback(self):
        if self.simulation is None:
            tools.log('There isn\'t any ongoing simulation')
            return False
        self.simulation.rollback()
        self.simulation = None
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
