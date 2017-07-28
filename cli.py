#!/usr/bin/env python
import argparse
import json
import os
import random
import string

import filelock
import sys

import custom
import engine

import ntwrk
import tools


def run_command(p):
    response = ntwrk.command(('localhost', custom.api_port), p)
    return response


if __name__ == '__main__':
    actions = ['start', 'stop', 'send', 'balance', 'mybalance', 'difficulty', 'info', 'myaddress',
               'peers', 'blockcount', 'txs', 'new_wallet', 'pubkey', 'block', 'mine']
    parser = argparse.ArgumentParser(description='CLI for halocoin application.')
    parser.add_argument('action', help='Main action to take', choices=actions)
    parser.add_argument('--address', action="store", type=str, dest='address',
                        help='Give a valid blockchain address')
    parser.add_argument('--amount', action="store", type=int, dest='amount',
                        help='Amount of coins that are going to be used')
    parser.add_argument('--number', action="store", type=int, dest='number',
                        help='Block number')
    parser.add_argument('--wallet', action="store", type=str, dest='wallet',
                        help='Wallet file address')
    """
    parser.add_argument('--start', help='Start a full node', action="store_true")
    parser.add_argument('--stop', help='Stop all the threads and shut down the node', action="store_true")
    parser.add_argument('--blockcount', help='returns the number of blocks since the genesis block',
                        action="store_true")
    parser.add_argument('--txs', action="store_true",
                        help='A list of the zeroth confirmation transactions that are expected to be included '
                             'in the next block')
    parser.add_argument('--balance', action="store", type=str, metavar="<addr>",
                        help='Balance of the given address. Example: balance 11j9csj9802hc982c2h09ds')
    parser.add_argument('--mybalance', action="store_true",
                        help='The amount of satoshis that you own')
    parser.add_argument('--difficulty', action="store_true", help='Current difficulty')
    parser.add_argument('--info', action="store_true",
                        help='The contents of an entry in the hashtable. If you want to know what the first '
                             'block was: info 0, if you want to know about a particular address <addr>: info '
                             '<addr>, if you want to know about yourself: info my_address')
    parser.add_argument('--myaddress', action="store_true", help='Tells you your own address')
    parser.add_argument('--peers', action="store_true", help='Your list of peers')
    """

    args = parser.parse_args()

    if args.action in ['balance', 'send'] and args.address is None:
        print('You should specify an address when running {}'.format(args.action))
        exit(1)
    elif args.action in ['start', 'new_wallet'] and args.wallet is None:
        print('You should specify a wallet to run {}'.format(args.action))
        exit(1)

    if args.action == 'start':
        lock = filelock.FileLock('engine_lock')
        try:
            with lock.acquire(timeout=2):
                wallet_file = open(args.wallet, 'r')
                wallet_encrypted_content = wallet_file.read()
                from getpass import getpass

                wallet_pw = getpass('Wallet password: ')
                wallet = json.loads(tools.decrypt(wallet_pw, wallet_encrypted_content))

                # TODO: Real configuration
                #tools.daemonize(lambda: engine.main(wallet, None))
                engine.main(wallet, None)
        except:
            print('Halocoin is already running')
    elif args.action == 'new_wallet':
        from getpass import getpass

        wallet_pw = 'w'
        wallet_pw_2 = 'w2'
        while wallet_pw != wallet_pw_2:
            wallet_pw = getpass('New wallet password: ')
            wallet_pw_2 = getpass('New wallet password(again): ')

        init = ''.join(random.choice(string.lowercase) for i in range(64))
        privkey = tools.det_hash(init)
        pubkey = tools.privtopub(privkey)
        address = tools.make_address([pubkey], 1)
        wallet = {
            'privkey': str(privkey),
            'pubkey': str(pubkey),
            'address': str(address)
        }
        wallet_content = json.dumps(wallet)
        wallet_encrypted_content = tools.encrypt(wallet_pw, wallet_content)
        with open(args.wallet, 'w') as f:
            f.write(wallet_encrypted_content)
        print('New wallet is created: {}'.format(args.wallet))
    else:
        cmd = {'action': args.action}
        if args.action == 'block':
            cmd['number'] = args.number
        print(run_command(cmd))
