import os
import random
import sys
import json

import time

import multiprocessing
import Queue

import signal

import tools

running = True


def target(candidate_block, queue):
    def handler(a, b):
        global target_running
        target_running = False

    target_running = True
    signal.signal(signal.SIGTERM, handler)
    if 'nonce' in candidate_block:
        candidate_block.pop('nonce')
    halfHash = tools.det_hash(candidate_block)
    candidate_block['nonce'] = random.randint(0, 10000000000000000000000000000000000000000)
    current_hash = tools.det_hash({'nonce': candidate_block['nonce'], 'halfHash': halfHash})
    while current_hash > candidate_block['target'] and target_running:
        candidate_block['nonce'] += 1
        current_hash = tools.det_hash({'nonce': candidate_block['nonce'], 'halfHash': halfHash})
    if current_hash > candidate_block['target']:
        queue.put(candidate_block)


def run(args):
    def is_everyone_dead(pool):
        for p in pool:
            if p.is_alive():
                return False
        return True

    candidate_block = json.load(open(args[1], 'r'))

    print os.getpid()

    from multiprocessing import Process
    pool = []
    queue = multiprocessing.Queue()
    for i in range(8):
        p = Process(target=target, args=[candidate_block, queue])
        p.start()
        pool.append(p)

    while not is_everyone_dead(pool) and running:
        try:
            candidate_block = queue.get(timeout=0.5)
            break
        except Queue.Empty:
            pass

    queue.close()

    for p in pool:
        if p.is_alive():
            p.terminate()
            p.join()

    f = open(args[1]+'_mined', 'w')
    f.write(json.dumps(candidate_block))
    f.flush()
    f.close()


def handler(sig, a):
    global running
    running = False


def main():

    if len(sys.argv) < 2:
        sys.stderr.write('Not enough arguments!\n')
        exit(1)
    signal.signal(signal.SIGTERM, handler)
    run(sys.argv)
    exit(0)

main()
