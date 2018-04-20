import copy
import hashlib
import json
import logging
import os
import random
import struct
import time
from uuid import UUID

from fastecdsa import curve
from fastecdsa.point import Point

alphabet = '123456789abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ'


class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (bytes, bytearray)):
            return {
                "_type": type(obj).__name__,
                "value": obj.hex()
            }
        elif isinstance(obj, UUID):
            return {
                "_type": 'UUID',
                "value": str(obj)
            }

        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


class ComplexDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj):
        if '_type' not in obj:
            return obj
        type = obj['_type']
        if type == 'bytearray':
            return bytearray.fromhex(obj['value'])
        elif type == 'bytes':
            return bytes(bytearray.fromhex(obj['value']))
        elif type == 'UUID':
            return UUID(obj['value'], version=4)

        return obj


def serialize(obj):
    return json.dumps(obj, cls=ComplexEncoder, sort_keys=True)


def deserialize(obj):
    return json.loads(obj, cls=ComplexDecoder)


def init_logging(DEBUG, working_dir, log_file):
    if DEBUG:
        logging.basicConfig(level=logging.INFO,
                            format='%(levelname)s on %(asctime)s\n%(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p')
    else:
        print("Current working directory: " + os.getcwd())
        print("Working_dir: " + working_dir)
        logging.basicConfig(filename=os.path.join(working_dir, log_file),
                            level=logging.DEBUG,
                            format='%(levelname)s on %(asctime)s\n%(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p')
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    log = logging.getLogger('docker')
    log.setLevel(logging.ERROR)


def get_default_dir():
    from os.path import expanduser
    home = expanduser("~")
    default_dir = os.path.join(home, '.halocoin')
    return os.environ.get("HALOCOIN_DATA_DIR", default_dir)


def get_default_dir_cli():
    from os.path import expanduser
    home = expanduser("~")
    default_dir = os.path.join(home, '.halocoincli')
    return os.environ.get("HALOCOIN_CLI_DIR", default_dir)


def log(message):
    import traceback
    if isinstance(message, Exception):
        logging.exception(message)
        logging.critical(traceback.format_exc())
    else:
        logging.info('{}'.format(message))


def tx_owner_address(tx):
    return make_address(tx['pubkeys'], len(tx['signatures']))


def reward_owner_name(tx):
    if 'auth' in tx:
        return tx['auth']
    else:
        return get_commonname_from_certificate(tx['certificate'])


def custom_verify(r, s, msg, Q):
    from fastecdsa import _ecdsa
    from fastecdsa.ecdsa import EcdsaError

    if isinstance(Q, tuple):
        Q = Point(Q[0], Q[1], curve)

    # validate Q, r, s (Q should be validated in constructor of Point already but double check)
    if not curve.secp256k1.is_point_on_curve((Q.x, Q.y)):
        raise EcdsaError('Invalid public key, point is not on curve {}'.format(curve.secp256k1.name))
    elif r > curve.secp256k1.q or r < 1:
        raise EcdsaError(
            'Invalid Signature: r is not a positive integer smaller than the curve order')
    elif s > curve.secp256k1.q or s < 1:
        raise EcdsaError(
            'Invalid Signature: s is not a positive integer smaller than the curve order')

    return _ecdsa.verify(
        str(r),
        str(s),
        msg,
        str(Q.x),
        str(Q.y),
        str(curve.secp256k1.p),
        str(curve.secp256k1.a),
        str(curve.secp256k1.b),
        str(curve.secp256k1.q),
        str(curve.secp256k1.gx),
        str(curve.secp256k1.gy)
    )


def custom_sign(msg, d):
    """Sign a message using the elliptic curve digital signature algorithm.

    The elliptic curve signature algorithm is described in full in FIPS 186-4 Section 6. Please
    refer to http://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.186-4.pdf for more information.

    Args:
        |  msg (str): Hexadecimal representation of an object.
        |  d (long): The ECDSA private key of the signer.
        |  curve (fastecdsa.curve.Curve): The curve to be used to sign the message.
        |  hashfunc (_hashlib.HASH): The hash function used to compress the message.
    """
    # generate a deterministic nonce per RFC6979
    from fastecdsa.util import RFC6979
    from fastecdsa import _ecdsa
    rfc6979 = RFC6979(msg, d, curve.secp256k1.q, hashlib.sha256)
    k = rfc6979.gen_nonce()

    r, s = _ecdsa.sign(
        msg,
        str(d),
        str(k),
        str(curve.secp256k1.p),
        str(curve.secp256k1.a),
        str(curve.secp256k1.b),
        str(curve.secp256k1.q),
        str(curve.secp256k1.gx),
        str(curve.secp256k1.gy)
    )
    return (int(r), int(s))


def sign(msg, privkey):
    from ecdsa import SigningKey
    from ecdsa.util import sigencode_string
    if isinstance(privkey, bytes):
        privkey = SigningKey.from_string(privkey)
    r, s = custom_sign(msg.hex(), privkey.privkey.secret_multiplier)
    return sigencode_string(r, s, curve.secp256k1.q)


def sign_verify(message, signature, pubkey):
    from ecdsa import VerifyingKey, SECP256k1
    from ecdsa.util import sigdecode_string

    if isinstance(pubkey, (str, bytes)):
        pubkey = VerifyingKey.from_string(pubkey, curve=SECP256k1)

    r, s = sigdecode_string(signature, pubkey.pubkey.order)
    try:
        fast_pubkey = Point(pubkey.pubkey.point.x(), pubkey.pubkey.point.y(), curve.secp256k1)
        return custom_verify(r, s, message.hex(), fast_pubkey)
    except Exception as e:
        return False


def block_reward(length):
    from halocoin import custom
    import math
    a = length // custom.halve_at
    b = custom.block_reward / math.pow(2, a)
    return int(b)


def det_hash(x):
    """Deterministically takes sha256 of dict, list, int, or string."""
    return hashlib.sha384(serialize(x).encode()).digest()[0:32]


def hash_without_nonce(block):
    a = copy.deepcopy(block)
    a.pop('nonce')
    return {'nonce': block['nonce'], 'halfHash': det_hash(a)}


def base58_encode(num):
    num = int(num.hex(), 16)
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


def is_address_valid(address):
    if len(address) < 32:
        return False
    if not str(address[:2]).isdigit():
        return False
    if not str(address[2:]).isalnum():
        return False
    return True


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
    infile = io.BytesIO()
    infile.write(content)
    infile.seek(0)
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


def check_certificate_chain(intermediate_cert_pem):
    from halocoin import custom
    from OpenSSL.crypto import load_certificate, FILETYPE_PEM, X509Store, X509StoreContext
    root_cert = load_certificate(FILETYPE_PEM, custom.root_cert_pem)
    intermediate_cert = load_certificate(FILETYPE_PEM, intermediate_cert_pem)
    try:
        store = X509Store()
        store.add_cert(root_cert)
        store_ctx = X509StoreContext(store, intermediate_cert)
        store_ctx.verify_certificate()
        return True
    except:
        return False


def get_pubkey_from_certificate(intermediate_cert_pem):
    from OpenSSL.crypto import load_certificate, FILETYPE_PEM, dump_publickey
    from ecdsa import VerifyingKey
    intermediate_cert = load_certificate(FILETYPE_PEM, intermediate_cert_pem)
    pubkey_pem = dump_publickey(FILETYPE_PEM, intermediate_cert.get_pubkey())
    return VerifyingKey.from_pem(pubkey_pem)


def get_commonname_from_certificate(intermediate_cert_pem):
    from OpenSSL.crypto import load_certificate, FILETYPE_PEM
    from slugify import slugify
    intermediate_cert = load_certificate(FILETYPE_PEM, intermediate_cert_pem)
    return slugify(intermediate_cert.get_subject().commonName)


last = 0


def echo(text):
    global last
    print(text)
    last = time.time()


def techo(text):
    global last
    if last == 0:
        print(text)
    else:
        print(text + ": {}".format(time.time() - last))
        last = time.time()


def readable_bytes(num, suffix='B'):
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


def get_locked_file():
    import sys
    if "linux" in sys.platform:
        return "/tmp/halocoin.lock"
    elif "win" in sys.platform:
        return os.path.join("%TEMP%", "halocoin.lock")


def get_engine_info_file():
    import sys
    if "linux" in sys.platform:
        return "/tmp/halocoin_info.lock"
    elif "win" in sys.platform:
        return os.path.join("%TEMP%", "halocoin_info.lock")