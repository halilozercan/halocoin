import os

import pickle
import random
import string

import yaml
from simplekv.memory.redisstore import RedisStore
import redis

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
        # TODO: Add authentication support for redis
        self.DB = RedisStore(redis.StrictRedis(db=self.engine.config['database']['index']))
        try:
            self.salt = self.DB.get('salt').decode()
            if self.salt is None:
                raise Exception
        except Exception as e:
            self.salt = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(5))
            self.DB.put('salt', self.salt.encode())
        return True

    @sync
    def get(self, key):
        """gets the key in args[0] using the salt"""
        try:
            return pickle.loads(
                self.DB.get(self.salt + str(key))
            )
        except Exception as e:
            return None

    @sync
    def put(self, key, value):
        """
        Puts the val in args[1] under the key in args[0] with the salt
        prepended to the key.
        """
        try:
            self.DB.put(self.salt + str(key), pickle.dumps(value))
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
            self.DB.dexists(self.salt + str(key))
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
            self.DB.delete(self.salt + str(key))
            return True
        except:
            return False
