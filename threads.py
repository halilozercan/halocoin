"""This program starts all the threads going. When it hears a kill signal, it kills all the threads.
"""
import multiprocessing
import sys
import time

import api
import blockchain
import custom
import services
from database import DatabaseService
from api import ApiService
import miner
import network
import peer_receive
import peers_check
import tools
from network import server


def peer_recieve_func(d, DB=custom.DB):
    return peer_receive.main(d, DB)


def test_database():
    response = get_db().put('test', 'TEST')
    if response:
        test_response = get_db().get('test')
        if test_response == 'TEST':
            delete_response = get_db().delete('test')
            return delete_response

    return False


def get_db():
    return services.get('database')


def main(wallet_location, configuration_file):
    print('Starting full node')
    #wallet = tools.read_wallet(wallet_location)
    #config = tools.read_config(configuration_file)
    config = {
        'database_name': custom.database_name
    }

    services.register(DatabaseService(config))

    if not test_database():
        tools.log("Database service is not working.")

    b = services.get('database').get('init')
    if not b:
        get_db().put('init', True)
        get_db().put('length', -1)
        get_db().put('memoized_votes', {})
        get_db().put('txs', [])
        get_db().put('peers_ranked', [])
        get_db().put('targets', {})
        get_db().put('times', {})
        get_db().put('mine', False)
        get_db().put('diffLength', '0')
    get_db().put('stop', False)

    print get_db().get('length')

    get_db().put('privkey', wallet.privkey)
    get_db().put('address', tools.make_address([wallet.pubkey], 1))

    services.register(ApiService(config))
    services.register(PeersCheckService(config))
    services.register(PeerReceiveService(config))
    services.register(BlockchainService(config))

    while not get_db().get('stop'):
        time.sleep(1)

    services.unregister()  # Stop all services
    sys.exit(0)


if __name__ == '__main__':  # for windows
    try:
        main(sys.argv[1])
    except Exception as exc:
        tools.log(exc)
