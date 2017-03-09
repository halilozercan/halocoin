import tools


class Response:
    def __init__(self, success=False, data=None):
        if data is None:
            data = ""

        if not success:
            tools.log(data.__str__())
        self.__dict = dict(success=success, data=data)

    def is_successful(self):
        return self.__dict['success']

    def get_data(self):
        return self.__dict['data']

    def set_data(self, new_data):
        self.__dict['data'] = new_data