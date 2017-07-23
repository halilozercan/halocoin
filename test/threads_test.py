import socket
import time

import ntwrk
from ntwrk import Message
from service import Service, sync, threaded, async


class ServiceA(Service):
    def __init__(self):
        Service.__init__(self, name='A')
        self.a = 1

    @sync
    def example(self, b):
        self.a += b

    @sync
    def get(self):
        return self.a

    @threaded
    def listen(self):
        print "running 2"
        time.sleep(1)
        #if self.get() > 12:
            #print 'not closing'
            #self.close_threaded()


class ServiceB(Service):
    def __init__(self, serviceA):
        Service.__init__(self, name='B')
        self.serviceA = serviceA
        self.a = 1

        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.settimeout(1)
        self.s.bind(('localhost', 2000))
        self.s.listen(5)

    @threaded
    def accept(self):
        try:
            print 'socket thread running'
            client_sock, address = self.s.accept()
            response, leftover = ntwrk.receive(client_sock)
            if response.is_successful():
                message = Message.from_yaml(response.getData())
                self.serviceA.example(int(message.get_body()))
        except socket.timeout:
            pass

    @sync
    def example(self, b):
        self.a += b
        self.serviceA.example(self.a)
        self.a *= serviceA.a

    def get(self):
        return self.a


serviceA = ServiceA()
serviceB = ServiceB(serviceA)

serviceA.register()
serviceB.register()

time.sleep(3)
serviceA.example(9)
serviceA.example(5)
print serviceA.get()
time.sleep(3)

serviceA.example(15)
print serviceA.get()

serviceA.unregister()
serviceB.unregister()
#print 'Sending data to ServiceB through socket'
#s = ntwrk.connect('localhost', 2000)
#ntwrk.send(Message(headers=None, body='5'), s)
