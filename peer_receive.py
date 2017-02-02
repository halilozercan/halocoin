"""When a peer talks to us, this is how we generate a response. This is the external API.
"""
import blockchain
import custom
import tools

from network.server import Server


def security_check(dic):
    if 'version' not in dic or dic['version'] != custom.version:
        return {'bool': False, 'error': 'version'}
    else:
        # we could add security features here.
        return {'bool': True, 'newdic': dic}


def receive_peer(dic, DB):
    peer = dic['peer']
    ps = tools.db_get('peers_ranked')
    if peer[0] not in map(lambda x: x[0][0], ps):
        tools.add_peer(peer)


def block_count(dic, DB):
    length = tools.db_get('length')
    d = '0'
    if length >= 0: d = tools.db_get('diffLength')
    return {'length': length, 'diffLength': d}


def range_request(dic, DB):
    ran = dic['range']
    out = []
    counter = 0
    while (len(tools.package(out)) < custom.max_download
           and ran[0] + counter <= ran[1]):
        block = tools.db_get(ran[0] + counter, DB)
        if 'length' in block:
            out.append(block)
        counter += 1
    return out


def txs(dic, DB):
    return tools.db_get('txs')


def pushtx(dic, DB):
    DB['suggested_txs'].put(dic['tx'])
    return 'success'


def pushblock(dic, DB):
    length = tools.db_get('length')
    block = tools.db_get(length, DB)
    if 'peer' in dic:
        peer = dic['peer']
    else:
        peer = False
    if 'blocks' in dic:
        for i in range(20):
            if tools.fork_check(dic['blocks'], DB, length, block):
                blockchain.delete_block(DB)
                length -= 1
        for block in dic['blocks']:
            DB['suggested_blocks'].put([block, peer])
    else:
        DB['suggested_blocks'].put([dic['block'], peer])
    return 'success'


def peers(dic, DB):
    return tools.db_get('peers_ranked')


def main(DB, heart_queue):
    def responder(dic, DB=DB):
        funcs = {'receive_peer': receive_peer, 'block_count': block_count, 'range_request': range_request, 'txs': txs,
                 'pushtx': pushtx, 'pushblock': pushblock, 'peers': peers}
        if 'type' not in dic:
            return 'oops: ' + str(dic)
        if dic['type'] not in funcs:
            return ' '.join([dic['type'], 'is not a supported endpoint for peers'])
        check = security_check(dic)
        if not check['bool']:
            return check
        try:
            return funcs[dic['type']](check['newdic'], DB)
        except Exception as exc:
            tools.log(exc)


    try:
        peer_network = Server(responder, custom.port, heart_queue, True)
        peer_network.run()
    except Exception as exc:
        tools.log('API init error.\nAPI could not be started. This error can be caused by blocked or busy ports.')
        tools.log(exc)
