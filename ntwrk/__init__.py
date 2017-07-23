import socket

from message import Message
from response import Response

MAX_MESSAGE_SIZE = 1024


def receive(sock, **kwargs):
    """
    Receives a socket message one time. This is not a SMP message.
    :param sock: Socket
    :param kwargs: 
    :return:
    """
    args = dict(
        timeout=-1,
        leftover=''
    )
    args.update(kwargs)

    try:
        if args['timeout'] != -1:
            sock.settimeout(args['timeout'])
        else:
            sock.settimeout(10)

        string = args['leftover']
        while string == '':
            received = sock.recv(MAX_MESSAGE_SIZE)
            if len(received) == 0:
                raise Exception('Socket is closed')
            string += received

        while string.find(':') < 0:
            received = sock.recv(MAX_MESSAGE_SIZE)
            if len(received) == 0:
                raise Exception('Socket is closed')
            string += received

        sep_loc = string.find(":")
        length = int(string[:sep_loc])
        string = string[sep_loc + 1:]

        while len(string) < length:
            received = sock.recv(MAX_MESSAGE_SIZE)
            if len(received) == 0:
                raise Exception('Socket is closed')
            string += received

        received_string = string[:length]
        leftover = string[length:]
        return Response(True, received_string), leftover

    except socket.timeout:
        # Timed out
        return Response(False, 'timeout'), ''
    except socket.error:
        return Response(False, 'gg'), ''
    except:
        import sys
        return Response(False, sys.exc_info()), ''


def send(_msg, sock):
    msg = str(_msg)

    sent = 0
    try:
        msg = str(len(msg)) + ":" + msg
        while sent < len(msg):
            sent += sock.send(msg[sent:])
    except:
        return False

    return sent == len(msg)


def connect(host='localhost', port=3699, ssl_args=None, unix_config=None):
    if unix_config is None:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    else:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.setblocking(5)
    if ssl_args is not None:
        import ssl
        s = ssl.wrap_socket(s, **ssl_args)
    try:
        if unix_config is None:
            s.connect((host, port))
        else:
            s.connect(unix_config['address'])
        return s
    except:
        return None
