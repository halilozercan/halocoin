import random
import sys
import json

import time

import multiprocessing

import tools


def target(candidate_block, queue):
    if 'nonce' in candidate_block:
        candidate_block.pop('nonce')
    halfHash = tools.det_hash(candidate_block)
    candidate_block['nonce'] = random.randint(0, 10000000000000000000000000000000000000000)
    current_hash = tools.det_hash({'nonce': candidate_block['nonce'], 'halfHash': halfHash})
    while current_hash > candidate_block['target']:
        candidate_block['nonce'] += 1
        current_hash = tools.det_hash({'nonce': candidate_block['nonce'], 'halfHash': halfHash})
    queue.put(candidate_block)


def run(args):
    candidate_block = json.load(open(args[1], 'r'))

    from multiprocessing import Process
    pool = []
    for i in range(8):
        queue = multiprocessing.Queue()
        p = Process(target=target, args=[candidate_block, queue])
        p.start()
        pool.append((p, queue))

    is_alive = True
    while is_alive:
        for p in pool:
            if not p[0].is_alive():
                finished = p
                is_alive = False
                break
        time.sleep(0.1)

    for p in pool:
        try:
            p[0].kill()
        except:
            pass
    candidate_block = finished[1].get()

    f = open(args[1]+'_mined', 'w')
    f.write(json.dumps(candidate_block))
    f.flush()
    f.close()
    print candidate_block


def main():
    run(sys.argv)