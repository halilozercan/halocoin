"""This is the internal API. These are the words that are used to interact with a local node that you have the password to.
"""
import copy

import blockchain
import services
import target
import tools
from service import Service, sync


class ApiService(Service):
    def __init__(self, config):
        Service.__init__(self, target=self.target, name='api')
        self.config = config
        self.db = services.get('database')

    def target(self):
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
                tx['count'] = tools.count(address, {})
            except:
                tx['count'] = 1
        if 'pubkeys' not in tx:
            tx['pubkeys'] = [pubkey]
        if 'signatures' not in tx:
            tx['signatures'] = [tools.sign(tools.det_hash(tx), privkey)]
        return blockchain.add_tx(tx)

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
        return target.target()

    @sync
    def mybalance(self, address='default'):
        if address == 'default':
            address = self.db.get('address')
        return self.db.get(address)['amount'] - tools.cost_0(self.db.get('txs'), address)

    @sync
    def balance(self, address=None):
        if address is None:
            return 'what address do you want the balance for?'
        else:
            return self.mybalance()

    @sync
    def stop_(self):
        self.db.put('stop', True)
        return 'turning off all services'

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
