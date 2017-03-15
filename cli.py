#!/usr/bin/env python
import argparse

import custom
import network
import threads
import tools


def get_address(tx):
    pubkey = str(raw_input('What is your address or pubkey\n>'))
    if len(pubkey) > 40:
        out = tools.make_address([pubkey], 1)
    else:
        out = pubkey
    return tx


def main(c):
    if c[0] == 'start':
        r = run_command({'command': 'blockcount'})
        if r is None:
            p = raw_input('Brain wallet?\n')
            tools.daemonize(lambda: threads.main(p))
        else:
            print("blockchain is already running")
    elif c[0] == 'new_address':
        if len(c) < 2:
            print("what is your brain wallet? not enough inputs.")
        else:
            privkey = tools.det_hash(c[1])
            pubkey = tools.privtopub(privkey)
            address = tools.make_address([pubkey], 1)
            return ({'brain': str(c[1]),
                     'privkey': str(privkey),
                     'pubkey': str(pubkey),
                     'address': str(address)})
    else:
        return run_command({'command': c})


def run_command(p):
    tools.log("Running API command: " + str(p['command']))
    response = network.send_receive(message=p, host='localhost', port=custom.api_port)
    if response is None:
        print("Node is probably off. Use --start argument to start.")
    return response


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='CLI for mc-chain application.')
    parser.add_argument('--start', help='Start a full node', action="store_true")
    parser.add_argument('--stop', help='Stop all the threads and shut down the node', action="store_true")
    parser.add_argument('--spend', action="store", type=str, metavar="<addr>",
                        help='Spends money, in satoshis, to an address <addr>. Example: spend 1000 '
                             '11j9csj9802hc982c2h09ds')
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

    args = vars(parser.parse_args())
    given_args = {}
    for arg in args.keys():
        if args[arg] is not None and args[arg] is not False:
            given_args[arg] = args[arg]
    if len(given_args) == 0:
        parser.print_help()
    elif len(given_args) > 1:
        print("Too many arguments given. Only one argument should be specified per run")
    else:
        command = [given_args.keys()[0], given_args[given_args.keys()[0]]]
        print(main(command))
