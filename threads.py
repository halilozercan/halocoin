"""This program starts all the threads going. When it hears a kill signal, it kills all the threads.
"""
import multiprocessing
import sys
import time

import api
import blockchain
import custom
import database
import miner
import network
import peer_receive
import peers_check
import tools
from network import server


# windows was complaining about lambda
def peer_recieve_func(d, DB=custom.DB):
    return peer_receive.main(d, DB)


def test_database():
    response = tools.db_put('test', 'TEST')
    if response:
        test_response = tools.db_get('test')
        if test_response == 'TEST':
            delete_response = tools.db_delete('test')
            return delete_response

    return False


def main(brainwallet, pubkey_flag=False):
    DB = custom.DB
    tools.log('custom.current_loc: ' + str(custom.current_loc))
    print('starting full node')

    cmds = [database.DatabaseProcess(
        DB['heart_queue'],
        custom.database_name,
        tools.log,
        custom.database_port)]

    try:
        cmds[0].start()
    except Exception as exc:
        tools.log(exc)

    tools.log('starting ' + cmds[0].name)
    if not test_database():
        tools.log("Database is not working as intended.")
        return

    b = tools.db_existence('init')
    if not b:
        tools.db_put('init', True)
        tools.db_put('length', -1)
        tools.db_put('memoized_votes', {})
        tools.db_put('txs', [])
        tools.db_put('peers_ranked', [])
        tools.db_put('targets', {})
        tools.db_put('times', {})
        tools.db_put('mine', False)
        tools.db_put('diffLength', '0')
    tools.db_put('stop', False)
    tools.log('stop: ' + str(tools.db_get('stop')))

    if not pubkey_flag:
        privkey = tools.det_hash(brainwallet)
        pubkey = tools.privtopub(privkey)
        tools.db_put('privkey', privkey)
    else:
        pubkey = brainwallet
        tools.db_put('privkey', 'Default')

    tools.db_put('address', tools.make_address([pubkey], 1))

    processes = [
        {'target': tools.heart_monitor,
         'args': (DB['heart_queue'],),
         'name': 'heart_monitor'},
        {'target': blockchain.main,
         'args': (DB,),
         'name': 'blockchain'},
        {'target': api.main,
         'args': (DB, DB['heart_queue']),
         'name': 'api'},
        {'target': peers_check.main,
         'args': (custom.peers, DB),
         'name': 'peers_check'},
        {'target': miner.main,
         'args': (pubkey, DB),
         'name': 'miner'},
        {'target': peer_receive.main,
         'args': (DB, DB['heart_queue']),
         'name': 'peer_receive'}
    ]

    for process in processes[1:]:
        cmd = multiprocessing.Process(**process)
        cmd.start()
        cmds.append(cmd)
        tools.log('starting ' + cmd.name)

    while not tools.db_get('stop'):
        time.sleep(1)

    tools.log('about to stop threads')
    DB['heart_queue'].put('stop')

    network.send_receive('stop', port=custom.port, host='localhost')
    network.send_receive('stop', port=custom.api_port, host='localhost')

    # this operation sends database process to the end of the list
    cmds.reverse()

    for cmd in cmds[:-1]:
        cmd.join()
        tools.log('stopped a process: ' + str(cmd))

    network.send_receive('stop', port=custom.database_port, host='localhost')

    cmds[-1].join()
    tools.log('stopped a process: ' + str(cmds[-1]))
    tools.log('all processes stopped')
    sys.exit(0)


if __name__ == '__main__':  # for windows
    try:
        main(sys.argv[1])
    except Exception as exc:
        tools.log(exc)
