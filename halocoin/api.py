import copy
import json
import threading

import requests
import sys
from jsonrpc import JSONRPCResponseManager, dispatcher
from werkzeug.serving import run_simple
from werkzeug.wrappers import Request, Response

import tools
from account import AccountService
from blockchain import BlockchainService
from service import Service

_engine = None


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
                                     kwargs={'hostname': 'localhost',
                                             'port': engine.config['api.port'],
                                             'application': application})
    listen_thread.start()


def shutdown():
    url = "http://localhost:" + str(_engine.config['api.port']) + "/jsonrpc"
    headers = {'content-type': 'application/json'}

    # Example echo method
    payload = {
        "method": "shutdown",
        "params": [],
        "jsonrpc": "2.0",
        "id": 0,
    }
    requests.post(url, data=json.dumps(payload), headers=headers).json()


def easy_add_transaction(tx_orig, privkey):
    tx = copy.deepcopy(tx_orig)
    pubkey = tools.privtopub(privkey)
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
def peers():
    return _engine.account.get_peers()


@dispatcher.add_method
@blockchain_synced
def invalidate(address=None):
    if address is None:
        address = _engine.db.get('address')
    _engine.account.invalidate_cache(address)
    account = _engine.account.get_account(address)
    account = AccountService.update_account_with_txs(address,
                                                     account,
                                                     _engine.blockchain.tx_pool(),
                                                     only_outgoing=True)
    return account['amount']


@dispatcher.add_method
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
    return easy_add_transaction({'type': 'spend', 'amount': int(amount),
                                 'to': address, 'message': message},
                                privkey=wallet['privkey'])


@dispatcher.add_method
def blockcount():
    return dict(length=_engine.db.get('length'),
                known_length=_engine.db.get('known_length'))


@dispatcher.add_method
def txs():
    return _engine.blockchain.tx_pool()


@dispatcher.add_method
def pubkey():
    return _engine.db.get('pubkey')


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
def block(number="default"):
    if "-" in number:
        _from = int(number.split("-")[0])
        _to = int(number.split("-")[1])
        _to = min(_from + 50, _to)
        return [_engine.db.get(str(i)) for i in range(_from, _to)]
    else:
        if number == "default":
            number = _engine.db.get('length')
        number = int(number)
        return [_engine.db.get(str(number))]


@dispatcher.add_method
@blockchain_synced
def difficulty():
    return _engine.blockchain.target(_engine.db.get('length'))


@dispatcher.add_method
@blockchain_synced
def balance(address=None):
    if address is None:
        address = _engine.db.get('address')
    account = _engine.account.get_account(address)
    account = AccountService.update_account_with_txs(address,
                                                     account,
                                                     _engine.blockchain.tx_pool(),
                                                     only_outgoing=True)
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
