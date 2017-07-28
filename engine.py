"""This program starts all the threads going. When it hears a kill signal, it kills all the threads.
"""
import custom
import tools
from api import ApiService
from blockchain import BlockchainService
from database import PDatabaseService
from peer_receive import PeerReceiveService
from peers_check import PeersCheckService
from service import Service, async


def test_database(db):
    response = db.put('test', 'TEST')
    if response:
        test_response = db.get('test')
        if test_response == 'TEST':
            delete_response = db.delete('test')
            return delete_response

    return False


class Engine(Service):
    def __init__(self, wallet, config):
        Service.__init__(self, 'engine')
        self.wallet = wallet
        self.config = config

        # TODO: remove
        self.config = {
            'database.name': custom.database_name,
            'api.port': custom.api_port,
            'peer.block_request_limit': 50,
            'peer.port': custom.port
        }

        self.db = PDatabaseService(self)
        self.blockchain = BlockchainService(self)
        self.api = ApiService(self)
        self.peers_check = PeersCheckService(self, custom.peers)
        self.peer_receive = PeerReceiveService(self)

    def on_register(self):
        print('Starting full node')
        self.db.register()

        if not test_database(self.db):
            tools.log("Database service is not working.")

        b = self.db.get('init')
        if not b:
            self.db.put('init', True)
            self.db.put('length', -1)
            self.db.put('memoized_votes', {})
            self.db.put('txs', [])
            self.db.put('peers_ranked', [])
            self.db.put('targets', {})
            self.db.put('times', {})
            self.db.put('mine', False)
            self.db.put('diffLength', '0')
        self.db.put('stop', False)

        self.db.put('privkey', self.wallet['privkey'])
        self.db.put('address', tools.make_address([self.wallet['pubkey']], 1))

        self.blockchain.register()
        self.api.register()
        #self.peers_check.register()
        #self.peer_receive.register()

    @async
    def stop(self):
        print 'Closing services'
        self.api.unregister()
        print 'Closed api'
        #self.peers_check.unregister()
        print 'Closed peers check'
        #self.peer_receive.unregister()
        print 'Closed peer receive'
        #self.blockchain.unregister()
        print 'Closed blockchain'
        self.db.unregister()
        print 'Closed db and everything'
        self.unregister()


def main(wallet, config):
    new_service = Engine(wallet, config)
    new_service.register()
