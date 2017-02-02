import sys
import pickle


class Message:
    def __init__(self, _type="default", _message=""):
        self.__type = _type
        self.__message = _message

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
