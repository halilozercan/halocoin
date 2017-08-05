#!/usr/bin/env python
import argparse
import json
import os
import random
import string
from pprint import pprint

import filelock
import sys

import signal

import custom
import engine

import ntwrk
import tools


def run_command(p):
    response = ntwrk.command(('localhost', custom.api_port), p)
    return response


def run(argv):
    actions = ['start', 'stop', 'spend', 'balance', 'mybalance', 'difficulty', 'info', 'myaddress',
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
    parser.add_argument('--number', action="store", type=int, dest='number',
                        help='Block number')
    parser.add_argument('--wallet', action="store", type=str, dest='wallet',
                        help='Wallet file address')
    parser.add_argument('--no-database', action="store_true", dest='no_database',
                        help='Do not use database information, look at blockchain')
    parser.add_argument('--dir', action="store", type=str, dest='dir',
                        help='Directory for halocoin to use.')

    args = parser.parse_args(argv[1:])

    if args.action in ['balance', 'send'] and args.address is None:
        print('You should specify an address when running {}'.format(args.action))
        exit(1)
    elif args.action in ['start', 'new_wallet'] and args.wallet is None:
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
        elif args.action == 'balance':
            cmd['address'] = args.address
            print(run_command(cmd))
        elif args.action == 'invalidate':
            cmd['address'] = args.address
            print(run_command(cmd))
        elif args.action == 'spend':
            cmd['address'] = args.address
            cmd['amount'] = args.amount
            if args.message is not None:
                cmd['message'] = args.message
            print(run_command(cmd))
        elif args.action == 'history':
            cmd['address'] = args.address
            history = run_command(cmd)
            if isinstance(history, str):
                print history
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
        else:
            print(run_command(cmd))


def main():
    if sys.stdin.isatty():
        run(sys.argv)
    else:
        argv = sys.stdin.read().split(' ')
        run(argv)


if __name__ == '__main__':
    run(sys.argv)
