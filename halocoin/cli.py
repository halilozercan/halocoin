#!/usr/bin/env python
import argparse
import datetime
import json
import os
import sys

import filelock
import requests
from tabulate import tabulate

from halocoin import custom
from halocoin import engine
from halocoin import tools


class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


actions = dict()


def action(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    global actions
    actions[func.__name__] = wrapper
    return wrapper


def make_api_request(method, **kwargs):
    url = "http://localhost:" + str(custom.api_port) + "/jsonrpc"
    headers = {'content-type': 'application/json'}

    # Example echo method
    payload = {
        "method": method,
        "params": kwargs,
        "jsonrpc": "2.0",
        "id": 0,
    }
    response = requests.post(url, data=json.dumps(payload), headers=headers).json()
    return response['result']


def print_txs(txs):
    table = []
    for tx in txs:
        tx['from'] = tools.tx_owner_address(tx)
        if tx['type'] == 'mint':
            tx['to'] = 'N/A'
            tx['amount'] = custom.block_reward
            tx['message'] = ''
        table.append([tx['type'], tx['from'], tx['to'], tx['amount'], tx['message']])

    print(tabulate(table,
                   headers=[Colors.HEADER + 'Type' + Colors.ENDC,
                            Colors.HEADER + 'From' + Colors.ENDC,
                            Colors.HEADER + 'To' + Colors.ENDC,
                            Colors.HEADER + 'Amount' + Colors.ENDC,
                            Colors.HEADER + 'Message' + Colors.ENDC],
                   tablefmt='orgtbl'))


def print_peers(peers):
    table = []
    for peer in peers:
        table.append([peer[0][0], peer[0][1], peer[1], peer[3]])

    print(tabulate(table,
                   headers=[Colors.HEADER + 'Address' + Colors.ENDC,
                            Colors.HEADER + 'Port' + Colors.ENDC,
                            Colors.HEADER + 'Rank' + Colors.ENDC,
                            Colors.HEADER + 'Length' + Colors.ENDC],
                   tablefmt='orgtbl'))


def print_blocks(blocks):
    table = []
    for block in blocks:
        if block['length'] == 0:
            block['prevHash'] = "N/A"
        block['time'] = datetime.datetime.fromtimestamp(
            int(block['time'])
        ).strftime('%Y-%m-%d %H:%M:%S')
        mint_tx = filter(lambda t: t['type'] == 'mint', block['txs'])[0]
        table.append([block['length'], tools.tx_owner_address(mint_tx), block['time']])
    print(Colors.WARNING + "Blocks:\n" + Colors.ENDC)
    print(tabulate(table, headers=[Colors.HEADER + 'Length' + Colors.ENDC,
                                   Colors.HEADER + 'Miner' + Colors.ENDC,
                                   Colors.HEADER + 'Time' + Colors.ENDC], tablefmt='orgtbl'))

    if len(blocks) == 1:
        print(Colors.WARNING + "\nTransactions in the Block:\n" + Colors.ENDC)
        print_txs(blocks[0]['txs'])


def print_history(history):
    if history is None:
        print("Could not receive history")
    elif isinstance(history, str):
        print(history)
    else:
        for tx in history['send']:
            print("In Block {} {} => {} for amount {}".format(
                tx['block'],
                Colors.HEADER + tools.tx_owner_address(tx) + Colors.ENDC,
                Colors.WARNING + tx['to'] + Colors.ENDC,
                tx['amount']))
        for tx in history['recv']:
            print("In Block {} {} => {} for amount {}".format(
                tx['block'],
                Colors.WARNING + tools.tx_owner_address(tx) + Colors.ENDC,
                Colors.HEADER + tx['to'] + Colors.ENDC,
                tx['amount']))
        for tx in history['mine']:
            print("In Block {} {} mined amount {}".format(
                tx['block'],
                Colors.HEADER + tools.tx_owner_address(tx) + Colors.ENDC,
                custom.block_reward))


@action
def start(args):
    if args.dir is None:
        working_dir = tools.get_default_dir()
    else:
        working_dir = args.dir

    if os.path.exists(working_dir) and not os.path.isdir(working_dir):
        print("Given path {} is not a directory.".format(working_dir))
        exit(1)
    elif not os.path.exists(working_dir):
        print("Given path {} does not exist. Attempting to create...".format(working_dir))
        try:
            os.makedirs(working_dir)
            print("Successful")
        except OSError:
            print("Could not create a directory!")
            exit(1)

    lock = filelock.FileLock(os.path.join(working_dir, 'engine_lock'))
    try:
        with lock.acquire(timeout=2):
            tools.init_logging(working_dir)
            engine.main(None, working_dir)
    except filelock.Timeout:
        print('Halocoin is already running')
    except Exception as e:
        print('Halocoin ran into a problem while starting!')
        tools.log(e)


@action
def new_wallet(args):
    from getpass import getpass

    wallet_pw = 'w'
    wallet_pw_2 = 'w2'
    while wallet_pw != wallet_pw_2:
        wallet_pw = getpass('New wallet password: ')
        wallet_pw_2 = getpass('New wallet password(again): ')

    wallet = tools.random_wallet()
    wallet_content = json.dumps(wallet)
    wallet_encrypted_content = tools.encrypt(wallet_pw, wallet_content)
    with open(args.path, 'w') as f:
        f.write(wallet_encrypted_content)
    print('New wallet is created at {}'.format(args.wallet))


@action
def info_wallet(args):
    wallet_file = open(args.path, 'r')
    wallet = tools.parse_wallet(wallet_file)

    print("Address: {}".format(wallet['address']))
    print("Pubkey: {}".format(wallet['pubkey']))
    print("Privkey: {}".format(wallet['privkey']))


@action
def block(args):
    blocks = make_api_request(args.action, number=args.number)
    print_blocks(blocks)


@action
def blockcount(args):
    result = make_api_request(args.action)
    print('We have {} blocks.'.format(result['length']))
    if result['length'] != result['known_length']:
        print('Peers are reporting {} blocks.'.format(result['known_length']))


@action
def balance(args):
    print(make_api_request(args.action, address=args.address))


@action
def send(args):
    wallet_file = open(args.path, 'r')
    wallet = tools.parse_wallet(wallet_file)
    print(make_api_request(args.action, address=args.address,
                           amount=args.amount, message=args.message,
                           wallet=wallet))

@action
def peers(args):
    peers = make_api_request(args.action)
    print_peers(peers)


@action
def history(args):
    history = make_api_request(args.action, address=args.address)
    print_history(history)


@action
def stop(args):
    print(make_api_request(args.action))


@action
def start_miner(args):
    if args.path is None:
        sys.stderr.write("Please provide a wallet which will be rewarded for mining\n")
        return
    wallet_file = open(args.path, 'rb')
    wallet = tools.parse_wallet(wallet_file)
    print(make_api_request(args.action, wallet=wallet))


@action
def stop_miner(args):
    print(make_api_request(args.action))


@action
def status_miner(args):
    print(make_api_request(args.action))


@action
def difficulty(args):
    print(make_api_request(args.action))


@action
def info(args):
    print(make_api_request(args.action))


@action
def txs(args):
    txs = make_api_request(args.action)
    print("Transactions in pool:")
    print_txs(txs)


def run(argv):
    parser = argparse.ArgumentParser(description='CLI for halocoin.')
    parser.add_argument('action', choices=actions.keys())
    parser.add_argument('--address', action="store", type=str, dest='address',
                        help='Give a valid blockchain address')
    parser.add_argument('--message', action="store", type=str, dest='message',
                        help='Message to send with transaction')
    parser.add_argument('--amount', action="store", type=int, dest='amount',
                        help='Amount of coins that are going to be used')
    parser.add_argument('--number', action="store", type=str, dest='number',
                        help='Block number or range')
    parser.add_argument('--path', action="store", type=str, dest='path',
                        help='Path for a file, e.g. wallet')
    parser.add_argument('--dir', action="store", type=str, dest='dir',
                        help='Directory for halocoin to use.')

    args = parser.parse_args(argv[1:])

    actions[args.action](args)
    return


def main():
    if sys.stdin.isatty():
        run(sys.argv)
    else:
        argv = sys.stdin.read().split(' ')
        run(argv)


if __name__ == '__main__':
    run(sys.argv)
