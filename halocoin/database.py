import os
import pickle
import sys
import threading

import plyvel

from halocoin import tools, custom
from halocoin.service import lockit


class KeyValueStore:
    def __init__(self, engine, dbname):
        self.engine = engine
        self.dbname = dbname
        self.DB = None
        self.iterator = None
        self.simulating = False
        self.simulation_owner = ''
        self.salt = None
        self.req_count = 0
        self.log = dict()
        try:
            db_location = os.path.join(self.engine.working_dir, self.dbname)
            DB = plyvel.DB(db_location, create_if_missing=True)
            self.DB = DB.prefixed_db(custom.version.encode())
            self.iterator = self.DB.iterator
        except Exception as e:
            tools.log(e)
            sys.stderr.write('Database connection cannot be established!\n')

    @lockit('kvstore')
    def get(self, key):
        def from_database(key):
            try:
                return pickle.loads(self.DB.get(str(key).encode()))
            except Exception as e:
                return None

        tname = threading.current_thread().getName()
        if (not self.simulating) or (tname != self.simulation_owner and self.simulating) or \
                (tname == self.simulation_owner and self.simulating and str(key) not in self.log):
            return from_database(key)
        else:
            return self.log[str(key)]

    def put(self, key, value):
        try:
            tname = threading.current_thread().getName()
            if tname != self.simulation_owner and self.simulating:
                raise EnvironmentError('There is a simulation going on! You cannot write to database from {}'
                                       .format(tname))
            elif tname == self.simulation_owner and self.simulating:
                self.log[str(key)] = value
            elif not self.simulating:
                self.DB.put(str(key).encode(), pickle.dumps(value))
            return True
        except Exception as e:
            return False

    @lockit('kvstore')
    def exists(self, key):
        result = self.get(key)
        return result is not None

    def delete(self, key):
        return self.put(key, None)

    @lockit('kvstore')
    def simulate(self):
        """
        Database simulations are thread based batch transactions.
        When a simulation is started by a thread, any get or put operation
        is executed on the simulated database.

        Other threads
        :return:
        """
        if self.simulating:
            tools.log('There is already an ongoing simulation! {}'.format(threading.current_thread().getName()))
            return False
        try:
            self.simulating = True
            self.simulation_owner = threading.current_thread().getName()
            return True
        except:
            return False

    @lockit('kvstore')
    def commit(self):
        """
        Commit simply erases the earlier snapshot.
        :return:
        """
        if not self.simulating:
            tools.log('There isn\'t any ongoing simulation')
            return False
        for key, value in self.log.items():
            self.DB.put(str(key).encode(), pickle.dumps(value))
        self.log = dict()
        self.simulating = False
        return True

    @lockit('kvstore')
    def rollback(self):
        if not self.simulating:
            tools.log('There isn\'t any ongoing simulation')
            return False
        self.log = dict()
        self.simulating = False
        return True