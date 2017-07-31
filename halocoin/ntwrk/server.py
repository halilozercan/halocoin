import Queue
import inspect
import logging
import os
import socket
import ssl
import threading
import time

import sys
import uuid

from smp import SMProtocol


class Server:
    def __init__(self, smprotocol, port=3000, external=False, smp_args=(), ssl_args=None, unix_socket_config=None):
        if inspect.isclass(smprotocol):
            self.smprotocol = smprotocol
        else:
            raise ValueError('Specified smp is not a class definition')
        self.port = port
        self.external = external
        self.ssl_args = ssl_args
        self.unix_socket_config = unix_socket_config
        self.id = str(uuid.uuid4())

        self.backlog = 20

        if external:
            self.host = '0.0.0.0'
        else:
            self.host = 'localhost'

        self.smp_args = smp_args
        self.is_active = False
        self.__accept_thread = threading.Thread(target=self.accept_thread)
        self.__mainloop_thread = threading.Thread(target=self.mainloop_thread, name='server-mainloop-' + self.id)

        self.mainloop_message_queue = Queue.Queue()

        self.client_smp_dict = {}
        self.client_counter = 0

        if unix_socket_config is not None:
            try:
                os.unlink(unix_socket_config['address'])
            except OSError:
                if os.path.exists(unix_socket_config['address']):
                    raise ReferenceError('There is already a file that addresses this socket')
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        else:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(10)
        self.new_client_lock = threading.Lock()

        self.originating_thread = threading.current_thread()
        self.is_main_thread = lambda: threading.current_thread().getName() == self.__mainloop_thread.getName()

    def list_clients(self, extras=list()):
        result = []
        for client in self.client_smp_dict.values():
            if client.is_active:
                client_summary = {
                    'server_assigned_name': client.server_assigned_name,
                    'address': client.address,
                    'connected_at': client.connected_at
                }
                for extra in extras:
                    if hasattr(client, extra) and extra not in client_summary:
                        client_summary[extra] = getattr(client, extra)
                result.append(client_summary)
        return result

    def new_client(self, _socket, _address):
        if self.is_main_thread():
            server_assigned_name = str(self.client_counter) + "c"
            _smp = self.smprotocol(_socket, self, server_assigned_name, _address, *self.smp_args)
            _smp.bind()
            self.client_smp_dict[server_assigned_name] = _smp
            self.client_counter += 1
        else:
            self.mainloop_message_queue.put(('new_client', [_socket, _address]))

    def start(self):
        self.is_active = True
        self.__mainloop_thread.start()
        self.__accept_thread.start()

    def stop(self):
        if self.is_main_thread():
            self.is_active = False
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
            for smp in self.client_smp_dict.values():
                smp.unbind()
            return True
        else:
            self.mainloop_message_queue.put(['stop'])

    def join(self):
        if self.originating_thread.getName() == threading.current_thread().getName():
            if self.__accept_thread.isAlive():
                self.__accept_thread.join()
            if self.__mainloop_thread.isAlive():
                self.__mainloop_thread.join()

    """
    ;param msg: Message to be sent to targets
    ;param target: a callable that evaluates whether given client should receive the message
    """
    def send_message(self, msg, target=None):
        if self.is_main_thread():
            if callable(target):
                for client in self.client_smp_dict.values():
                    if (target is None or target(client)) and client.is_active:
                        client.send_message(msg)
            else:
                for client in self.client_smp_dict.values():
                    if (target is None or client.server_assigned_name == target) and client.is_active:
                        client.send_message(msg)
        else:
            self.mainloop_message_queue.put(('send', [msg, target]))

    def mainloop_thread(self):
        while self.is_active:
            try:
                message = self.mainloop_message_queue.get(timeout=1)
                if message[0] == 'new_client':
                    self.new_client(message[1][0], message[1][1])
                elif message[0] == 'send':
                    self.send_message(message[1][0], message[1][1])
                elif message[0] == 'stop':
                    self.stop()
            except Queue.Empty:
                pass

    def accept_thread(self):
        if self.unix_socket_config is None:
            self.socket.bind((self.host, self.port))
        else:
            self.socket.bind(self.unix_socket_config['address'])

        self.socket.listen(self.backlog)

        while self.is_active:
            try:
                client_sock, address = self.socket.accept()
                if self.ssl_args is not None:
                    client_sock = ssl.wrap_socket(client_sock, server_side=True, **self.ssl_args)
                self.new_client(client_sock, address)
            except:
                pass
                #sys.stderr.write(str(sys.exc_info()))
                #sys.stderr.flush()


class ServerSMProtocol(SMProtocol):
    def __init__(self, sock, server, server_assigned_name, address):
        self.server = server
        self.server_assigned_name = server_assigned_name
        self.address = address
        SMProtocol.__init__(self, sock)

    def connection_error(self):
        try:
            del self.server.client_smp_dict[self.server_assigned_name]
        except:
            pass
