"""This is the internal API. These are the words that are used to interact with a local node that you have the password to.
"""
import copy
import json
import socket
import sys

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

    def on_register(self):
        self.db = self.engine.db
        self.blockchain = self.engine.blockchain

        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.settimeout(1)
        self.s.bind(('localhost', self.engine.config['api.port']))
        self.s.listen(5)

    def on_close(self):
        try:
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
                response = Message(headers={'ack': message.get_header('id')},
                                   body=result)
                ntwrk.send(response, client_sock)
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
                tx['count'] = tools.count(self.db.get(address), address, self.db.get('txs'))
            except:
                tx['count'] = 1
        if 'pubkeys' not in tx:
            tx['pubkeys'] = [pubkey]
        if 'signatures' not in tx:
            tx['signatures'] = [tools.sign(tools.det_hash(tx), privkey)]
        return self.blockchain.tx_queue.put(tx)

    @sync
    def peers(self):
        return self.db.get('peers_ranked')

    @sync
    def info(self, args):
        if len(args) < 1:
            return 'not enough inputs'
        if args[0] == 'myaddress':
            address = self.db.get('address')
        else:
            address = args[0]
        return self.db.get(address)

    @sync
    def myaddress(self):
        return self.db.get('address')

    @sync
    def spend(self, args):
        if len(args) < 2:
            return 'not enough inputs'
        return self.easy_add_transaction({'type': 'spend', 'amount': int(args[0]), 'to': args[1]})

    @sync
    def pushtx(self, args):
        tx = tools.unpackage(args[0].decode('base64'))
        if len(args) == 1:
            return self.easy_add_transaction(tx)
        privkey = tools.det_hash(args[1])
        return self.easy_add_transaction(tx, privkey)

    @sync
    def blockcount(self):
        return self.db.get('length')

    @sync
    def txs(self):
        return self.db.get('txs')

    @sync
    def difficulty(self):
        return self.blockchain.target(self.db.get('length'))

    @sync
    def balance(self, address='default'):
        if address == 'default':
            address = self.db.get('address')
        account = self.db.get(address)
        if account is None:
            return 0
        else:
            return account['amount'] - tools.total_spendings_of_address(self.db.get('txs'), address)

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
        m = not (self.db.get('mine'))
        self.db.put('mine', m)
        if m:
            m = 'on'
        else:
            m = 'off'
        return 'miner is currently: ' + m

    @sync
    def pass_(self):
        return ' '

    @sync
    def error_(self):
        # return error
        # Previously an error object was returned. No idea what it was about
        return "error"
