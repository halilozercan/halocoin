#!/usr/bin/env python
import argparse
import datetime
import os
import sys

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
connection_port = 7899
host = os.environ.get('HALOCOIN_API_HOST', 'localhost')


def action(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    global actions
    actions[func.__name__] = wrapper
    return wrapper


def make_api_request(method, files=None, **kwargs):
    from requests_toolbelt import MultipartEncoder
    if files is None:
        files = {}
    url = "http://" + str(host) + ":" + str(connection_port) + "/" + method

    if len(files) > 0:
        fields = {}
        fields.update(kwargs)
        fields.update(files)
        m = MultipartEncoder(fields=fields)
        response = requests.post(url, data=m, headers={'Content-Type': m.content_type}).json()
    else:
        response = requests.post(url, data=kwargs).json()
    return response


def print_txs(txs, length=-1):
    table = []
    for tx in txs:
        tx['from'] = tools.tx_owner_address(tx)
        if tx['type'] == 'mint':
            tx['to'] = 'N/A'
            tx['amount'] = tools.block_reward(length)
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
        table.append([peer['node_id'], peer['ip'], peer['port'], "{:10.3f}".format(peer['rank']), peer['length']])

    print(tabulate(table,
                   headers=[Colors.HEADER + 'Node ID' + Colors.ENDC,
                            Colors.HEADER + 'Address' + Colors.ENDC,
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
        mint_tx = list(filter(lambda t: t['type'] == 'mint', block['txs']))[0]
        table.append([block['length'], tools.tx_owner_address(mint_tx), block['time']])
    print(Colors.WARNING + "Blocks:\n" + Colors.ENDC)
    print(tabulate(table, headers=[Colors.HEADER + 'Length' + Colors.ENDC,
                                   Colors.HEADER + 'Miner' + Colors.ENDC,
                                   Colors.HEADER + 'Time' + Colors.ENDC], tablefmt='orgtbl'))

    if len(blocks) == 1:
        print(Colors.WARNING + "\nTransactions in the Block:\n" + Colors.ENDC)
        print_txs(blocks[0]['txs'], length=blocks[0]['length'])


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
                tools.block_reward(tx['block'])))


def extract_configuration(args):
    if args.dir is None:
        working_dir = tools.get_default_dir()
    else:
        working_dir = args.dir

    working_dir = os.path.join(working_dir, str(custom.version))

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

    if args.config is not None:
        config = custom.read_config_file(args.config)
    elif os.path.exists(os.path.join(working_dir, 'config')):
        args.config = os.path.join(working_dir, 'config')
        config = custom.read_config_file(args.config)
    else:
        config = custom.generate_default_config()
        custom.write_config_file(config, os.path.join(working_dir, 'config'))

    if config is None:
        raise ValueError('Couldn\'t parse config file {}'.format(args.config))

    return config, working_dir


@action
def start(args):
    config, working_dir = extract_configuration(args)
    tools.init_logging(config['DEBUG'], working_dir, config['logging']['file'])
    engine.main(config, working_dir)


@action
def new_wallet(args):
    from getpass import getpass

    if args.pw is None:
        wallet_pw = 'w'
        wallet_pw_2 = 'w2'
        while wallet_pw != wallet_pw_2:
            wallet_pw = getpass('New wallet password: ')
            wallet_pw_2 = getpass('New wallet password(again): ')
    else:
        wallet_pw = args.pw

    print(make_api_request(args.action, wallet_name=args.wallet, password=wallet_pw))


@action
def info_wallet(args):
    from getpass import getpass
    if args.pw is None:
        wallet_pw = getpass('Wallet password: ')
    else:
        wallet_pw = args.pw

    information = make_api_request(args.action, wallet_name=args.wallet_name, password=wallet_pw)

    if isinstance(information, dict):
        print("Address: {}".format(information['address']))
        print("Balance: {}".format(information['balance']))
        print("Pubkey: {}".format(information['pubkey']))
        print("Privkey: {}".format(information['privkey']))
    else:
        print(information)


@action
def upload_wallet(args):
    files = {
        "wallet_file": ('wallet_file', open(args.wallet_path, 'rb')),
        "wallet_name": args.wallet_name
    }
    print(make_api_request(args.action, files=files))


@action
def download_wallet(args):
    print(make_api_request(args.action, wallet_name=args.wallet))


@action
def block(args):
    blocks = make_api_request(args.action, start=args.start, end=args.end)
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
def node_id(args):
    print(make_api_request(args.action))


@action
def send(args):
    from getpass import getpass
    if args.pw is None:
        wallet_pw = getpass('Wallet password: ')
    else:
        wallet_pw = args.pw

    print(make_api_request(args.action, address=args.address,
                           amount=args.amount, message=args.message,
                           wallet_name=args.wallet_name, password=wallet_pw))


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
    if args.wallet_name is None:
        sys.stderr.write("Please provide a wallet which will be rewarded for mining\n")
        return
    from getpass import getpass
    if args.pw is None:
        wallet_pw = getpass('Wallet password: ')
    else:
        wallet_pw = args.pw
    print(make_api_request(args.action, wallet_name=args.wallet_name, password=wallet_pw))


@action
def stop_miner(args):
    print(make_api_request(args.action))


@action
def status_miner(args):
    print(make_api_request(args.action))


@action
def difficulty(args):
    result = make_api_request(args.action)
    if isinstance(result, bytearray):
        print(result.hex())
    else:
        print(result)


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
    parser.add_argument('--start', action="store", type=str, dest='start',
                        help='Starting number while requesting range of blocks')
    parser.add_argument('--end', action="store", type=str, dest='end',
                        help='Ending number while requesting range of blocks')
    parser.add_argument('--wallet-path', action="store", type=str, dest='wallet_path',
                        help='Wallet path for uploading')
    parser.add_argument('--wallet', action="store", type=str, dest='wallet_name',
                        help='Wallet name')
    parser.add_argument('--config', action="store", type=str, dest='config',
                        help='Config file address. Use with start command.')
    parser.add_argument('--pw', action="store", type=str, dest='pw',
                        help='NOT RECOMMENDED! If you want to pass wallet password as argument.')
    parser.add_argument('--dir', action="store", type=str, dest='dir',
                        help='Directory for halocoin to use.')

    args = parser.parse_args(argv[1:])

    config, working_dir = extract_configuration(args)
    global connection_port
    connection_port = config['port']['api']

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
