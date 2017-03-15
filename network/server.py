import Queue
import socket
import time
import threading

import network
import tools


class Server:

    def __init__(self, handler, port, heart_queue='default', external=False, keep_connection=False):
        self.__handler = handler
        self.__port = port
        self.__heart_queue = heart_queue
        self.__external = external
        self.__keep = keep_connection

        self.__backlog = 5
        if self.__heart_queue == 'default':
            self.__heart_queue = Queue.Queue()
        else:
            self.__heart_queue = heart_queue

        if external:
            self.__host = '0.0.0.0'
        else:
            self.__host = 'localhost'

        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def run_async(self):
        thread = threading.Thread(target=self.run)
        thread.start()

    def run(self):
        self.__socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.__socket.bind((self.__host, self.__port))
        except:
            tools.log("Killing processes")
            tools.kill_processes_using_ports([str(self.__port)])
            time.sleep(2)
            return self.run()

        self.__socket.listen(self.__backlog)

        print "Started server at", self.__port

        while True:
            try:
                a = self.serve_once()
                if a == 'stop':
                    self.__socket.close()
                    tools.log('Shutting off server: ' + str(self.__port))
                    return
            except Exception as exc:
                tools.log('Networking error: ' + str(self.__port))
                tools.log(exc)

    def serve_once(self):
        client, address = self.__socket.accept()
        response = network.receive(client)
        if not response.is_successful():
            return self.serve_once()
        else:
            if response.get_data() == "stop":
                network.send("stopping", client)
                return "stop"
            elif response.get_data() == "ping":
                network.send("pong", client)
            else:
                answer = self.__handler(response.get_data())
                if answer is None:
                    network.send("Could not give a response. Endpoint does not understand the message.", client)
                else:
                    network.send(answer, client)
        if not self.__keep:
            client.close()
        return 0