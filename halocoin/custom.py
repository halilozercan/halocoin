import os
from cdecimal import Decimal

version = "0.0013"
block_reward = 500  # Initial block reward
miner_core_count = -1  # -1 evaluates to number of cores
# Lower limits on what the "time" tag in a block can say.
median_block_time_limit = 100
# Take the median of this many of the blocks.
# How far back in history do we look when we use statistics to guess at
# the current blocktime and difficulty.
history_length = 110
# How far in history we look when we determine next block reward

# This constant is selected such that the 50 most recent blocks count for 1/2 the
# total weight.
inflection = Decimal('0.98')
# How often to generate a block in seconds
blocktime = 60
halve_at = (365 * 24 * 60 * 60 / blocktime)  # Approximately one year
recalculate_target_at = (4*60*60 // blocktime)  # It's every half day

# Precalculate
memoized_weights = [inflection ** i for i in range(history_length)]


first_target = '0' * 4 + 'f' * 60


def generate_default_config():
    config = dict()
    config['DEBUG'] = False
    config['database'] = {
        "type": "sql",
        "location": "halocoin.db"
    }

    config['logging'] = {
        'file': 'log'
    }

    config["port"] = {
        "api": int(os.environ.get('HALOCOIN_API_PORT', '7001')),
        "peers": int(os.environ.get('HALOCOIN_PEERS_PORT', '7002'))
    }

    config["peers"] = {
        "list": [
            {
                'node_id': '52e6eb49-6d59-4bf3-af96-ca3252408a4f',
                'ip': '159.89.9.43',
                'port': 7002,
                'rank': 1,
                'diffLength': '',
                'length': -1
            }
        ],
        "download_limit": 190
    }

    config["miner"] = {
        "cores": -1
    }
    return config


def read_config_file(file_address):
    import yaml
    config = yaml.load(open(file_address, 'rb'))
    if 'DEBUG' in config.keys():
        return config
    else:
        return None


def write_config_file(config, file_address):
    import yaml
    yaml.dump(config, open(file_address, 'w'))
