#!/usr/bin/env python
import argparse
import os
import sys
from functools import wraps
from inspect import Parameter
from pprint import pprint

import requests

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
    @wraps(func)
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

    kwargs = {k: v for k, v in kwargs.items() if v is not None}

    if len(files) > 0:
        fields = {}
        fields.update(kwargs)
        fields.update(files)
        m = MultipartEncoder(fields=fields)
        response = requests.post(url, data=m, headers={'Content-Type': m.content_type})
    else:
        response = requests.post(url, data=kwargs)
    if response.status_code != 200:
        return {
            'error': response.status_code,
            'message': response.text
        }
    else:
        return response.json()


def extract_configuration(dir, config):
    if dir is None:
        working_dir = tools.get_default_dir()
    else:
        working_dir = dir

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

    if config is not None:
        config = custom.read_config_file(config)
    elif os.path.exists(os.path.join(working_dir, 'config')):
        config = os.path.join(working_dir, 'config')
        config = custom.read_config_file(config)
    else:
        config = custom.generate_default_config()
        custom.write_config_file(config, os.path.join(working_dir, 'config'))

    if config is None:
        raise ValueError('Couldn\'t parse config file {}'.format(config))

    return config, working_dir


@action
def start(dir=None, config=None):
    config, working_dir = extract_configuration(dir, config)
    tools.init_logging(config['DEBUG'], working_dir, config['logging']['file'])
    engine.main(config, working_dir)


@action
def new_wallet(wallet, pw):
    from getpass import getpass

    if pw is None:
        wallet_pw = 'w'
        wallet_pw_2 = 'w2'
        while wallet_pw != wallet_pw_2:
            wallet_pw = getpass('New wallet password: ')
            wallet_pw_2 = getpass('New wallet password(again): ')
    else:
        wallet_pw = pw

    print(make_api_request("new_wallet", wallet_name=wallet, password=wallet_pw))


@action
def info_wallet(wallet=None, pw=None):
    from getpass import getpass
    if pw is None:
        wallet_pw = getpass('Wallet password: ')
    else:
        wallet_pw = pw

    information = make_api_request("info_wallet", wallet_name=wallet, password=wallet_pw)

    if isinstance(information, dict):
        print("Address: {}".format(information['address']))
        print("Balance: {}".format(information['balance']))
        print("Pubkey: {}".format(information['pubkey']))
        print("Privkey: {}".format(information['privkey']))
    else:
        pprint(information)


@action
def upload_wallet(file, wallet):
    files = {
        "wallet_file": ('wallet_file', open(file, 'rb')),
        "wallet_name": wallet
    }
    print(make_api_request("upload_wallet", files=files))


@action
def download_wallet(wallet):
    print(make_api_request("download_wallet", wallet_name=wallet))


@action
def blocks(start, end=None):
    _blocks = make_api_request("blocks", start=start, end=end)
    pprint(_blocks)


@action
def blockcount():
    result = make_api_request("blockcount")
    print('We have {} blocks.'.format(result['length']))
    if result['length'] != result['known_length']:
        print('Peers are reporting {} blocks.'.format(result['known_length']))


@action
def balance(address=None):
    print(make_api_request("balance", address=address))


@action
def node_id():
    print(make_api_request("node_id"))


@action
def send(address, amount, pw, wallet=None, message=None):
    from getpass import getpass
    if pw is None:
        wallet_pw = getpass('Wallet password: ')
    else:
        wallet_pw = pw

    print(make_api_request(action, address=address,
                           amount=amount, message=message,
                           wallet_name=wallet, password=wallet_pw))


@action
def peers():
    peers = make_api_request("peers")
    pprint(peers)


@action
def history(address):
    history = make_api_request("history", address=address)
    pprint(history)


@action
def stop():
    print(make_api_request("stop"))


@action
def start_miner(pw, wallet=None):
    print(make_api_request("start_miner", wallet_name=wallet, password=pw))


@action
def stop_miner():
    print(make_api_request("stop_miner"))


@action
def status_miner():
    print(make_api_request("status_miner"))


@action
def difficulty():
    result = make_api_request("difficulty")
    if isinstance(result, bytearray):
        print(result.hex())
    else:
        print(result)


@action
def mempool():
    txs = make_api_request("mempool")
    pprint(txs)


def run(argv):
    parser = argparse.ArgumentParser(description='CLI for halocoin.')
    parser.add_argument('action', choices=sorted(actions.keys()),
                        help="Main action to perform by this CLI.")
    parser.add_argument('--version', action='version', version='%(prog)s ' + custom.version)
    parser.add_argument('--address', action="store", type=str, dest='address',
                        help='Give a valid blockchain address')
    parser.add_argument('--message', action="store", type=str, dest='message',
                        help='Message to send with transaction')
    parser.add_argument('--amount', action="store", type=int, dest='amount',
                        help='Amount of coins that are going to be used')
    parser.add_argument('--start', metavar='<integer>', action="store", type=str, dest='start',
                        help='Starting number while requesting range of blocks')
    parser.add_argument('--end', metavar='<integer>', action="store", type=str, dest='end',
                        help='Ending number while requesting range of blocks')
    parser.add_argument('--file', metavar='/file/path', action="store", type=str, dest='file',
                        help='File path for wallet upload')
    parser.add_argument('--wallet', metavar='my_wallet', action="store", type=str, dest='wallet',
                        help='Wallet name')
    parser.add_argument('--config', action="store", type=str, dest='config',
                        help='Config file address. Use with start command.')
    parser.add_argument('--pw', action="store", type=str, dest='pw',
                        help='NOT RECOMMENDED! If you want to pass wallet password as argument.')
    parser.add_argument('--dir', action="store", type=str, dest='dir',
                        help='Directory for halocoin to use.')
    parser.add_argument('--port', action="store", type=int, dest='port',
                        help='Override API port defined in config file.')
    parser.add_argument('--force', action="store_true", dest='force',
                        help='Force something that makes trouble.')

    args = parser.parse_args(argv[1:])

    config, working_dir = extract_configuration(args.dir, args.config)
    global connection_port
    connection_port = config['port']['api']

    from inspect import signature
    sig = signature(actions[args.action])
    kwargs = {}
    for parameter in sig.parameters.keys():
        if sig.parameters[parameter].default == Parameter.empty and \
                (not hasattr(args, parameter) or getattr(args, parameter) is None):
            sys.stderr.write("\"{}\" requires parameter {}\n".format(args.action, parameter))
            sys.exit(1)
        kwargs[parameter] = getattr(args, parameter)
    actions[args.action](**kwargs)
    return


def main():
    if sys.stdin.isatty():
        run(sys.argv)
    else:
        argv = sys.stdin.read().split(' ')
        run(argv)


if __name__ == '__main__':
    run(sys.argv)
