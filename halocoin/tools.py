"""A bunch of functions that are used by multiple threads.
"""
import os
import random
import sys
from json import dumps as package, loads as unpackage

import copy

import struct

import StringIO

import custom
import hashlib
import logging
import pt


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def init_logging(working_dir):
    if custom.DEBUG:
        logging.basicConfig(level=logging.INFO,
                            format='%(levelname)s on %(asctime)s\n%(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p')
    else:
        logging.basicConfig(filename=os.path.join(working_dir, custom.log_file),
                            level=logging.DEBUG,
                            format='%(levelname)s on %(asctime)s\n%(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p')


def get_default_dir():
    from os.path import expanduser
    home = expanduser("~")
    return os.path.join(home, '.halocoin')


def add_peer_ranked(peer, current_peers):
    if peer[0] not in map(lambda x: x[0][0], current_peers):
        current_peers.append([peer, 5, '0', 0])
    return current_peers


def log(message):
    if isinstance(message, Exception):
        logging.exception(message)
    else:
        logging.info('{}'.format(message))


def tx_owner_address(tx):
    return make_address(tx['pubkeys'], len(tx['signatures']))


def sign(msg, privkey):
    return pt.ecdsa_sign(msg, privkey)


def privtopub(privkey):
    return pt.privtopub(privkey)


def hash_(x):
    return hashlib.sha384(x).hexdigest()[0:64]


def det_hash(x):
    """Deterministically takes sha256 of dict, list, int, or string."""
    return hash_(package(x, sort_keys=True))


def hash_without_nonce(block):
    a = copy.deepcopy(block)
    a.pop('nonce')
    return {'nonce': block['nonce'], 'halfHash': det_hash(a)}


def base58_encode(num):
    num = int(num, 16)
    alphabet = '123456789abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ'
    base_count = len(alphabet)
    encode = ''
    if num < 0:
        return ''
    while (num >= base_count):
        mod = num % base_count
        encode = alphabet[mod] + encode
        num = num / base_count
    if num:
        encode = alphabet[num] + encode
    return encode


def make_address(pubkeys, n):
    """n is the number of pubkeys required to spend from this address."""
    return (str(len(pubkeys)) + str(n) +
            base58_encode(det_hash({str(n): pubkeys}))[0:29])


def buffer_(str_to_pad, size):
    return str_to_pad.rjust(size, '0')


def exponential_random(r, i=0):
    if random.random() < r:
        return i
    return exponential_random(r, i + 1)


def median(mylist):
    if len(mylist) < 1:
        return 0
    return sorted(mylist)[len(mylist) / 2]


def daemonize(f):
    pid = os.fork()
    if pid == 0:
        f()
    else:
        sys.exit(0)


from Crypto.Cipher import AES


def encrypt(key, content, chunksize=64 * 1024):
    infile = StringIO.StringIO(content)
    outfile = StringIO.StringIO()
    key = hashlib.sha256(key).digest()

    iv = ''.join(chr(random.randint(0, 0xFF)) for i in range(16))
    encryptor = AES.new(key, AES.MODE_CBC, iv)
    filesize = len(content)

    outfile.write(struct.pack('<Q', filesize))
    outfile.write(iv)
    while True:
        chunk = infile.read(chunksize)
        if len(chunk) == 0:
            break
        elif len(chunk) % 16 != 0:
            chunk += ' ' * (16 - len(chunk) % 16)

            outfile.write(encryptor.encrypt(chunk))
    return outfile.getvalue()


def decrypt(key, content, chunksize=24 * 1024):
    infile = StringIO.StringIO(content)
    outfile = StringIO.StringIO()

    key = hashlib.sha256(key).digest()

    origsize = struct.unpack('<Q', infile.read(struct.calcsize('Q')))[0]
    iv = infile.read(16)
    decryptor = AES.new(key, AES.MODE_CBC, iv)

    while True:
        chunk = infile.read(chunksize)
        if len(chunk) == 0:
            break
        outfile.write(decryptor.decrypt(chunk))

    outfile.truncate(origsize)
    return outfile.getvalue()
