import os
import sys
import threading

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
        self.simLock = threading.RLock()
        self.salt = None
        self.req_count = 0
        self.log = set()
        self.snapshots = {}
        try:
            db_location = os.path.join(self.engine.working_dir, self.dbname)
            DB = plyvel.DB(db_location, create_if_missing=True)
            self.DB = DB.prefixed_db(custom.version.encode())
            self.iterator = self.DB.iterator
        except Exception as e:
            tools.log(e)
            sys.stderr.write('Database connection cannot be established!\n')

    def get(self, key):
        db = self.DB
        tname = threading.current_thread().getName()
        if tname != "blockchain_process" and tname != "MainThread" and self.snapshot is not None:
            # Request is coming from blockchain process thread.
            # All actions are directed to ongoing database
            # If there is a simulation going on and we are not inside a blockchain namespace,
            # then we must use the earlier snapshot for this operation
            db = self.snapshot
        try:
            return yaml.load(db.get(str(key).encode()).decode())
        except Exception as e:
            return None

    def put(self, key, value):
        if threading.current_thread().getName() != 'blockchain_process':
            print(threading.current_thread().getName())
        try:
            encoded_value = yaml.dump(value).encode()
            self.DB.put(str(key).encode(), encoded_value)
            if self.snapshot is not None:
                self.log.add(str(key).encode())
            return True
        except Exception as e:
            return False

    def exists(self, key):
        result = self.get(key)
        return result is not None

    def delete(self, key):
        try:
            self.DB.delete(str(key).encode())
            if self.snapshot is not None:
                self.log.add(str(key).encode())
            return True
        except:
            return False

    @lockit('kvstore')
    def simulate(self):
        """
        Database simulations are thread based batch transactions.
        When a simulation is started by a thread, any get or put operation
        is executed on the simulated database.

        Other threads
        :return:
        """
        if self.snapshot is not None:
            tools.log('There is already an ongoing simulation!')
            return False
        try:
            self.snapshot = self.DB.snapshot()
            return True
        except:
            return False

    @lockit('kvstore')
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

    @lockit('kvstore')
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