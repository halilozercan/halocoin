"""This is the internal API. These are the words that are used to interact with a local node that you have the password to.
"""
import copy
import json
import socket
import sys

import time

import ntwrk
import tools
from ntwrk import Message
from service import Service, sync, threaded


class ApiService(Service):
    def __init__(self, engine):
        Service.__init__(self, name='api')
        self.engine = engine
        self.db = None
        self.blockchain = None
        self.miner = None

    def on_register(self):
        self.db = self.engine.db
        self.blockchain = self.engine.blockchain
        self.miner = self.engine.miner

        start = time.time()
        while start + 60 > time.time():
            try:
                self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.s.settimeout(1)
                self.s.bind(('localhost', self.engine.config['api.port']))
                self.s.listen(5)
                return True
            except:
                tools.log("Could not start API socket!")
                time.sleep(2)
        return True

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

    @sync
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
                account = tools.get_account(self.db, address)
                txs_in_pool = self.blockchain.tx_pool()
                tx['count'] = tools.known_tx_count(account, address, txs_in_pool)
            except:
                tx['count'] = 0
        if 'pubkeys' not in tx:
            tx['pubkeys'] = [pubkey]
        if 'signatures' not in tx:
            tx['signatures'] = [tools.sign(tools.det_hash(tx), privkey)]
        self.blockchain.tx_queue.put(tx)
        return 'Tx amount:{} to:{} added to the pool'.format(tx['amount'], tx['to'])

    @sync
    def peers(self):
        return self.db.get('peers_ranked')

    @sync
    def info(self, subject=None):
        if subject is None:
            return 'not enough inputs'
        if subject == 'myaddress':
            address = self.db.get('address')
        else:
            address = subject
        return tools.get_account(self.db, address)

    @sync
    def myaddress(self):
        return self.db.get('address')

    @sync
    def spend(self, amount=0, address=None):
        if amount == 0 and address is None:
            return 'not enough inputs'
        return self.easy_add_transaction({'type': 'spend', 'amount': int(amount), 'to': address})

    @sync
    def blockcount(self):
        return self.db.get('length')

    @sync
    def txs(self):
        return self.blockchain.tx_pool()

    @sync
    def pubkey(self):
        return self.db.get('pubkey')

    @sync
    def block(self, number=-1):
        if number == -1:
            number = self.db.get('length')
        return self.db.get(str(number))

    @sync
    def difficulty(self):
        return self.blockchain.target(self.db.get('length'))

    @sync
    def balance(self, address='default'):
        if address == 'default':
            address = self.db.get('address')
        account = tools.get_account(self.db, address)
        account = tools.update_account_with_txs(self.blockchain.tx_pool(), address, account)
        return account['amount']

    @sync
    def mybalance(self):
        return self.balance()

    @sync
    def stop(self):
        self.db.put('stop', True)
        self.engine.stop()
        return 'Shutting down'

    @sync
    def mine(self):
        if self.miner.get_state() == Service.RUNNING:
            self.miner.unregister()
            return 'Closed miner'
        else:
            self.miner.register()
            return 'Running miner'
