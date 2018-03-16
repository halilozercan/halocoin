#!/usr/bin/env python
import argparse
import os
import sys
from functools import wraps
from inspect import Parameter

from halocoin import custom

# TODO
""" 
@app.route('/tx/application', methods=['POST'])
@app.route('/power/available', methods=['GET'])
"""


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


def make_api_request(method, http_method="GET", **kwargs):
    from requests import get, post
    if not method.startswith("/"):
        raise ValueError('Method endpoints should start with backslash')
    url = "http://" + str(host) + ":" + str(connection_port) + method

    kwargs = {k: v for k, v in kwargs.items() if v is not None}

    if http_method == "GET":
        response = get(url, params=kwargs)
    else:
        response = post(url, data=kwargs)
    if response.status_code != 200:
        return {
            'error': response.status_code,
            'message': response.text
        }
    else:
        return response.json()


def haloprint(text):
    import json
    content = json.dumps(text, indent=4, sort_keys=True)
    from pygments import highlight
    from pygments.formatters import TerminalFormatter
    from pygments.lexers import JsonLexer
    print(highlight(content, JsonLexer(), TerminalFormatter()))


def extract_configuration(dir):
    from halocoin import tools
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

    if os.path.exists(os.path.join(working_dir, 'config')):
        config = os.path.join(working_dir, 'config')
        config = custom.read_config_file(config)
    else:
        config = custom.generate_default_config()
        custom.write_config_file(config, os.path.join(working_dir, 'config'))

    if config is None:
        raise ValueError('Couldn\'t parse config file {}'.format(config))

    return config, working_dir


@action
def start(dir=None):
    from halocoin import engine, tools
    config, working_dir = extract_configuration(dir)
    tools.init_logging(config['DEBUG'], working_dir, config['logging']['file'])
    engine.main(config, working_dir)


@action
def new_wallet(wallet, pw=None, set_default=None):
    from getpass import getpass

    if pw is None:
        wallet_pw = 'w'
        wallet_pw_2 = 'w2'
        while wallet_pw != wallet_pw_2:
            wallet_pw = getpass('New wallet password: ')
            wallet_pw_2 = getpass('New wallet password(again): ')
    else:
        wallet_pw = pw

    haloprint(make_api_request("/wallet/new", http_method="POST",
                               wallet_name=wallet, password=wallet_pw,
                               set_default=set_default))


@action
def upload_wallet(file, wallet):
    haloprint(make_api_request("/wallet/upload", http_method="POST",
                               wallet_name=wallet,
                               wallet_file=open(file, 'rb').read()))


@action
def download_wallet(wallet):
    # TODO: actual file download
    haloprint(make_api_request("/wallet/download", wallet_name=wallet, http_method="GET"))


@action
def auth_list():
    haloprint(make_api_request("/subauths", http_method="GET"))


@action
def wallets():
    haloprint(make_api_request("/wallet/list", http_method="GET"))


@action
def info_wallet(wallet=None, pw=None):
    from getpass import getpass
    if wallet is not None and pw is None:
        wallet_pw = getpass('Wallet password: ')
    else:
        wallet_pw = pw

    information = make_api_request("/wallet/info", http_method="GET",
                                   wallet_name=wallet,
                                   password=wallet_pw)
    haloprint(information)


@action
def remove_wallet(wallet, pw=None):
    from getpass import getpass
    if pw is None:
        wallet_pw = getpass('Wallet password: ')
    else:
        wallet_pw = pw

    information = make_api_request("/wallet/remove", http_method="GET",
                                   wallet_name=wallet,
                                   password=wallet_pw)
    haloprint(information)


@action
def default_wallet(wallet, pw=None):
    from getpass import getpass
    if pw is None:
        wallet_pw = getpass('Wallet password: ')
    else:
        wallet_pw = pw

    information = make_api_request("/wallet/default", http_method="GET",
                                   wallet_name=wallet,
                                   password=wallet_pw)
    haloprint(information)


@action
def info_address(address=None):
    information = make_api_request("/address/" + address, http_method="GET")
    haloprint(information)


@action
def blocks(start, end=None):
    _blocks = make_api_request("/blocks", http_method="GET", start=start, end=end)
    haloprint(_blocks)


@action
def blockcount():
    result = make_api_request("/blockcount", http_method="GET")
    haloprint(result)


@action
def node_id():
    haloprint(make_api_request("node_id", http_method="GET"))


@action
def send(address, amount, wallet, pw=None, message=None):
    from getpass import getpass
    if pw is None:
        wallet_pw = getpass('Wallet password: ')
    else:
        wallet_pw = pw

    haloprint(make_api_request("/tx/send", http_method="POST", address=address,
                               amount=amount, message=message,
                               wallet_name=wallet, password=wallet_pw))


@action
def pool_reg(wallet, pw=None, force=None):
    from getpass import getpass
    if pw is None:
        wallet_pw = getpass('Wallet password: ')
    else:
        wallet_pw = pw

    haloprint(make_api_request("/tx/pool_reg", http_method="POST",
                               wallet_name=wallet, password=wallet_pw, force=force))


@action
def application(wallet, mode=None, list=None, pw=None):
    from getpass import getpass
    if pw is None:
        wallet_pw = getpass('Wallet password: ')
    else:
        wallet_pw = pw

    if list is None:
        list = ''

    if mode is None:
        mode = 's'

    haloprint(make_api_request("/tx/application", http_method="POST",
                               wallet_name=wallet, password=wallet_pw, list=list, mode=mode))


@action
def reward(certificate, privkey, job_id, address):
    certificate = open(certificate, 'rb').read()
    privkey = open(privkey, 'rb').read()
    haloprint(make_api_request("/tx/reward", http_method="POST", address=address, job_id=job_id,
                               certificate=certificate, privkey=privkey))


@action
def job_dump(certificate, privkey, job_id, amount, download_url, upload_url, hashsum, image):
    import time
    certificate = open(certificate, 'rb').read()
    privkey = open(privkey, 'rb').read()
    haloprint(make_api_request("/tx/job_dump", http_method="POST", id=job_id, timestamp=time.time(), amount=amount,
                               certificate=certificate, privkey=privkey, download_url=download_url,
                               upload_url=upload_url, hashsum=hashsum, image=image))


@action
def auth_reg(certificate, privkey, host, amount, description):
    certificate = open(certificate, 'rb').read()
    privkey = open(privkey, 'rb').read()
    haloprint(make_api_request("/tx/auth_reg", http_method="POST", certificate=certificate, privkey=privkey, host=host,
                               supply=amount, description=description))


@action
def jobs():
    haloprint(make_api_request("/job/list", http_method="GET"))

@action
def peers():
    peers = make_api_request("/peers", http_method="GET")
    haloprint(peers)


@action
def stop():
    haloprint(make_api_request("/stop", http_method="POST"))


@action
def start_miner(wallet=None, pw=None):
    from getpass import getpass
    if wallet is not None and pw is None:
        wallet_pw = getpass('Wallet password: ')
    else:
        wallet_pw = pw

    haloprint(make_api_request("/miner/start", http_method="POST", wallet_name=wallet, password=wallet_pw))


@action
def stop_miner():
    haloprint(make_api_request("/miner/stop", http_method="POST"))


@action
def status_miner():
    haloprint(make_api_request("/miner", http_method="GET"))


@action
def start_power(wallet=None, pw=None):
    from getpass import getpass
    if wallet is not None and pw is None:
        wallet_pw = getpass('Wallet password: ')
    else:
        wallet_pw = pw

    haloprint(make_api_request("/power/start", http_method="POST", wallet_name=wallet, password=wallet_pw))


@action
def stop_power():
    haloprint(make_api_request("/miner/power", http_method="POST"))


@action
def status_power():
    haloprint(make_api_request("/power", http_method="GET"))


@action
def difficulty():
    result = make_api_request("/difficulty", http_method="GET")
    if isinstance(result, bytearray):
        print(result.hex())
    else:
        print(result)


@action
def mempool():
    txs = make_api_request("/mempool", http_method="GET")
    haloprint(txs)


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
    parser.add_argument('--certificate', action="store", type=str, dest='certificate',
                        help='Rewarding sub-auth certificate file in pem format')
    parser.add_argument('--download-url', action="store", type=str, dest='download_url',
                        help='Job dump download address')
    parser.add_argument('--upload-url', action="store", type=str, dest='upload_url',
                        help='Job dump upload address')
    parser.add_argument('--image', action="store", type=str, dest='image',
                        help='Job dump docker image tag')
    parser.add_argument('--hashsum', action="store", type=str, dest='hashsum',
                        help='Job dump file hashsum')
    parser.add_argument('--description', action="store", type=str, dest='description',
                        help='Required at sub-auth registration')
    parser.add_argument('--job-id', action="store", type=str, dest='job_id',
                        help='While dumping, requesting, or rewarding, necessary job id.')
    parser.add_argument('--privkey', action="store", type=str, dest='privkey',
                        help='Rewarding sub-auth private key file in pem format')
    parser.add_argument('--pw', action="store", type=str, dest='pw',
                        help='NOT RECOMMENDED! If you want to pass wallet password as argument.')
    parser.add_argument('--dir', action="store", type=str, dest='dir',
                        help='Directory for halocoin to use.')
    parser.add_argument('--port', action="store", type=int, dest='port',
                        help='Override API port defined in config file.')
    parser.add_argument('--host', action="store", type=str, dest='host',
                        help='Define a host address while registering an auth.')
    parser.add_argument('--list', action="store", type=str, dest='list',
                        help='Sub authority application list')
    parser.add_argument('--mode', choices=sorted(['c', 's']), dest='mode',
                        help="Main action to perform by this CLI.")
    parser.add_argument('--force', action="store_true", dest='force',
                        help='Force something that makes trouble.')
    parser.add_argument('--default', action="store_true", dest='set_default',
                        help='Make new wallet default')
    args = parser.parse_args(argv[1:])

    config, working_dir = extract_configuration(args.dir)
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
