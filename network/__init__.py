import socket
import sys

import pickle

import tools
from network.response import Response

MAX_MESSAGE_SIZE = 60000


def receive(client, data='', step=0, length=0, forever=False):
    if forever:
        print 'Step', step
    if step == 0:
        try:
            client.settimeout(10.0)
            try:
                string = client.recv(4)
            except socket.timeout:
                #Timed out
                return Response(False, 'Receive timed out')
            if forever:
                print 'length', string, int(string)
            length = int(string)
        except ValueError:
            print step
            print sys.exc_info()
            return Response(False, 'Received Length is not a valid integer.')
        return receive(client, data, step=1, length=length, forever=forever)
    else:
        while len(data) < length:
            d = client.recv(MAX_MESSAGE_SIZE)
            if forever:
                print 'content', d
            if not d:
                return Response(False, 'Broken connection to {}'.format(client.getpeername()))
            data += d

        try:
            received_message = pickle.loads(data)
            return Response(True, received_message)
        except:
            return Response(False, "Deserialization went wrong")


def send(msg, sock):
    # Add length of the string to the start. Also pad it to be at least 5 characters.
    try:
        serialized_msg = pickle.dumps(msg)
    except:
        tools.log("Send_msg received wrong type of message")
        tools.log(sys.exc_info())
        return False

    length_of_msg = tools.buffer_(str(len(serialized_msg)), 4)
    try:
        sock.send(length_of_msg)
    except:
        tools.log("Failed to send length of message")
        tools.log(sys.exc_info())
        return False

    while serialized_msg:
        try:
            sent = sock.send(serialized_msg)
        except:
            tools.log('Peer at {} died'.format(sock.getpeername()))
            return False
        serialized_msg = serialized_msg[sent:]

    return True


def send_receive(message=None, sock=None, host='localhost', port=3699, counter=0):
    if sock is None:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setblocking(5)
        try:
            s.connect((host, port))
        except:
            return None
    else:
        s = sock

    res = send(message, s)

    if not res:
        print "Could not send to", host, port
        return None

    res = receive(s)

    if not res.is_successful():
        return None
        #return send_error(message, sock=s, host=host, port=port, counter=counter)
    else:
        return res.get_data()


def send_error(msg, sock, host, port, counter):
    if counter > 1:
        tools.log('Maximum number of attempts is reached.\n'
                  '{}:{} could not get the message: {}'
                  .format(host, port, msg))
        return None
    return send_receive(msg, sock=sock, host=host, port=port, counter=(counter + 1))


def connect(host='localhost', port=3699):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setblocking(5)
    try:
        s.connect((host, port))
        return s
    except:
        return None
