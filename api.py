"""This is the internal API. These are the words that are used to interact with a local node that you have the password to.
"""
import copy
import sys

import blockchain
import custom
import target
import tools
from network import Response
from network.server import Server


def easy_add_transaction(tx_orig, DB, privkey='default'):
    tx = copy.deepcopy(tx_orig)
    if privkey in ['default', 'Default']:
        if tools.db_existence('privkey'):
            privkey = tools.db_get('privkey')
        else:
            return ('no private key is known, so the tx cannot be signed. Here is the tx: \n' + str(
                tools.package(tx_orig).encode('base64').replace('\n', '')))
    pubkey = tools.privtopub(privkey)
    address = tools.make_address([pubkey], 1)
    if 'count' not in tx:
        try:
            tx['count'] = tools.count(address, {})
        except:
            tx['count'] = 1
    if 'pubkeys' not in tx:
        tx['pubkeys'] = [pubkey]
    if 'signatures' not in tx:
        tx['signatures'] = [tools.sign(tools.det_hash(tx), privkey)]
    return blockchain.add_tx(tx, DB)


def peers(DB, args):
    return tools.db_get('peers_ranked')


def DB_print(DB, args):
    return DB


def info(DB, args):
    if len(args) < 1:
        return 'not enough inputs'
    if args[0] == 'myaddress':
        address = tools.db_get('address')
    else:
        address = args[0]
    return tools.db_get(address, DB)


def myaddress(DB, args):
    return tools.db_get('address')


def spend(DB, args):
    if len(args) < 2:
        return 'not enough inputs'
    return easy_add_transaction({'type': 'spend', 'amount': int(args[0]), 'to': args[1]}, DB)


def accumulate_words(l, out=''):
    if len(l) > 0:
        return accumulate_words(l[1:], out + ' ' + l[0])
    else:
        return out


def pushtx(DB, args):
    tx = tools.unpackage(args[0].decode('base64'))
    if len(args) == 1:
        return easy_add_transaction(tx, DB)
    privkey = tools.det_hash(args[1])
    return easy_add_transaction(tx, DB, privkey)


def blockcount(DB, args):
    return tools.db_get('length')


def txs(DB, args):
    return tools.db_get('txs')


def difficulty(DB, args):
    return target.target(DB)


def mybalance(DB, args, address='default'):
    if address == 'default':
        address = tools.db_get('address')
    return \
        tools.db_get(address, DB)['amount'] - tools.cost_0(tools.db_get('txs'), address)


def balance(DB, args):
    if len(args) < 1:
        return 'what address do you want the balance for?'
    else:
        return mybalance(DB, args, args[0])


def log(DB, args):
    tools.log(accumulate_words(args)[1:])


def stop_(DB, args):
    tools.db_put('stop', True)
    return 'turning off all threads'


def mine(DB, args):
    m = not (tools.db_get('mine'))
    tools.db_put('mine', m)
    if m:
        m = 'on'
    else:
        m = 'off'
    return 'miner is currently: ' + m


def pass_(DB, args): return ' '


def error_(DB, args):
    # return error
    # Previously an error object was returned. No idea what it was about
    return "error"


def main(DB, heart_queue):
    def responder(dic):
        command = dic['command']
        args = command[1:]
        try:
            possibles = globals().copy()
            possibles.update(locals())
            method = possibles.get(command[0])
            return method(DB, args)
        except Exception as exc:
            tools.log(exc)
            out = 'Failure : ' + str(sys.exc_info())
            return None

    try:
        api_network = Server(handler=responder, port=custom.api_port, heart_queue=heart_queue)
        api_network.run()
    except Exception as exc:
        tools.log('API init error.\nAPI could not be started. This error can be caused by blocked or busy ports.')
        tools.log(exc)
