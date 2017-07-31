import json
import yaml
import uuid


class Order:
    def __init__(self, action, args, kwargs):
        self.id = uuid.uuid4()
        self.action = action
        self.args = args
        self.kwargs = kwargs


class Response:
    def __init__(self, id, answer):
        self.id = id
        self.answer = answer


class Message:
    def __init__(self, headers=None, body=""):
        if headers is None:
            headers = {}
        self.__headers = headers
        self.__body = body

    def set_header(self, key, value):
        self.__headers[key] = value

    def get_header(self, key):
        if key in self.__headers.keys():
            return self.__headers[key]
        else:
            return None

    def get_headers(self):
        return self.__headers

    def set_body(self, body):
        self.__body = body

    def add_body(self, b):
        self.__body += b

    def get_body(self):
        return self.__body

    def __str__(self):
        return yaml.dump({'headers': self.__headers,
                          'body': self.__body})

    def __repr__(self):
        return self.__body

    @staticmethod
    def from_yaml(string):
        try:
            as_dict = yaml.load(string)
        except:
            raise ValueError('Could not load yaml representation of arrived message')

        return Message(headers=as_dict['headers'], body=as_dict['body'])