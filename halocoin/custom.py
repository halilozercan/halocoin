"""This is to make magic numbers easier to deal with."""
import multiprocessing
import os
from cdecimal import Decimal

DEBUG = False
peers = [['188.166.65.249', 7900], ['46.101.107.152', 7900]]
database_name = 'db_4'
log_file = 'log'
port = 7900
api_port = 7899
version = "0.0002"
block_reward = 10 ** 5
fee = 10 ** 3
miner_core_count = 8  # -1 evaluates to number of cores
# Lower limits on what the "time" tag in a block can say.
mmm = 100
# Take the median of this many of the blocks.
# How far back in history do we look when we use statistics to guess at
# the current blocktime and difficulty.
history_length = 400
# This constant is selected such that the 50 most recent blocks count for 1/2 the
# total weight.
inflection = Decimal('0.985')
download_many = 50  # Max number of blocks to request from a peer at the same time.
blocktime = 120