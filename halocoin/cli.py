#!/usr/bin/env python
import argparse
import datetime
import json
import os
import sys

import filelock
import requests
from tabulate import tabulate

import custom
import engine
import tools


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
                   headers=[tools.bcolors.HEADER + 'Type' + tools.bcolors.ENDC,
                            tools.bcolors.HEADER + 'From' + tools.bcolors.ENDC,
                            tools.bcolors.HEADER + 'To' + tools.bcolors.ENDC,
                            tools.bcolors.HEADER + 'Amount' + tools.bcolors.ENDC,
                            tools.bcolors.HEADER + 'Message' + tools.bcolors.ENDC],
                   tablefmt='orgtbl'))


def print_peers(peers):
    table = []
    for peer in peers:
        table.append([peer[0][0], peer[0][1], peer[1], peer[3]])

    print(tabulate(table,
                   headers=[tools.bcolors.HEADER + 'Address' + tools.bcolors.ENDC,
                            tools.bcolors.HEADER + 'Port' + tools.bcolors.ENDC,
                            tools.bcolors.HEADER + 'Rank' + tools.bcolors.ENDC,
                            tools.bcolors.HEADER + 'Length' + tools.bcolors.ENDC],
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
    print(tools.bcolors.WARNING + "Blocks:\n" + tools.bcolors.ENDC)
    print(tabulate(table, headers=[tools.bcolors.HEADER + 'Length' + tools.bcolors.ENDC,
                                   tools.bcolors.HEADER + 'Miner' + tools.bcolors.ENDC,
                                   tools.bcolors.HEADER + 'Time' + tools.bcolors.ENDC], tablefmt='orgtbl'))

    if len(blocks) == 1:
        print(tools.bcolors.WARNING + "\nTransactions in the Block:\n" + tools.bcolors.ENDC)
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
                tools.bcolors.HEADER + tools.tx_owner_address(tx) + tools.bcolors.ENDC,
                tools.bcolors.WARNING + tx['to'] + tools.bcolors.ENDC,
                tx['amount']))
        for tx in history['recv']:
            print("In Block {} {} => {} for amount {}".format(
                tx['block'],
                tools.bcolors.WARNING + tools.tx_owner_address(tx) + tools.bcolors.ENDC,
                tools.bcolors.HEADER + tx['to'] + tools.bcolors.ENDC,
                tx['amount']))
        for tx in history['mine']:
            print("In Block {} {} mined amount {}".format(
                tx['block'],
                tools.bcolors.HEADER + tools.tx_owner_address(tx) + tools.bcolors.ENDC,
                custom.block_reward))


def run(argv):
    actions = ['start', 'stop', 'send', 'balance', 'mybalance', 'difficulty', 'info', 'myaddress',
               'peers', 'blockcount', 'txs', 'new_wallet', 'pubkey', 'block', 'mine', 'history',
               'invalidate']
    parser = argparse.ArgumentParser(description='CLI for halocoin application.')
    parser.add_argument('action', help='Main action to take', choices=actions)
    parser.add_argument('--address', action="store", type=str, dest='address',
                        help='Give a valid blockchain address')
    parser.add_argument('--message', action="store", type=str, dest='message',
                        help='Message to send with transaction')
    parser.add_argument('--amount', action="store", type=int, dest='amount',
                        help='Amount of coins that are going to be used')
    parser.add_argument('--number', action="store", type=str, dest='number',
                        help='Block number or range')
    parser.add_argument('--wallet', action="store", type=str, dest='wallet',
                        help='Wallet file address')
    parser.add_argument('--dir', action="store", type=str, dest='dir',
                        help='Directory for halocoin to use.')

    args = parser.parse_args(argv[1:])

    if args.action in ['start', 'new_wallet'] and args.wallet is None:
        print('You should specify a wallet to run {}'.format(args.action))
        exit(1)

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

    tools.init_logging(working_dir)

    if args.action == 'start':
        lock = filelock.FileLock(os.path.join(working_dir, 'engine_lock'))
        try:
            with lock.acquire(timeout=2):
                wallet_file = open(args.wallet, 'r')
                wallet_encrypted_content = wallet_file.read()
                from getpass import getpass

                while True:
                    try:
                        wallet_pw = getpass('Wallet password: ')
                        wallet = json.loads(tools.decrypt(wallet_pw, wallet_encrypted_content))
                        break
                    except ValueError:
                        print('Wrong password')

                # TODO: Real configuration
                engine.main(wallet, None, working_dir)
        except filelock.Timeout:
            print('Halocoin is already running')
        except:
            print('Halocoin ran into a problem while starting!')
    elif args.action == 'new_wallet':
        from getpass import getpass

        wallet_pw = 'w'
        wallet_pw_2 = 'w2'
        while wallet_pw != wallet_pw_2:
            wallet_pw = getpass('New wallet password: ')
            wallet_pw_2 = getpass('New wallet password(again): ')

        wallet = tools.random_wallet()
        wallet_content = json.dumps(wallet)
        wallet_encrypted_content = tools.encrypt(wallet_pw, wallet_content)
        with open(args.wallet, 'w') as f:
            f.write(wallet_encrypted_content)
        print('New wallet is created: {}'.format(args.wallet))
    else:
        if args.action == 'block':
            blocks = make_api_request(args.action, number=args.number)
            print_blocks(blocks)
        elif args.action == 'blockcount':
            result = make_api_request(args.action)
            print 'We have {} blocks.'.format(result['length'])
            if result['length'] != result['known_length']:
                print 'Peers are reporting {} blocks.'.format(result['known_length'])
        elif args.action == 'balance':
            print(make_api_request(args.action, address=args.address))
        elif args.action == 'invalidate':
            print(make_api_request(args.action, address=args.address))
        elif args.action == 'send':
            print(make_api_request(args.action, address=args.address, amount=args.amount, message=args.message))
        elif args.action == 'peers':
            peers = make_api_request(args.action)
            print_peers(peers)
        elif args.action == 'history':
            history = make_api_request(args.action, address=args.address)
            print_history(history)
        else:
            print(make_api_request(args.action))


def main():
    if sys.stdin.isatty():
        run(sys.argv)
    else:
        argv = sys.stdin.read().split(' ')
        run(argv)


if __name__ == '__main__':
    run(sys.argv)
