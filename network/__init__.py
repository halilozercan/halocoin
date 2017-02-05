import socket
import sys
import time

import tools
from network.message import Message
from network.response import Response

MAX_MESSAGE_SIZE = 60000


def receive_all(client, data='', step=0, length=0):
    if step == 0:
        # Read length of the string first
        try:
            str = client.recv(4)
            print str
            length = int(str)
        except ValueError:
            tools.log('Received Length is not a valid integer.')
            return Response(False, "Length is not a valid integer")
        return receive_all(client, data, step=1, length=length)
    else:
        while len(data) < length:
            d = client.recv(MAX_MESSAGE_SIZE)
            if not d:
                return Response(False, 'Broken connection')
            data += d

        try:
            received_message = Message()
            received_message.load(data)
            return Response(True, received_message)
        except:
            tools.log('Deserializing expcetion: ' + sys.exc_info())
            return Response(False, 'Deserializing expcetion: ' + sys.exc_info())


def send_error(msg, port, host, counter):
    if counter > 3:
        return Response(False, 'could not get a response')
    return send_receive(msg, port, host, counter + 1)


def send_msg(msg, sock):
    # Add length of the string to the start. Also pad it to be at least 5 characters.
    try:
        msg = msg.dump()
    except:
        tools.log("Send_msg received wrong type of message")
        tools.log(sys.exc_info())
        return Response(False, "Message type invalid")

    length_of_msg = tools.buffer_(str(len(msg)), 4)
    try:
        sent = sock.send(length_of_msg)
    except:
        tools.log("Failed to send length of message")
        tools.log(sys.exc_info())
        return Response(False, "Could not send size")

    while msg:
        try:
            sent = sock.send(msg)
        except:
            return Response(False, 'Peer died')
        msg = msg[sent:]

    return Response(True)


def send_any(_object, sock):
    msg = Message(_type="Socket", _message=_object)
    return send_msg(msg, sock)


def send_receive(msg, port, host='localhost', counter=0):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setblocking(5)
    try:
        s.connect((host, port))
    except:
        return Response(False, 'cannot connect host:' + str(host) + ' port:' + str(port))

    res = send_any(msg, s)

    if not res.is_successful():
        res.setData(res.getData() + ': ' + str(msg))
        return res

    res = receive_all(s)

    if not res.is_successful():
        tools.log(res.getData() + ': ' + str(msg))
        return send_error(msg, port, host, counter)
    else:
        return res


def send_command(peer, msg):
    return send_receive(msg, peer[1], peer[0])
