import Queue
import socket
import threading
import time
import uuid

import sys

import ntwrk
from message import Message


class SMProtocol:
    def __init__(self, sock, hb_interval=5):
        self.sock = sock
        self.id = str(uuid.uuid4())
        self.origin_thread = threading.current_thread()
        self.__receive_thread = threading.Thread(target=self.receive_thread)
        self.__heartbeat_thread = threading.Thread(target=self.heartbeat_thread)
        self.__send_thread = threading.Thread(target=self.send_thread)
        self.__mainloop_thread = threading.Thread(target=self.mainloop_thread, name="smp-mainloop-" + self.id)
        self.is_active = False
        self.send_message_queue = Queue.Queue()
        self.mainloop_message_queue = Queue.Queue()
        self.hb_interval = hb_interval
        self.__hb_enabled = (hb_interval > 0)
        self.sent_message_counter = 0
        self.connected_at = 0
        self.is_main_thread = lambda: threading.current_thread().getName() == self.__mainloop_thread.getName()

    def bind(self):
        self.is_active = True
        self.__receive_thread.start()
        self.__send_thread.start()
        if self.__hb_enabled:
            self.__heartbeat_thread.start()
        self.__mainloop_thread.start()

    def unbind(self):
        if self.is_main_thread():
            self.is_active = False
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.close()
            except:
                print 'Warning. Socket could not be shutdown.'
        else:
            self.mainloop_message_queue.put(['unbind'])

    def join(self):
        if self.origin_thread.getName() == threading.current_thread().getName():
            if self.__hb_enabled:
                self.__heartbeat_thread.join()
            self.__receive_thread.join()
            self.__send_thread.join()
            self.__mainloop_thread.join()
        else:
            sys.stderr.write('You are trying to join from another thread. Use originating thread.\n')
            sys.stderr.flush()

    def send_message(self, msg):
        if self.is_main_thread():
            # We are already in mainloop. Just send this request to send thread
            self.send_message_queue.put(msg)
        else:
            # Being called from somewhere else. Make sure this goes to mainloop before hand.
            self.mainloop_message_queue.put(('send', msg))

    def send_file(self, headers, file_address, filename=''):
        msg = Message(headers=headers, body=open(file_address, 'rb').read())
        msg.set_header('type', 'file')
        if filename != '':
            msg.set_header('filename', filename)
        return self.send_message(msg)

    def receive_message(self, message):
        # Should be implemented by subclass
        pass

    def connection_error(self):
        # Should be implemented by subclass
        pass

    def is_connected(self):
        return self.is_active

    def mainloop_thread(self):
        while self.is_active:
            try:
                message = self.mainloop_message_queue.get(timeout=1)
                if message[0] == 'send':
                    self.send_message(message[1])
                elif message[0] == 'receive':
                    self.receive_message(message[1])
                elif message[0] == 'unbind':
                    self.unbind()
                elif message[0] == 'connection_error':
                    self.connection_error()
                    self.unbind()
            except Queue.Empty:
                pass

    def heartbeat_thread(self):
        index = 1
        while self.is_active:
            hb_msg = Message(body="", headers={"HB": str(index)})
            if ntwrk.send(hb_msg, self.sock):
                time.sleep(self.hb_interval)
                index += 1
            elif self.is_active:
                self.mainloop_message_queue.put(['connection_error'])

    def send_thread(self):
        def send_message(msg, sock):
            if msg.get_header('content_length') is None:
                msg.set_header('content_length', len(msg.get_body()))

            return ntwrk.send(msg, sock)

        while self.is_active:
            try:
                new_message = self.send_message_queue.get(timeout=1)
                send_message(new_message, self.sock)
            except Queue.Empty:
                pass

    def receive_thread(self):
        leftover = ''
        while self.is_active:
            response, leftover = ntwrk.receive(self.sock, leftover=leftover)
            if self.connected_at == 0:
                self.connected_at = time.time()

            if response.getFlag():
                string = response.getData()
                try:
                    received_message = Message.from_yaml(string)
                except:
                    continue

                if received_message.get_header('HB') is not None:
                    # Simple heartbeat. Al iz wel
                    continue

                self.mainloop_message_queue.put(('receive', received_message))

            elif response.getData() != 'timeout' or (response.getData() == 'timeout' and self.__hb_enabled):
                if self.is_active:
                    self.mainloop_message_queue.put(['connection_error'])
