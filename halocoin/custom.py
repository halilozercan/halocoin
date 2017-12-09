import os
from cdecimal import Decimal

"""
Most of these stuff should be moved into config file.
- Initial peer list must be in some kind of torrent file.
- Inflection, block reward, etc. are not configurable. 
They must stay here.
- 

# Configurable
DEBUG = False
db_type = 'redis'
db_user = 'username'
db_pass = 'halocoin'
db_port = 6379
db_name = 0
log_file = 'log'
port = 7900
api_port = 7899
download_many = 50  # Max number of blocks to request from a peer at the same time.


# Independent
peers = [['159.89.9.43', 7900]]
"""

version = "0.0003"
block_reward = 10 ** 2
miner_core_count = -1  # -1 evaluates to number of cores
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


def generate_default_config():
    config = dict()
    config['DEBUG'] = False
    config['database'] = {
        "type": "redis",
        "index": 0,
        "auth": False,
        "user": "",
        "pw": "",
        "port": 6379
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
                'node_id': 'e2f9c001-4c5c-447a-96ef-b5271146e046',
                'ip': '159.89.9.43',
                'port': 7002,
                'rank': 1,
                'diffLength': '',
                'length': -1
            }
        ],
        "download_limit": 50
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
