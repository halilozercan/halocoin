import marshal
import leveldb
import os

import redis as redis

from service import Service, sync


class DatabaseService(Service):
    """
    Database bindings for leveldb
    """
    def __init__(self, engine):
        Service.__init__(self, name='database')
        self.engine = engine
        self.database_name = self.engine.config['database.name']
        self.DB = None
        self.salt = None
        self.req_count = 0
        self.set_state(Service.INIT)

    def on_register(self):
        self.DB = leveldb.LevelDB(self.database_name)
        try:
            self.salt = self.DB.Get('salt')
        except KeyError:
            self.salt = os.urandom(5)
            self.DB.Put('salt', self.salt)
        return True

    @sync
    def get(self, key):
        """Gets the key in args[0] using the salt"""
        try:
            return marshal.loads(self.DB.Get(self.salt + str(key)))
        except KeyError:
            return None

    @sync
    def put(self, key, value):
        """
        Puts the val in args[1] under the key in args[0] with the salt
        prepended to the key.
        """
        try:
            self.DB.Put(self.salt + str(key), marshal.dumps(value))
            return True
        except:
            import sys
            print sys.exc_info()
            return False

    @sync
    def exists(self, key):
        """
        Checks if the key in args[0] with the salt prepended is
        in the database.
        """
        try:
            self.DB.Get(self.salt + str(key))
        except KeyError:
            return False
        return True

    @sync
    def delete(self, key):
        """
        Removes the entry in the database under the the key in args[0]
        with the salt prepended.
        """
        try:
            self.DB.Delete(self.salt + str(key))
            return True
        except:
            return False


class RedisService(Service):
    """
    Database bindings for redis
    """
    def __init__(self, engine):
        Service.__init__(self, name='database')
        self.engine = engine
        self.database_name = self.engine.config['database.name']
        self.database_pass = self.engine.config['database.pass']
        self.database_port = self.engine.config['database.port']
        self.DB = None
        self.salt = None
        self.req_count = 0
        self.set_state(Service.INIT)

    def on_register(self):
        self.DB = redis.Redis(host='localhost', port=self.database_port,
                              db=self.database_name, password=self.database_pass)
        if self.DB.exists('salt'):
            self.salt = self.DB.get('salt')
        else:
            self.salt = os.urandom(5)
            self.DB.set('salt', self.salt)
        return True

    @sync
    def get(self, key):
        """Gets the key in args[0] using the salt"""
        try:
            return marshal.loads(self.DB.get(self.salt + str(key)))
        except:
            return None

    @sync
    def put(self, key, value):
        """
        Puts the val in args[1] under the key in args[0] with the salt
        prepended to the key.
        """
        try:
            self.DB.set(self.salt + str(key), marshal.dumps(value))
            return True
        except:
            return False

    @sync
    def exists(self, key):
        """
        Checks if the key in args[0] with the salt prepended is
        in the database.
        """
        return self.DB.exists(self.salt + str(key))

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
