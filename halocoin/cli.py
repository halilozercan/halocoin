#!/usr/bin/env python
import json
import os
import sys
import time
from functools import wraps
from getpass import getpass
from inspect import Parameter, signature

from halocoin import custom, tools

actions = dict()

"""
0.0.19.c CLI changes

- Every CLI command must start with an action. 
- Actions are tied to a function
- Function parameters are command line arguments
- Optional arguments are defined with None as default value
- Help is completely auto generated according to this scheme.
- Help first level only lists actions
- Action help command returns help for that action only
"""


def print_help(action=None):
    print("Halocoin Commandline Interface")
    print("Version: " + custom.version)
    if action is None:
        print("List of actions:\n")
        sorted_actions = sorted(actions, key=lambda x:x)
        for action in sorted_actions:
            print("\t" + action)
    else:
        print("Parameters:")
        sig = signature(actions[action])
        for parameter in sig.parameters.keys():
            sys.stdout.write("\t--" + sig.parameters[parameter].name + "\t")
            if sig.parameters[parameter].default == Parameter.empty:
                print("Required")
            else:
                print("Optional")



def parseParams(params, **kwargs):
    def getArgumentName(arg):
        while arg[0] == '-':
            arg = arg[1:]
        arg = arg.replace("-", "_")
        return arg

    result = {
        "action": None,
        "map": dict()
    }

    for key, value in kwargs.items():
        result['map'][key] = value

    if len(params) == 0:
        sys.stderr.write("You must define at least one action\n\n")
        print_help()
        exit(1)

    result['action'] = params[0]

    current_arg = None
    for param in params[1:]:
        if current_arg is None and param[0] != '-':
            sys.stderr.write("Could'nt parse command line arguments\n\n")
            exit(1)
        elif current_arg is None:
            current_arg = getArgumentName(param)
            result['map'][current_arg] = None
        elif param[0] != '-':
            result["map"][current_arg] = param
        elif param[0] == '-':
            current_arg = getArgumentName(param)
            result['map'][current_arg] = None
    return result


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
    config = json.load(open(tools.get_engine_info_file()))
    url = "http://" + str(config['api']['host']) + ":" + str(config['api']['port']) + method

    kwargs = {k: v for k, v in kwargs.items() if v is not None}

    try:
        if http_method == "GET":
            response = get(url, params=kwargs, headers={"Authorization": "Bearer " + jwtToken()})
        else:
            response = post(url, data=kwargs, headers={"Authorization": "Bearer " + jwtToken()})

        if response.status_code != 200:
            return {
                'error': response.status_code,
                'message': response.text
            }
        else:
            return response.json()
    except Exception as e:
        sys.stderr.write("Could not connect to API. Maybe halocoind is not running?\n")
        exit(1)


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


def jwtToken():
    jwtTokenPath = os.path.join(tools.get_default_dir_cli(), 'jwt')
    if os.path.exists(jwtTokenPath):
        jwtToken = open(jwtTokenPath, 'r').read()
        return jwtToken
    else:
        return ""


@action
def start(data_dir=None, daemon=False):
    from filelock import FileLock, Timeout
    from halocoin.daemon import Daemon
    from halocoin import engine, tools

    lock = FileLock(tools.get_locked_file(), timeout=1)
    try:
        with lock:
            config, working_dir = extract_configuration(data_dir)
            json.dump(config, open(tools.get_engine_info_file(), "w"))
            tools.init_logging(config['DEBUG'], working_dir, config['logging']['file'])
            if daemon:
                myDaemon = Daemon(pidfile='/tmp/halocoin', run_func=lambda: engine.main(config, working_dir))
                myDaemon.start()
            else:
                engine.main(config, working_dir)
    except Timeout:
        sys.stderr.write("It seems like another halocoin instance is already running.\n")
        sys.stderr.write("If you are sure there is a mistake, remove the file at: \n")
        sys.stderr.write(tools.get_locked_file())



@action
def login(wallet, pw=None):
    if pw is None:
        wallet_pw = getpass('Password: ')
    else:
        wallet_pw = pw

    result = make_api_request("/login", http_method="POST", wallet_name=wallet, password=wallet_pw)
    if result['success']:
        print("Successfully logged in with {}".format(wallet))
        os.makedirs(tools.get_default_dir_cli(), exist_ok=True)
        with open(os.path.join(tools.get_default_dir_cli(), 'jwt'), 'w') as f:
            f.write(result['jwt'])
    else:
        print("Could not login with {}".format(wallet))


@action
def new_wallet(wallet, pw=None):
    if pw is None:
        wallet_pw = 'w'
        wallet_pw_2 = 'w2'
        while wallet_pw != wallet_pw_2:
            wallet_pw = getpass('New wallet password: ')
            wallet_pw_2 = getpass('New wallet password(again): ')
    else:
        wallet_pw = pw

    haloprint(make_api_request("/wallet/new", http_method="POST",
                               wallet_name=wallet, password=wallet_pw))


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
def login_info():
    if jwtToken() == '':
        haloprint({"error": "You are not logged in!"})

    information = make_api_request("/login/info", http_method="GET")
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
def send(address, amount, message=None):
    if jwtToken() == '':
        haloprint({"error": "You are not logged in!"})

    haloprint(make_api_request("/tx/send", http_method="POST", address=address,
                               amount=amount, message=message))


@action
def pool_reg(force=None):
    if jwtToken() == '':
        haloprint({"error": "You are not logged in!"})

    haloprint(make_api_request("/tx/pool_reg", http_method="POST",
                               force=force))


@action
def application(mode=None, list=None):
    if jwtToken() == '':
        haloprint({"error": "You are not logged in!"})

    if list is None:
        list = ''

    if mode is None:
        mode = 's'

    haloprint(make_api_request("/tx/application", http_method="POST",
                               list=list, mode=mode))


@action
def reward(certificate, privkey, job_id, address):
    certificate = open(certificate, 'rb').read()
    privkey = open(privkey, 'rb').read()
    haloprint(make_api_request("/tx/reward", http_method="POST", address=address, job_id=job_id,
                               certificate=certificate, privkey=privkey))


@action
def job_dump(certificate, privkey, job_id, amount, download_url, upload_url, hashsum, image):
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
    if wallet is not None and pw is None:
        wallet_pw = getpass('Wallet password: ')
    else:
        wallet_pw = pw

    haloprint(make_api_request("service/miner/start", http_method="POST", wallet_name=wallet, password=wallet_pw))


@action
def stop_miner():
    haloprint(make_api_request("service/miner/stop", http_method="POST"))


@action
def status_miner():
    haloprint(make_api_request("service/miner/status", http_method="GET"))


@action
def start_power(wallet=None, pw=None):
    if wallet is not None and pw is None:
        wallet_pw = getpass('Wallet password: ')
    else:
        wallet_pw = pw

    haloprint(make_api_request("service/power/start", http_method="POST", wallet_name=wallet, password=wallet_pw))


@action
def stop_power():
    haloprint(make_api_request("service/power/stop", http_method="POST"))


@action
def status_power():
    haloprint(make_api_request("service/power/status", http_method="GET"))


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
    params = parseParams(argv[1:], dir=None)

    from inspect import signature
    sig = signature(actions[params['action']])
    kwargs = {}
    for parameter in sig.parameters.keys():
        if sig.parameters[parameter].default == Parameter.empty and \
                (parameter not in params['map']):
            sys.stderr.write("\"{}\" requires parameter {}\n".format(params['action'], parameter))
            sys.exit(1)
        elif parameter in params['map']:
            kwargs[parameter] = params['map'][parameter]
    if "help" in kwargs:
        print_help(params['action'])
        exit(0)
    actions[params['action']](**kwargs)
    return


def main():
    if sys.stdin.isatty():
        run(sys.argv)
    else:
        argv = sys.stdin.read().split(' ')
        run(argv)


if __name__ == '__main__':
    run(sys.argv)
