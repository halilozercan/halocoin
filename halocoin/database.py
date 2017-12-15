import sys

import os
import yaml
from simplekv.db.sql import SQLAlchemyStore
from sqlalchemy.exc import OperationalError

from halocoin import tools, custom
from halocoin.service import Service, sync


class DatabaseService(Service):
    """
    Database bindings for leveldb
    """

    def __init__(self, engine):
        Service.__init__(self, name='database')
        self.engine = engine
        self.DB = None
        self.salt = None
        self.req_count = 0
        self.set_state(Service.INIT)

    def on_register(self):
        try:
            from sqlalchemy import create_engine, MetaData
            db_location = os.path.join(self.engine.working_dir, self.engine.config['database']['location'])
            engine = create_engine('sqlite:///' + db_location)
            metadata = MetaData(bind=engine)
            self.DB = SQLAlchemyStore(engine, metadata, 'kvstore')
            self.DB.table.create()
        except OperationalError as e:
            pass
        except Exception as e:
            tools.log(e)
            sys.stderr.write('Redis connection cannot be established!\nFalling to SQLAlchemy')
            return False

        self.salt = custom.version
        return True

    @sync
    def get(self, key):
        """gets the key in args[0] using the salt"""
        try:
            return yaml.load(self.DB.get(self.salt + str(key)).decode())
        except Exception as e:
            return None

    @sync
    def put(self, key, value):
        """
        Puts the val in args[1] under the key in args[0] with the salt
        prepended to the key.
        """
        try:
            self.DB.put(self.salt + str(key), yaml.dump(value).encode())
            return True
        except Exception as e:
            return False

    @sync
    def exists(self, key):
        """
        Checks if the key in args[0] with the salt prepended is
        in the database.
        """
        try:
            return (self.salt + str(key)) in self.DB
        except KeyError:
            return False

    @sync
    def delete(self, key):
        """
        Removes the entry in the database under the the key in args[0]
        with the salt prepended.
        """
        try:
            self.DB.delete(self.salt + str(key))
            return True
        except:
            return False