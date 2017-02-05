import Queue
import socket
import time

import network
import tools


class Server:
    def __init__(self, handler, port, heart_queue='default', external=False):
        self.__handler = handler
        self.__port = port
        self.__heart_queue = heart_queue
        self.__external = external

        self.__backlog = 5
        if self.__heart_queue == 'default':
            self.__heart_queue = Queue.Queue()

        if external:
            self.__host = '0.0.0.0'
        else:
            self.__host = 'localhost'

        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def run(self):
        time.sleep(1)

        self.__socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.__socket.bind((self.__host, self.__port))
        except:
            tools.kill_processes_using_ports([str(self.__port)])
            time.sleep(2)
            return self.run()

        self.__socket.listen(self.__backlog)

        while True:
            try:
                a = self.serve_once(network.MAX_MESSAGE_SIZE)
                if a == 'stop':
                    self.__socket.close()
                    tools.log('Shutting off server: ' + str(self.__port))
                    return
            except Exception as exc:
                tools.log('Networking error: ' + str(self.__port))
                tools.log(exc)

    def serve_once(self, size):
        client, address = self.__socket.accept()
        response = network.receive_all(client)
        if not response.is_successful():
            return self.serve_once(size)
        else:
            if response.getData() is "stop":
                return "stop"
            elif response.getData() is "ping":
                network.send_any("pong", client)
            else:
                response = self.__handler(response.getData())
                network.send_any(response, client)
        client.close()
        return 0



