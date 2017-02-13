import socket
import sys
import time

import custom
import tools
from network.message import Message
from network.response import Response

MAX_MESSAGE_SIZE = 60000


def receive_all(client, data='', step=0, length=0):
    """
    :param client; A python socket to identify client
    :param data; Data that is being received. Do not specify from outside
    :param step; Number of steps that receive_all is called
    :param length; Length of incoming message
    :returns Response object.
    """
    if step == 0:
        # Read length of the string first
        try:
            string = client.recv(4)
            length = int(string)
        except ValueError:
            return Response(False, 'Received Length is not a valid integer.')
        return receive_all(client, data, step=1, length=length)
    else:
        while len(data) < length:
            d = client.recv(MAX_MESSAGE_SIZE)
            if not d:
                return Response(False, 'Broken connection to {}'.format(client.getpeername()))
            data += d

        try:
            received_message = Message()
            received_message.load(data)
            return Response(True, received_message)
        except:
            return Response(False, 'Deserializing expcetion: ' + sys.exc_info())


def send_msg(msg, sock):
    """
    :param msg; Message object that is being sent
    :param sock; A python socket to transfer data
    :returns bool.
    """
    # Add length of the string to the start. Also pad it to be at least 5 characters.
    try:
        msg = msg.dump()
    except:
        tools.log("Send_msg received wrong type of message")
        tools.log(sys.exc_info())
        return False

    length_of_msg = tools.buffer_(str(len(msg)), 4)
    try:
        sock.send(length_of_msg)
    except:
        tools.log("Failed to send length of message")
        tools.log(sys.exc_info())
        return False

    while msg:
        try:
            sent = sock.send(msg)
        except:
            tools.log('Peer at {} died'.format(sock.getpeername()))
            return False
        msg = msg[sent:]

    return True


def send_any(_object, sock):
    """
    Sends any object to destination socket.

    :param _object; Any object that is being sent. Transferred as message to :func:send_msg
    :param sock; A python socket to transfer data
    :returns bool.
    """
    return send_msg(Message(_type="Socket", _message=_object), sock)


def send_receive(msg, host='localhost', port=custom.api_port, counter=0):
    """
    Sends any object to destination socket and returns the received message.

    :param msg; Message object that is being sent
    :param port; Port of destination
    :param host; Address of destination
    :param counter; Number of attempts.
    :returns Object that is received.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setblocking(5)
    try:
        s.connect((host, port))
    except:
        return None

    res = send_any(msg, s)

    if not res:
        return None

    res = receive_all(s)

    if not res.is_successful():
        return send_error(msg, host, port, counter)
    else:
        return res.getData().getMessage()


def send_error(msg, host, port, counter):
    if counter > 3:
        tools.log('Maximum number of attempts is reached.\n'
                  '{}:{} could not get the message: {}'
                  .format(host, port, msg))
        return None
    return send_receive(msg, host, port, counter + 1)