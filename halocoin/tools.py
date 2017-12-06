import copy
import hashlib
import logging
import os
import random
import struct

from halocoin import custom


def init_logging(DEBUG, working_dir, log_file):
    if DEBUG:
        logging.basicConfig(level=logging.INFO,
                            format='%(levelname)s on %(asctime)s\n%(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p')
    else:
        logging.basicConfig(filename=os.path.join(working_dir, log_file),
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
    from ecdsa import SigningKey
    if isinstance(privkey, bytes):
        privkey = SigningKey.from_string(privkey)
    return privkey.sign(msg)


def det_hash(x):
    """Deterministically takes sha256 of dict, list, int, or string."""
    import yaml
    pack = yaml.dump(x).encode()
    return hashlib.sha384(pack).digest()[0:32]


def hash_without_nonce(block):
    a = copy.deepcopy(block)
    a.pop('nonce')
    return {'nonce': block['nonce'], 'halfHash': det_hash(a)}


def base58_encode(num):
    num = int(num.hex(), 16)
    alphabet = '123456789abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ'
    base_count = len(alphabet)
    encode = ''
    if num < 0:
        return ''
    while num >= base_count:
        mod = num % base_count
        encode = alphabet[mod] + encode
        num = num // base_count
    if num:
        encode = alphabet[num] + encode
    return encode


def make_address(pubkeys, n):
    """
    n is the number of pubkeys required to spend from this address.
    This function is compatible with string or VerifyingKey representation of keys.
    """
    from ecdsa import VerifyingKey
    pubkeys_as_string = [p.to_string() if isinstance(p, VerifyingKey) else p for p in pubkeys]
    hashed = det_hash({str(n): pubkeys_as_string})
    return str(len(pubkeys_as_string)) + str(n) + base58_encode(hashed[0:29])


def buffer_(str_to_pad, size):
    return str_to_pad.rjust(size, '0')


def exponential_random(r, i=0):
    if random.random() < r:
        return i
    return exponential_random(r, i + 1)


def median(mylist):
    if len(mylist) < 1:
        return 0
    return sorted(mylist)[len(mylist) // 2]


def hex_sum(a, b):
    # Sum of numbers expressed as hexidecimal strings
    if isinstance(a, bytearray):
        a = a.hex()
        b = b.hex()
    return buffer_(format(int(a, 16) + int(b, 16), 'x'), 64)


def hex_invert(n):
    # Use double-size for division, to reduce information leakage.
    if isinstance(n, bytearray):
        n = n.hex()
    return buffer_(format(int('f' * 128, 16) // int(n, 16), 'x'), 64)


def encrypt(key, content, chunksize=64 * 1024):
    import io
    import Crypto.Random
    from Crypto.Cipher import AES
    infile = io.BytesIO(content.encode())
    outfile = io.BytesIO()
    if isinstance(key, str):
        key = key.encode()
    key = hashlib.sha256(key).digest()

    iv = Crypto.Random.OSRNG.posix.new().read(AES.block_size)
    encryptor = AES.new(key, AES.MODE_CBC, iv)
    filesize = len(content)

    outfile.write(struct.pack('<Q', filesize))
    outfile.write(iv)
    while True:
        chunk = infile.read(chunksize)
        if len(chunk) == 0:
            break
        elif len(chunk) % 16 != 0:
            chunk += '\0'.encode() * (16 - len(chunk) % 16)

            outfile.write(encryptor.encrypt(chunk))
    return outfile.getvalue()


def decrypt(key, content, chunksize=24 * 1024):
    from Crypto.Cipher import AES
    import io
    infile = io.BytesIO(content)
    outfile = io.BytesIO()

    if isinstance(key, str):
        key = key.encode()
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


def parse_wallet(wallet_file, pw=None):
    from getpass import getpass
    import yaml
    wallet_encrypted_content = wallet_file.read()
    if pw is None:
        while True:
            try:
                wallet_pw = getpass('Wallet password: ')

                wallet = yaml.load(decrypt(wallet_pw, wallet_encrypted_content).decode())
                break
            except ValueError:
                print('Wrong password')
    else:
        wallet = yaml.load(decrypt(pw, wallet_encrypted_content).decode())
    return wallet


def signature_verify(message, signature, pubkey):
    from ecdsa import VerifyingKey
    if isinstance(pubkey, str):
        pubkey = VerifyingKey.from_string(pubkey)
    elif isinstance(pubkey, bytes):
        pubkey = VerifyingKey.from_string(pubkey)

    if isinstance(pubkey, VerifyingKey):
        return pubkey.verify(signature, message)
    else:
        return False


def wallet_to_str(wallet):
    import yaml
    return yaml.dump(wallet)


def wallet_from_str(wallet_str):
    import yaml
    return yaml.load(wallet_str)


def byteslike_to_hexstr(input):
    if isinstance(input, (bytearray, bytes)):
        return input.hex()
    else:
        return str(input)


def validate_uuid4(uuid_string):

    """
    Validate that a UUID string is in
    fact a valid uuid4.
    Happily, the uuid module does the actual
    checking for us.
    It is vital that the 'version' kwarg be passed
    to the UUID() call, otherwise any 32-character
    hex string is considered valid.
    """

    try:
        from uuid import UUID
        val = UUID(uuid_string, version=4)
    except ValueError:
        # If it's a value error, then the string
        # is not a valid hex code for a UUID.
        return False

    # If the uuid_string is a valid hex code,
    # but an invalid uuid4,
    # the UUID.__init__ will convert it to a
    # valid uuid4. This is bad for validation purposes.

    return val.hex == uuid_string.replace('-', '')