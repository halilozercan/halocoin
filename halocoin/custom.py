import os
from cdecimal import Decimal

version = "0.0004"
block_reward = 10 ** 3  # Initial block reward
halve_at = 525600  # Approximately one year
recalculate_target_at = 1440  # It's everyday bro!
miner_core_count = -1  # -1 evaluates to number of cores
# Lower limits on what the "time" tag in a block can say.
median_block_time_limit = 100
# Take the median of this many of the blocks.
# How far back in history do we look when we use statistics to guess at
# the current blocktime and difficulty.
history_length = 1440
# This constant is selected such that the 50 most recent blocks count for 1/2 the
# total weight.
inflection = Decimal('0.985')
# Precalculate
memoized_weights = [inflection ** i for i in range(recalculate_target_at)]
# How often to generate a block in seconds
blocktime = 60


# Coinami root certificate.
# Everyone will accept any certificate that is
root_cert_pem = b"""-----BEGIN CERTIFICATE-----
MIIGVjCCBD6gAwIBAgIJAJl3ePtD2nV6MA0GCSqGSIb3DQEBCwUAMIG3MQswCQYD
VQQGEwJUUjEPMA0GA1UECAwGVHVya2V5MQ8wDQYDVQQHDAZBbmthcmExGzAZBgNV
BAoMEkJpbGtlbnQgVW5pdmVyc2l0eTErMCkGA1UECwwiRGVwYXJ0bWVudCBvZiBD
b21wdXRlciBFbmdpbmVlcmluZzETMBEGA1UEAwwKQmlsa2VudCBDUzEnMCUGCSqG
SIb3DQEJARYYY2Fsa2FuQGNzLmJpbGtlbnQuZWR1LnRyMB4XDTE3MTIxMTE0NDIx
MVoXDTM3MTIwNjE0NDIxMVowgbcxCzAJBgNVBAYTAlRSMQ8wDQYDVQQIDAZUdXJr
ZXkxDzANBgNVBAcMBkFua2FyYTEbMBkGA1UECgwSQmlsa2VudCBVbml2ZXJzaXR5
MSswKQYDVQQLDCJEZXBhcnRtZW50IG9mIENvbXB1dGVyIEVuZ2luZWVyaW5nMRMw
EQYDVQQDDApCaWxrZW50IENTMScwJQYJKoZIhvcNAQkBFhhjYWxrYW5AY3MuYmls
a2VudC5lZHUudHIwggIiMA0GCSqGSIb3DQEBAQUAA4ICDwAwggIKAoICAQCj3TA8
38NJiv9pKTwmUHUSyD8K3Sxu5GBiqanXbP1ARl0mQlET/Amj4nsKTsnJXaEodJ+u
hlQUsXUTWTF5A5NXc4ME1CVJ7A4UoqSVNR8LPEbZWVZfc0OodFUG8EjygH6gtxFT
hCAIeva18uXBNqitY33clpkC6BlGWQaqIISgT59wrTn5j7mxDx+LtuSDxKNqpitm
aa9+kwJt3uUNw0iHasyL2k0dKtF2FB8SZgTPdB61rpWCSGz4cSf4lSbJwomMNQFM
Efu/J2vhrVbOxuRmgEqSTQ2dMmWQU1XsHw9+JdBlus67RSTLH9hFrpdw/T0BIpVZ
/gIddAxqU2acZ4/cDgDjanLP8v3mTD7ojiCegOkTPdLA/2IN//HhLcSqjDPRIq5g
RGe4y91pOtBVWIMNSv2WZTHqgmJN6pTsgbLryAujHrXMLZy618KBkwMSIEJ7NyVp
pTonmAFy/YTP2KJXNKES1diolHuXBRzbttO+7D/bHFIy3GUlWabr3VWXVLbdDPsj
Xr7AVhol+AFoQjbwaDZ+jAH9ecnLRo+AmZ7sPKccDhrX5NaNYbtxdke2mvewhxBP
KNxSOYkoeobXmzZy7p9O9brb3Auov/2X3/HctjII1ERoBhUJwVB2z3Kfsn13V9K2
zSeXAvkCtVP8hCO5rpK1V2sddlEEOVm5nNJSDwIDAQABo2MwYTAdBgNVHQ4EFgQU
VZWCeGnp/YBt9YoiTncFTbwZD9owHwYDVR0jBBgwFoAUVZWCeGnp/YBt9YoiTncF
TbwZD9owDwYDVR0TAQH/BAUwAwEB/zAOBgNVHQ8BAf8EBAMCAYYwDQYJKoZIhvcN
AQELBQADggIBAB/oH0Ii03Rvv5mjfjyzLpn9nWthqPQvJ+k870N7qVQRVKpnTemf
FtmDoBoZ76MG/O1JSag7LhTrxFyNL3225bNKeYtjiJvnH4Vh55/YDaFXi5+9zw8p
3m/EdrfZQ73Dy1rwQI1ibllTRKInU2b23MC2CeGe4f6hSU60XjtJaznty4j7JvEO
u7t2bZ5oAY77zO1NocCpTO72sSZA+PY1o4Fnpg26BXDh8YhGokXTj0pf03f0HQoh
F1eIepFJtT2GI93e88hrG16PX2DEVP2M0nIStad1YrGFI8S7caRlfwkciuMGphSd
Q7JVHgoyYu+88CLru7rReKqhGPTVxBtFV5og41Qy1AyVCZnOboAW6sQ/EUFURZgB
vUsElkEAodzrmydTFzznhi60Ofx/kpgSXDdKESjVxSrmPGWV0OuTrav1xMGbvU0U
c5oivtDgs1LxS97g0g8FIiXXTPnwijwlsLyx3AVqXZ8xnN7V8QRXK9Yqv4pWE0sI
br8P1iAh9XRhccYptm8OTfWE3FdDCpF9L4ZB01bQaYxpxF+7hu5jkWNgvUIOq3Eu
lBDg3MdT6UszjRvv9InqUaDR0MtK2OMeuZwHnZJCTZeFj98kuuvKWV/HddLGKmc4
bHDwpsDtaedaBp9kDqRSAxA9+e1FeE1xpA+bNIrY39FWtBr0GeTTgiOK
-----END CERTIFICATE-----
"""


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
                'node_id': '52e6eb49-6d59-4bf3-af96-ca3252408a4e',
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
