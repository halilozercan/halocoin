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


# print(json.dumps(x, indent=3, sort_keys=True))  for pretty printing
def update_account_with_txs(txs, address, account):
    for tx in txs:
        owner = tx_owner_address(tx)
        if tx['type'] == 'mint' and owner == address:
            account['amount'] += custom.block_reward
        elif tx['type'] == 'spend':
            if owner == address:
                account['amount'] -= tx['amount']
                account['amount'] -= custom.fee
                account['count'] += 1
            elif tx['to'] == address:
                account['amount'] += tx['amount']
                account['count'] += 1
    return account


def fee_check(tx, txs_in_pool, acc):
    address = tx_owner_address(tx)
    copy_acc = copy.deepcopy(acc)
    acc = update_account_with_txs(txs_in_pool + [tx], address, copy_acc)
    if int(acc['amount']) < 0:
        log('insufficient money')
        return False
    # if tx['amount'] + custom.fee > acc['amount']:
    #    return False
    return True


def get_account(db, address):
    account = {'count': 0, 'amount': 0}
    current_length = int(db.get('length'))
    last_cache_length = int(db.get('last_cache_length'))
    last_blocks_indices = range(last_cache_length, current_length+1)
    for i in last_blocks_indices:
        block = db.get(str(i))
        account = update_account_with_txs(block['txs'], address, account)
    cached_account = db.get(address)
    if cached_account:
        account['count'] += cached_account['count']
        account['amount'] += cached_account['amount']
    return account


def known_tx_count(account, address, txs_in_pool):
    # TODO: address is a address object from database. Find the real address string inside
    # Returns the number of transactions that pubkey has broadcast.
    def number_of_unconfirmed_txs(address):
        return len(filter(lambda t: address == tx_owner_address(t), txs_in_pool))

    return account['count'] + number_of_unconfirmed_txs(address)


def get_dict_nested(loc, dic):
    if loc == []:
        return dic
    return get_dict_nested(loc[1:], dic[loc[0]])


def set_dict_nested(loc, dic, val):
    get_dict_nested(loc[:-1], dic)[loc[-1]] = val
    return dic


def add_peer(peer, current_peers):
    if peer[0][0] not in map(lambda x: x[0][0], current_peers):
        log('add peer: ' + str(peer))
        current_peers.append([peer, 5, '0', 0])
    return current_peers


def dump_out(queue):
    while not queue.empty():
        try:
            queue.get(False)
        except:
            pass


if not custom.DEBUG:
    logging.basicConfig(filename=custom.log_file, level=logging.INFO)


def log(junk):
    if isinstance(junk, Exception):
        logging.exception(junk)
    else:
        logging.info(str(junk))


def can_unpack(o):
    try:
        unpackage(o)
        return True
    except:
        return False


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


def is_number(s):
    try:
        int(s)
        return True
    except:
        return False


def fork_check(newblocks, length, block):
    recent_hash = det_hash(block)
    their_hashes = map(lambda x: x['prevHash'] if x['length'] > 0 else 0, newblocks) + [det_hash(newblocks[-1])]
    b = (recent_hash not in their_hashes) and newblocks[0]['length'] - 1 < length < newblocks[-1]['length']
    return b


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
