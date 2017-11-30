"""
Notes:
    Because json cannot serialize bytes-like objects,
    wallet objects should be passed into JSON-RPC functions
    as serialized. They will be encoded with yaml.
"""
import json
import threading

import requests
from jsonrpc import JSONRPCResponseManager, dispatcher
from werkzeug.serving import run_simple
from werkzeug.wrappers import Request, Response

from halocoin import tools
from halocoin.blockchain import BlockchainService
from halocoin.service import Service

_engine = None


class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (bytes, bytearray)):
            return obj.hex()
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


def json_sanitizer(func):
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        initial = json.dumps(result, cls=ComplexEncoder)
        return json.loads(initial)

    # To keep the function name same for RPC helper
    wrapper.__name__ = func.__name__

    return wrapper


def blockchain_synced(func):
    def wrapper(*args, **kwargs):
        if _engine.blockchain.get_chain_state() == BlockchainService.IDLE:
            return func(*args, **kwargs)
        else:
            return 'Blockchain is syncing. This method is not reliable while operation continues.\n' + \
                   str(_engine.db.get('length')) + '-' + str(_engine.db.get('known_length'))

    # To keep the function name same for RPC helper
    wrapper.__name__ = func.__name__

    return wrapper


@Request.application
def application(request):
    def shutdown():
        func = request.environ.get('werkzeug.server.shutdown')
        if func is None:
            raise RuntimeError('Not running with the Werkzeug Server')
        func()

    dispatcher["shutdown"] = shutdown

    response = JSONRPCResponseManager.handle(
        request.data, dispatcher)
    return Response(response.json, mimetype='application/json')


def run(engine):
    global _engine
    _engine = engine
    listen_thread = threading.Thread(target=run_simple,
                                     kwargs={'hostname': '0.0.0.0',
                                             'port': engine.config['api']['port'],
                                             'application': application})
    listen_thread.start()


def shutdown():
    url = "http://localhost:" + str(_engine.config['api']['port']) + "/jsonrpc"
    headers = {'content-type': 'application/json'}

    # Example echo method
    payload = {
        "method": "shutdown",
        "params": [],
        "jsonrpc": "2.0",
        "id": 0,
    }
    requests.post(url, data=json.dumps(payload), headers=headers).json()


@dispatcher.add_method
@json_sanitizer
def peers():
    return _engine.account.get_peers()


@dispatcher.add_method
def node_id():
    return _engine.db.get('node_id')


@dispatcher.add_method
@json_sanitizer
@blockchain_synced
def history(address=None):
    if address is None:
        address = _engine.db.get('address')
    account = _engine.account.get_account(address)
    txs = {
        "send": [],
        "recv": [],
        "mine": []
    }
    for block_index in reversed(account['tx_blocks']):
        block = _engine.db.get(str(block_index))
        for tx in block['txs']:
            tx['block'] = block_index
            owner = tools.tx_owner_address(tx)
            if owner == address:
                txs['send'].append(tx)
            elif tx['type'] == 'spend' and tx['to'] == address:
                txs['recv'].append(tx)
    for block_index in reversed(account['mined_blocks']):
        block = _engine.db.get(str(block_index))
        for tx in block['txs']:
            tx['block'] = block_index
            owner = tools.tx_owner_address(tx)
            if owner == address:
                txs['mine'].append(tx)
    return txs


@dispatcher.add_method
@blockchain_synced
def send(amount=0, address=None, message='', wallet=None):
    if amount == 0 or address is None or wallet is None:
        return 'A problem was occurred while processing inputs'
    tx = {'type': 'spend', 'amount': int(amount),
          'to': address, 'message': message}
    wallet = tools.wallet_from_str(wallet)
    privkey, pubkey = tools.get_key_pairs_from_wallet(wallet)
    address = tools.make_address([pubkey], 1)
    if 'count' not in tx:
        try:
            tx['count'] = _engine.account.known_tx_count(address)
        except:
            tx['count'] = 0
    if 'pubkeys' not in tx:
        tx['pubkeys'] = [pubkey]
    if 'signatures' not in tx:
        tx['signatures'] = [tools.sign(tools.det_hash(tx), privkey)]
    _engine.blockchain.tx_queue.put(tx)
    return 'Tx amount:{} to:{} added to the pool'.format(tx['amount'], tx['to'])


@dispatcher.add_method
def blockcount():
    return dict(length=_engine.db.get('length'),
                known_length=_engine.db.get('known_length'))


@dispatcher.add_method
@json_sanitizer
def txs():
    return _engine.blockchain.tx_pool()


@dispatcher.add_method
def delete_block(number="0"):
    counts = [0, 0]
    for i in range(int(number)):
        try:
            _engine.blockchain.delete_block()
            counts[0] += 1
        except:
            counts[1] += 1
    return "Removed {}, Not removed {}".format(counts[0], counts[1])


@dispatcher.add_method
@json_sanitizer
def block(number="default"):
    if "-" in number:
        _from = int(number.split("-")[0])
        _to = int(number.split("-")[1])
        _to = min(_from + 50, _to)
        result = []
        for i in range(_from, _to):
            _block = _engine.db.get(str(i))
            if _block is not None:
                result.append(_block)
        return result
    else:
        if number == "default":
            number = _engine.db.get('length')
        number = int(number)
        return [_engine.db.get(str(number))]


@dispatcher.add_method
@json_sanitizer
@blockchain_synced
def difficulty():
    return _engine.blockchain.target(_engine.db.get('length'))


@dispatcher.add_method
@blockchain_synced
def balance(address=None):
    if address is None:
        address = _engine.db.get('address')
    account = _engine.account.get_account(address, apply_tx_pool=True)
    return account['amount']


@dispatcher.add_method
def stop():
    _engine.db.put('stop', True)
    _engine.stop()
    return 'Shutting down'


@dispatcher.add_method
def start_miner(wallet=None):
    if _engine.miner.get_state() == Service.RUNNING:
        return 'Miner is already running.'
    elif wallet is None:
        return 'Given wallet is not valid.'
    else:
        wallet = tools.wallet_from_str(wallet)
        _engine.miner.set_wallet(wallet)
        _engine.miner.register()
        return 'Running miner'


@dispatcher.add_method
def stop_miner():
    if _engine.miner.get_state() == Service.RUNNING:
        _engine.miner.unregister()
        return 'Closed miner'
    else:
        return 'Miner is not running.'
