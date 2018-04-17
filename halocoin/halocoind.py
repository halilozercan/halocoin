import argparse

import os

import sys

from halocoin import custom, tools


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


def start(config, working_dir, daemon=False):
    from halocoin.daemon import Daemon
    from halocoin import engine, tools
    tools.init_logging(config['DEBUG'], working_dir, config['logging']['file'])
    if daemon:
        myDaemon = Daemon(pidfile='/tmp/halocoin', run_func=lambda: engine.main(config, working_dir))
        myDaemon.start()
    else:
        engine.main(config, working_dir)


def run(argv):
    parser = argparse.ArgumentParser(description='Halocoin engine.')
    parser.add_argument('--version', action='version', version='%(prog)s ' + custom.version)
    parser.add_argument('--api-host', action="store", type=str, dest='api_host',
                        help='Hosting address of API')
    parser.add_argument('--api-port', action="store", type=int, dest='api_port',
                        help='Hosting port of API')
    parser.add_argument('--p2p-host', action="store", type=str, dest='p2p_host',
                        help='Hosting address of API')
    parser.add_argument('--p2p-port', action="store", type=int, dest='p2p_port',
                        help='Hosting port of API')
    parser.add_argument('--data-dir', action="store", type=str, dest='dir',
                        help='Data directory. Defaults to ' + tools.get_default_dir())
    parser.add_argument('--daemon', action="store_true", dest='daemon',
                        help='Start in daemon mode.')
    args = parser.parse_args(argv[1:])

    config, working_dir = extract_configuration(args.dir)
    if args.api_host is not None and args.api_host != "":
        config['host']['api'] = args.api_host
    if args.api_port is not None and args.api_port != "":
        config['port']['api'] = args.api_port
    if args.p2p_host is not None and args.p2p_host != "":
        config['host']['peers'] = args.p2p_host
    if args.p2p_port is not None and args.p2p_port != "":
        config['port']['peers'] = args.p2p_port

    start(config, working_dir, args.daemon)
    return


def main():
    if sys.stdin.isatty():
        run(sys.argv)
    else:
        argv = sys.stdin.read().split(' ')
        run(argv)


if __name__ == '__main__':
    run(sys.argv)