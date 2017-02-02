import socket
import sys
import time

import tools
from network.message import Message
from network.response import Response

MAX_MESSAGE_SIZE = 60000


def receive_all(client, data=''):
    try:
        data += client.recv(MAX_MESSAGE_SIZE)
    except:
        time.sleep(0.001)
        tools.log('Receiving is not ready.')
        receive_all(client, data)

    if not data:
        return Response(False, 'Broken connection')
    if len(data) < 5:
        return receive_all(client, data)
    try:
        length = int(data[0:5])
    except:
        tools.log(sys.exc_info())
        return Response(False, 'No length is in prefix')

    data = data[5:]
    while len(data) < length:
        d = client.recv(MAX_MESSAGE_SIZE - len(data))
        if not d:
            return Response(False, 'Broken connection')
        data += d
    try:
        received_message = Message()
        received_message.load(data)
        return Response(True, received_message)
    except:
        return Response(False, 'Deserializing expcetion: ' + sys.exc_info())


def send_error(msg, port, host, counter):
    if counter > 3:
        return Response(False, 'could not get a response')
    return send_receive(msg, port, host, counter + 1)


def send_msg(msg, sock):
    data = tools.buffer_(str(len(msg.dump())), 5) + msg.dump()
    while data:
        time.sleep(0.0001)
        try:
            sent = sock.send(data)
        except:
            return Response(False, 'Peer died')
        data = data[sent:]
    return 0


def send_any(string, sock):
    msg = Message(_type="Socket", _message=string)
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
