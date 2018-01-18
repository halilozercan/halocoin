import os
import sys

import plyvel
import yaml

from halocoin import tools, custom
from halocoin.service import lockit


class KeyValueStore:
    def __init__(self, engine, dbname):
        self.engine = engine
        self.dbname = dbname
        self.DB = None
        self.iterator = None
        self.snapshot = None
        self.salt = None
        self.req_count = 0
        self.log = set()
        try:
            db_location = os.path.join(self.engine.working_dir, self.dbname)
            DB = plyvel.DB(db_location, create_if_missing=True)
            self.DB = DB.prefixed_db(custom.version.encode())
            self.iterator = self.DB.iterator
        except Exception as e:
            tools.log(e)
            sys.stderr.write('Database connection cannot be established!\n')

    def get(self, key):
        """gets the key in args[0] using the salt"""
        try:
            return yaml.load(self.DB.get(str(key).encode()).decode())
        except Exception as e:
            return None

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

    def exists(self, key):
        """
        Checks if the key in args[0] with the salt prepended is
        in the database.
        """
        result = self.get(key)
        return result is not None

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

    @lockit('simulation')
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

    @lockit('simulation')
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

    @lockit('simulation')
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
