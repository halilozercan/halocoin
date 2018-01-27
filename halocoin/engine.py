import signal
import sys
import time

import psutil

from halocoin import api
from halocoin import tools
from halocoin.blockchain import BlockchainService
from halocoin.client_db import ClientDB
from halocoin.database import KeyValueStore
from halocoin.miner import MinerService
from halocoin.peer_check import PeerCheckService
from halocoin.peer_listen import PeerListenService
from halocoin.service import Service, async, threaded
from halocoin.state import StateDatabase


def test_database(db):
    results = [False, False]
    response = db.put('test', 'TEST')
    if response:
        test_response = db.get('test')
        if test_response == 'TEST':
            results[0] = True

    db.simulate()
    response = db.put('test', 'TEST_SIM')
    if response:
        test_response = db.get('test')
        if test_response == 'TEST_SIM':
            db.rollback()
            if db.get('test') == 'TEST':
                results[1] = True

    return results[0] and results[1]


instance = None


class Engine(Service):
    def __init__(self, config, working_dir):
        Service.__init__(self, 'engine')
        self.config = config
        self.working_dir = working_dir

        self.db = KeyValueStore(self, self.config['database']['location'])
        self.blockchain = BlockchainService(self)
        self.peers_check = PeerCheckService(self, self.config['peers']['list'])
        self.peer_receive = PeerListenService(self)
        self.clientdb = ClientDB(self)
        self.statedb = StateDatabase(self)
        self.miner = MinerService(self)

    def on_register(self):
        print('Starting halocoin')

        if not test_database(self.db):
            tools.log("Database service is not working.")
            return False

        b = self.db.get('init')
        if not b:
            print("Initializing records")
            self.db.put('init', True)
            self.db.put('length', -1)
            self.db.put('peer_list', [])
            self.db.put('targets', {})
            self.db.put('times', {})
            self.db.put('diffLength', '0')
            self.db.put('accounts', {})
            self.db.put('job_list', [])
            self.clientdb.put('known_length', -1)

        if not self.blockchain.register():
            sys.stderr.write("Blockchain service has failed. Exiting!\n")
            self.unregister_sub_services()
            return False

        if not self.peer_receive.register():
            sys.stderr.write("Peer Receive service has failed. Exiting!\n")
            self.unregister_sub_services()
            return False

        if not self.peers_check.register():
            sys.stderr.write("Peers Check service has failed. Exiting!\n")
            self.unregister_sub_services()
            return False

        api.run()

        return True

    def unregister_sub_services(self):
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

        for service in running_services:
            service.join()
            print('Closed {}'.format(service.name))

    @threaded
    def stats(self):
        value = psutil.cpu_percent()
        if int(psutil.cpu_percent()) > 0:
            api.cpu_usage(str(value))
        time.sleep(0.1)

    @async
    def stop(self):
        self.unregister_sub_services()
        self.unregister()


def signal_handler(signal, frame):
    sys.stderr.write('Detected interrupt, initiating shutdown\n')
    if instance is not None:
        instance.stop()


def main(config, working_dir):
    global instance
    instance = Engine(config, working_dir)
    if instance.register():
        print("Halocoin is fully running...")
        signal.signal(signal.SIGINT, signal_handler)
        instance.join()
        print("Shutting down gracefully")
    else:
        print("Couldn't start halocoin")
