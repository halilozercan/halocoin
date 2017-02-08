import sys
import pickle


class Message:
    def __init__(self, _type="default", _message=""):
        self.__type = _type
        self.__message = _message

    def __len__(self):
        return len(self.dump())

    def __str__(self):
        return self.__message.__str__()

    def getType(self):
        return self.__type

    def getMessage(self):
        return self.__message

    def setType(self, _type):
        self.__type = _type

    def setMessage(self, message):
        self.__message = message

    def dump(self):
        return pickle.dumps({
            'type': self.__type,
            'message': self.__message
        })

    def load(self, pickled):
        try:
            obj = pickle.loads(pickled)
            self.__type = obj['type']
            self.__message = obj['message']
        except:
            print("Unpackaging error: " + sys.exc_info())
