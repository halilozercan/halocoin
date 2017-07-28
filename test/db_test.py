import random

import miner
import tools

candidate_block = miner.genesis("043f742d02bda3f03fd5154ce201d6b488484ea6b5c306d6b7ac0ef58414d72d080a3dd7f4821b479f5e7af76ea7762c468b40d2dc7db05b8e34cbc68694db1e69")

halfHash = tools.det_hash(candidate_block)
candidate_block['nonce'] = random.randint(0, 10000000000000000000000000000000000000000)
count = 0
while tools.det_hash({'nonce': candidate_block['nonce'],
                      'halfHash': halfHash}) > candidate_block['target']:
    count += 1
    candidate_block['nonce'] += 1
print candidate_block