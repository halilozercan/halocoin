"""This is the internal API. These are the words that are used to interact with a local node that you have the password to.
"""
import copy
import json
import socket
import sys

import ntwrk
import tools
from account import AccountService
from blockchain import BlockchainService
from ntwrk import Message
from service import Service, threaded


def blockchain_synced(func):
    def wrapper(self, *args, **kwargs):
        if self.blockchain.get_chain_state() == BlockchainService.IDLE:
            return func(self, *args, **kwargs)
        else:
            return 'Blockchain is syncing. This method is not reliable while operation continues.'

    return wrapper


class ApiService(Service):
    def __init__(self, engine):
        Service.__init__(self, name='api')
        self.engine = engine
        self.db = None
        self.blockchain = None
        self.account = None
        self.miner = None

    def on_register(self):
        self.db = self.engine.db
        self.blockchain = self.engine.blockchain
        self.account = self.engine.account
        self.miner = self.engine.miner

        try:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.s.settimeout(1)
            self.s.bind(('localhost', self.engine.config['api.port']))
            self.s.listen(5)
            return True
        except:
            return False

    def on_close(self):
        try:
            self.s.shutdown(socket.SHUT_RDWR)
            self.s.close()
        except:
            print sys.exc_info()

    @threaded
    def listen(self):
        try:
            client_sock, address = self.s.accept()
            response, leftover = ntwrk.receive(client_sock)
            if response.getFlag():
                message = Message.from_yaml(response.getData())
                request = json.loads(message.get_body())
                try:
                    if hasattr(self, request['action']):
                        kwargs = copy.deepcopy(request)
                        del kwargs['action']
                        result = getattr(self, request['action'])(**kwargs)
                    else:
                        result = 'Received action is not valid'
                except:
                    result = 'Something went wrong while evaluating.\n' + str(sys.exc_info())
                    tools.log(result)
                response = Message(headers={'ack': message.get_header('id')},
                                   body=result)
                ntwrk.send(response, client_sock)
                client_sock.shutdown(socket.SHUT_RDWR)
                client_sock.close()
        except:
            pass

    def easy_add_transaction(self, tx_orig, privkey='default'):
        tx = copy.deepcopy(tx_orig)
        if privkey in ['default', 'Default']:
            if self.db.exists('privkey'):
                privkey = self.db.get('privkey')
            else:
                return ('no private key is known, so the tx cannot be signed. Here is the tx: \n' + str(
                    tools.package(tx_orig).encode('base64').replace('\n', '')))
        pubkey = tools.privtopub(privkey)
        address = tools.make_address([pubkey], 1)
        if 'count' not in tx:
            try:
                tx['count'] = self.account.known_tx_count(address)
            except:
                tx['count'] = 0
        if 'pubkeys' not in tx:
            tx['pubkeys'] = [pubkey]
        if 'signatures' not in tx:
            tx['signatures'] = [tools.sign(tools.det_hash(tx), privkey)]
        self.blockchain.tx_queue.put(tx)
        return 'Tx amount:{} to:{} added to the pool'.format(tx['amount'], tx['to'])

    def peers(self):
        return self.db.get('peers_ranked')

    @blockchain_synced
    def info(self, subject=None):
        if subject is None:
            return 'not enough inputs'
        if subject == 'myaddress':
            address = self.db.get('address')
        else:
            address = subject
        return self.account.get_account(address)

    def myaddress(self):
        return self.db.get('address')

    @blockchain_synced
    def invalidate(self, address=None):
        if address is None:
            address = self.db.get('address')
        self.account.invalidate_cache(address)
        account = self.account.get_account(address)
        account = AccountService.update_account_with_txs(address,
                                                         account,
                                                         self.blockchain.tx_pool(),
                                                         only_outgoing=True)
        return account['amount']

    @blockchain_synced
    def history(self, address=None):
        if address is None:
            address = self.db.get('address')
        account = self.account.get_account(address)
        txs = {
            "send": [],
            "recv": [],
            "mine": []
        }
        for block_index in reversed(account['tx_blocks']):
            block = self.db.get(str(block_index))
            for tx in block['txs']:
                tx['block'] = block_index
                owner = tools.tx_owner_address(tx)
                if owner == address:
                    txs['send'].append(tx)
                elif tx['type'] == 'spend' and tx['to'] == address:
                    txs['recv'].append(tx)
        for block_index in reversed(account['mined_blocks']):
            block = self.db.get(str(block_index))
            for tx in block['txs']:
                tx['block'] = block_index
                owner = tools.tx_owner_address(tx)
                if owner == address:
                    txs['mine'].append(tx)
        return txs

    @blockchain_synced
    def spend(self, amount=0, address=None, message=''):
        if amount == 0 and address is None:
            return 'not enough inputs'
        return self.easy_add_transaction({'type': 'spend', 'amount': int(amount),
                                          'to': address, 'message': message})

    def blockcount(self):
        return self.db.get('length')

    def txs(self):
        return self.blockchain.tx_pool()

    def pubkey(self):
        return self.db.get('pubkey')

    def block(self, number=-1):
        if number == -1:
            number = self.db.get('length')
        return self.db.get(str(number))

    @blockchain_synced
    def difficulty(self):
        return self.blockchain.target(self.db.get('length'))

    @blockchain_synced
    def balance(self, address='default'):
        if address == 'default':
            address = self.db.get('address')
        account = self.account.get_account(address)
        account = AccountService.update_account_with_txs(address,
                                                         account,
                                                         self.blockchain.tx_pool(),
                                                         only_outgoing=True)
        return account['amount']

    @blockchain_synced
    def mybalance(self):
        return self.balance()

    def stop(self):
        self.db.put('stop', True)
        self.engine.stop()
        return 'Shutting down'

    def mine(self):
        if self.miner.get_state() == Service.RUNNING:
            self.miner.unregister()
            return 'Closed miner'
        else:
            self.miner.register()
            return 'Running miner'
