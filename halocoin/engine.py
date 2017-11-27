import os
import time

from halocoin import api
from halocoin import custom
from halocoin import tools
from halocoin.database import DatabaseService
from halocoin.account import AccountService
from halocoin.blockchain import BlockchainService
from halocoin.miner import MinerService
from halocoin.peer_check import PeerCheckService
from halocoin.peer_listen import PeerListenService
from halocoin.service import Service, async


def test_database(db):
    response = db.put('test', 'TEST')
    if response:
        test_response = db.get('test')
        if test_response == 'TEST':
            delete_response = db.delete('test')
            return delete_response

    return False


class Engine(Service):
    def __init__(self, config, working_dir):
        Service.__init__(self, 'engine')
        self.config = config
        self.working_dir = working_dir

        # TODO: remove
        self.config = {
            'database.type': custom.db_type,
            'api.port': custom.api_port,
            'peer.block_request_limit': 50,
            'peer.port': custom.port
        }

        if self.config['database.type'] == 'redis':
            """
            self.config.update({
                'database.name': os.path.join(self.working_dir, custom.db_name)
            })
            """
            self.db = DatabaseService(self)

        self.blockchain = BlockchainService(self)
        self.peers_check = PeerCheckService(self, custom.peers)
        self.peer_receive = PeerListenService(self)
        self.account = AccountService(self)
        self.miner = MinerService(self)

    def on_register(self):
        print('Starting halocoin')
        if not self.db.register():
            return False

        print("Firing up the Database")
        time.sleep(0.1)

        if not test_database(self.db):
            tools.log("Database service is not working.")
            return False

        b = self.db.get('init')
        if not b:
            print("Initializing records")
            self.db.put('init', True)
            self.db.put('length', -1)
            self.db.put('memoized_votes', {})
            self.db.put('txs', [])
            self.db.put('peers_ranked', [])
            self.db.put('peers', [])
            self.db.put('targets', {})
            self.db.put('times', {})
            self.db.put('mine', False)
            self.db.put('diffLength', '0')
            self.db.put('accounts', {})
            self.db.put('known_length', -1)
        self.db.put('stop', False)

        if not self.account.register():
            print("Account service has failed. Exiting!")
            self.unregister_sub_services()
            return False
        print("Started Account")

        if not self.blockchain.register():
            print("Blockchain service has failed. Exiting!")
            self.unregister_sub_services()
            return False
        print("Started Blockchain")

        if not self.peer_receive.register():
            print("Peer Receive service has failed. Exiting!")
            self.unregister_sub_services()
            return False
        print("Started Peer Receive")

        if not self.peers_check.register():
            print("Peers Check service has failed. Exiting!")
            self.unregister_sub_services()
            return False
        print("Started Peers Check")

        api.run(self)
        print("Started API")

        return True

    def unregister_sub_services(self):
        api.shutdown()
        print('Closed api')

        running_services = set()
        if self.miner.get_state() == Service.RUNNING:
            self.miner.unregister()
            running_services.add(self.miner)
        if self.peers_check.get_state() == Service.RUNNING:
            self.peers_check.unregister()
            running_services.add(self.peers_check)
        if self.peer_receive.get_state() == Service.RUNNING:
            self.peer_receive.unregister()
            running_services.add(self.peer_receive)
        if self.blockchain.get_state() == Service.RUNNING:
            self.blockchain.unregister()
            running_services.add(self.blockchain)
        if self.account.get_state() == Service.RUNNING:
            self.account.unregister()
            running_services.add(self.account)
        if self.db.get_state() == Service.RUNNING:
            self.db.unregister()
            running_services.add(self.db)

        for service in running_services:
            service.join()
            print('Closed {}'.format(service.name))

    @async
    def stop(self):
        self.unregister_sub_services()
        self.unregister()


def main(config, working_dir):
    engine_instance = Engine(config, working_dir)
    if engine_instance.register():
        print("Halocoin is fully running...")
        engine_instance.join()
        print("Shutting down gracefully")
    else:
        print("Couldn't start halocoin")
