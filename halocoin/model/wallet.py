import os
import yaml

from ecdsa import NIST192p
from ecdsa.util import randrange_from_seed__trytryagain
from ecdsa import SigningKey

from halocoin import tools


class Wallet:

    def __init__(self, name, privkey=None):
        """
        A wallet object is initialized by a private key.
        """
        self.name = name
        if privkey is None:
            secexp = randrange_from_seed__trytryagain(os.urandom(NIST192p.baselen), NIST192p.order)
            self.privkey = SigningKey.from_secret_exponent(secexp, curve=NIST192p)
        else:
            self.privkey = privkey
        self.pubkey = self.privkey.get_verifying_key()
        self.address = tools.make_address([self.pubkey], 1)

    def get_pubkey_str(self):
        return self.pubkey.to_string()

    def get_privkey_str(self):
        return self.privkey.to_string()

    def to_string(self):
        return yaml.dump({
            'name': self.name,
            'privkey': self.get_privkey_str()
        })

    @staticmethod
    def from_string(wallet_string):
        wallet_dict = yaml.load(wallet_string)
        return Wallet(wallet_dict['name'], SigningKey.from_string(wallet_dict['privkey']))

