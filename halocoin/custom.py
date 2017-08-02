"""This is to make magic numbers easier to deal with."""
import multiprocessing
import os
from decimal import Decimal

DEBUG = False
peers = [['188.166.65.249', 7900], ['46.101.107.152', 7900]]
database_name = 'db_4'
log_file = 'log'
port = 7900
api_port = 7899
version = "0.0001"
max_key_length = 6 ** 4
block_reward = 10 ** 5
fee = 10 ** 3
# Lower limits on what the "time" tag in a block can say.
mmm = 100
# Take the median of this many of the blocks.
# How far back in history do we look when we use statistics to guess at
# the current blocktime and difficulty.
history_length = 400
# Any address information can be found by scanning whole blockchain. However,
# this solution does not scale. By caching available information at every $cache_length
# number of blocks, address information can be quickly found.
cache_length = 100
# This constant is selected such that the 50 most recent blocks count for 1/2 the
# total weight.
inflection = Decimal('0.985')
download_many = 50  # Max number of blocks to request from a peer at the same time.
max_download = 58000
blocktime = 120