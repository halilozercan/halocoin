from cdecimal import Decimal

"""
Most of these stuff should be moved into config file.
- Initial peer list must be in some kind of torrent file.
- Inflection, block reward, etc. are not configurable. 
They must stay here.
- 
"""

# Configurable
DEBUG = False
db_type = 'redis'
# db_user = 'username'
db_pass = 'halocoin'
db_port = 6379
db_name = 0
log_file = 'log'
port = 7900
api_port = 7899
download_many = 50  # Max number of blocks to request from a peer at the same time.


# Integrity of blockchain
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
memoized_weights = [inflection ** i for i in range(1000)]
blocktime = 120


# Independent
peers = [['188.166.65.249', 7900], ['46.101.107.152', 7900]]

