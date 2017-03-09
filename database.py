import json
import leveldb
import os
from multiprocessing import Process

from network import Response
from network.server import Server


def default_entry(): return dict(count=0, amount=0)


def _noop():
    return None


class DatabaseProcess(Process):
    """
    Manages operations on the database.
    """

    def __init__(self, heart_queue, database_name, logfile, port):
        super(DatabaseProcess, self).__init__(name='database')
        self.heart_queue = heart_queue
        self.database_name = database_name
        self.logfile = logfile
        self.port = port

    def get(self, args):
        """Gets the key in args[0] using the salt"""
        try:
            return json.loads(self._get(self.salt + str(args[0])))
        except KeyError:
            return default_entry()

    def put(self, args):
        """
        Puts the val in args[1] under the key in args[0] with the salt
        prepended to the key.
        """
        try:
            self._put(self.salt + str(args[0]), json.dumps(args[1]))
        except:
            return False

    def existence(self, args):
        """
        Checks if the key in args[0] with the salt prepended is
        in the database.
        """
        try:
            self._get(self.salt + str(args[0]))
        except KeyError:
            return False
        else:
            return True

    def delete(self, args):
        """
        Removes the entry in the database under the the key in args[0]
        with the salt prepended.
        """
        # It isn't an error to try to delete something that isn't there.
        try:
            self._del(self.salt + str(args[0]))
            return True
        except:
            return False

    def run(self):
        def command_handler(command):
            try:
                name = command['type']
                assert (name not in ['__init__', 'run'])
                out = getattr(self, name)(command['args'])
                return out
            except Exception as exc:
                self.logfile(exc)
                self.logfile('command: ' + str(command))
                self.logfile('command type: ' + str(type(command)))
                return None

        self.DB = leveldb.LevelDB(self.database_name)
        self._get = self.DB.Get
        self._put = self.DB.Put
        self._del = self.DB.Delete

        try:
            self.salt = self._get('salt')
        except KeyError:
            self.salt = os.urandom(5)
            self._put('salt', self.salt)

        database_network = Server(handler=command_handler,
                                  port=self.port,
                                  heart_queue=self.heart_queue)
        database_network.run()
