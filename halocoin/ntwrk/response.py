class Response:
    def __init__(self, success=False, data=None):
        if data is None:
            data = ""

        self.__dict = dict(success=success, data=data)

    def setFlag(self, flag):
        self.__dict['success'] = flag

    def getFlag(self):
        return self.__dict['success']

    def getData(self):
        return self.__dict['data']

    def setData(self, new_data):
        self.__dict['data'] = new_data