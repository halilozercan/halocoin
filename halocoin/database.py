import os

import yaml

from halocoin.service import Service, sync


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
        self.DB = halodb(self.database_name, True)
        try:
            self.salt = self.DB.get('salt')
            if self.salt is None:
                raise Exception
        except Exception as e:
            self.salt = str(os.urandom(5))
            self.DB.set('salt', self.salt)
        return True

    @sync
    def get(self, key):
        """gets the key in args[0] using the salt"""
        try:
            return yaml.load(
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
            self.DB.set(self.salt + str(key), yaml.dump(value))
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
            self.DB.rem(self.salt + str(key))
            return True
        except:
            return False


class halodb(object):

    def __init__(self, location, option):
        '''Creates a database object and loads the data from the location path.
        If the file does not exist it will be created on the first update.'''
        self.load(location, option)

    def load(self, location, option):
        '''Loads, reloads or changes the path to the db file.'''
        location = os.path.expanduser(location)
        self.loco = location
        self.fsave = option
        if os.path.exists(location):
            self._loaddb()
        else:
            self.db = {}
        return True

    def dump(self):
        '''Force dump memory db to file.'''
        self._dumpdb(True)
        return True

    def set(self, key, value):
        '''Set the (string,int,whatever) value of a key'''
        self.db[key] = value
        self._dumpdb(self.fsave)
        return True

    def get(self, key):
        '''Get the value of a key'''
        try:
            return self.db[key]
        except KeyError:
            return None

    def getall(self):
        '''Return a list of all keys in db'''
        return self.db.keys()

    def rem(self, key):
        '''Delete a key'''
        del self.db[key]
        self._dumpdb(self.fsave)
        return True

    def lcreate(self, name):
        '''Create a list'''
        self.db[name] = []
        self._dumpdb(self.fsave)
        return True

    def ladd(self, name, value):
        '''Add a value to a list'''
        self.db[name].append(value)
        self._dumpdb(self.fsave)
        return True

    def lextend(self, name, seq):
        '''Extend a list with a sequence'''
        self.db[name].extend(seq)
        self._dumpdb(self.fsave)
        return True

    def lgetall(self, name):
        '''Return all values in a list'''
        return self.db[name]

    def lget(self, name, pos):
        '''Return one value in a list'''
        return self.db[name][pos]

    def lrem(self, name):
        '''Remove a list and all of its values'''
        number = len(self.db[name])
        del self.db[name]
        self._dumpdb(self.fsave)
        return number

    def lpop(self, name, pos):
        '''Remove one value in a list'''
        value = self.db[name][pos]
        del self.db[name][pos]
        self._dumpdb(self.fsave)
        return value

    def llen(self, name):
        '''Returns the length of the list'''
        return len(self.db[name])

    def append(self, key, more):
        '''Add more to a key's value'''
        tmp = self.db[key]
        self.db[key] = ('%s%s' % (tmp, more))
        self._dumpdb(self.fsave)
        return True

    def lappend(self, name, pos, more):
        '''Add more to a value in a list'''
        tmp = self.db[name][pos]
        self.db[name][pos] = ('%s%s' % (tmp, more))
        self._dumpdb(self.fsave)
        return True

    def dcreate(self, name):
        '''Create a dict'''
        self.db[name] = {}
        self._dumpdb(self.fsave)
        return True

    def dadd(self, name, pair):
        '''Add a key-value pair to a dict, "pair" is a tuple'''
        self.db[name][pair[0]] = pair[1]
        self._dumpdb(self.fsave)
        return True

    def dget(self, name, key):
        '''Return the value for a key in a dict'''
        return self.db[name][key]

    def dgetall(self, name):
        '''Return all key-value pairs from a dict'''
        return self.db[name]

    def drem(self, name):
        '''Remove a dict and all of its pairs'''
        del self.db[name]
        self._dumpdb(self.fsave)
        return True

    def dpop(self, name, key):
        '''Remove one key-value pair in a dict'''
        value = self.db[name][key]
        del self.db[name][key]
        self._dumpdb(self.fsave)
        return value

    def dkeys(self, name):
        '''Return all the keys for a dict'''
        return self.db[name].keys()

    def dvals(self, name):
        '''Return all the values for a dict'''
        return self.db[name].values()

    def dexists(self, name, key):
        '''Determine if a key exists or not'''
        if self.db[name][key] is not None:
            return 1
        else:
            return 0

    def deldb(self):
        '''Delete everything from the database'''
        self.db= {}
        self._dumpdb(self.fsave)
        return True

    def _loaddb(self):
        '''Load or reload the json info from the file'''
        with open(self.loco, 'r') as db_file:
            self.db = yaml.load(db_file)

    def _dumpdb(self, forced):
        '''Write/save the json dump into the file'''
        if forced:
            with open(self.loco, 'w') as db_file:
                yaml.dump(self.db, db_file)
