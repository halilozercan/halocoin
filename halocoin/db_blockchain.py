import copy
import os
import pickle
import sys
import threading

import plyvel

from halocoin import tools, custom
from halocoin.service import lockit


class KeyValueStore:
    def __init__(self, engine):
        self.engine = engine
        self.DB = None
        self.iterator = None
        self.simulating = False
        self.recording = False
        self.changes_in_record = dict()
        self.simulation_owner = ''
        self.salt = None
        self.req_count = 0
        self.log = dict()
        try:
            db_location = os.path.join(self.engine.working_dir, 'halocoin.db')
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
            return copy.deepcopy(self.log[str(key)])

    @lockit('kvstore')
    def put(self, key, value):
        try:
            tname = threading.current_thread().getName()
            if tname != self.simulation_owner and self.simulating:
                raise EnvironmentError('There is a simulation going on! You cannot write to database from {}'
                                       .format(tname))
            elif tname == self.simulation_owner and self.simulating:
                if self.recording and str(key) not in self.changes_in_record.keys():
                    self.changes_in_record[str(key)] = {
                        'old': self.get(key)
                    }

                self.log[str(key)] = value
            elif not self.simulating:
                self.DB.put(str(key).encode(), pickle.dumps(value))
            return True
        except Exception as e:
            return False

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
        with self.DB.write_batch(transaction=True) as wb:
            for key, value in self.log.items():
                wb.put(str(key).encode(), pickle.dumps(value))

        self.log = dict()
        self.simulating = False

        # Remove earlier indices.
        length = self.get('length')
        for i in range(1000):
            self.delete('changes_' + str(length-i-30))

        return True

    @lockit('kvstore')
    def rollback(self):
        if not self.simulating:
            tools.log('There isn\'t any ongoing simulation')
            return False
        self.log = dict()
        self.simulating = False
        return True

    @lockit('kvstore')
    def start_record(self):
        if not self.simulating:
            tools.log('There isn\'t any ongoing simulation')
            return False

        self.recording = True
        self.changes_in_record = dict()

    @lockit('kvstore')
    def discard_record(self):
        if not self.simulating:
            tools.log('There isn\'t any ongoing simulation')
            return False

        self.recording = False
        self.changes_in_record = dict()

    @lockit('kvstore')
    def keep_record(self, name):
        if not self.simulating:
            tools.log('There isn\'t any ongoing simulation')
            return False

        self.recording = False
        self.put('changes_' + str(name), self.changes_in_record)
        self.changes_in_record = dict()
