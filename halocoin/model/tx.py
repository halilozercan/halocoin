import copy
import yaml

from halocoin import tools, custom


class Transaction:
    def __init__(self, pubkeys, privkey=None):
        self.signatures = []
        self.pubkeys = pubkeys
        self.version = custom.version
        if privkey is not None:
            self.sign(privkey)

    def is_valid(self):
        # Base transaction is only checked for signature and version number
        # Child classes should override this method by calling super.
        if self.version != custom.version:
            return False

        if not isinstance(self.signatures, list) or len(self.signatures) == 0:
            tools.log('no signatures')
            return False
        if not isinstance(self.signatures, list) or len(self.pubkeys) == 0:
            tools.log('no pubkeys')
            return False
        if len(self.signatures) > len(self.pubkeys):
            tools.log('There are not enough pubkeys to evaluate signatures')
            return False

        signatures = self.signatures
        self.signatures = []
        str = Transaction.dumps(self)
        encoded_str = tools.det_hash(str)
        if not Transaction.sigs_match(signatures, self.pubkeys, encoded_str):
            tools.log('sigs do not match')
            return False
        return True

    def sign(self, privkey):
        from ecdsa import SigningKey
        if not isinstance(privkey, SigningKey):
            raise TypeError('Given private key is not a proper SigningKey')
        self.signatures = []
        str = Transaction.dumps(self)
        encoded_str = tools.det_hash(str)
        self.signatures = [tools.sign(tools.det_hash(encoded_str), privkey)]

    @staticmethod
    def sigs_match(_sigs, _pubs, msg):
        pubs = copy.deepcopy(_pubs)
        sigs = copy.deepcopy(_sigs)

        def match(sig, pubs, msg):
            for p in pubs:
                if tools.signature_verify(msg, sig, p):
                    return {'bool': True, 'pub': p}
            return {'bool': False}

        for sig in sigs:
            a = match(sig, pubs, msg)
            if not a['bool']:
                return False
            sigs.remove(sig)
            pubs.remove(a['pub'])
        return True

    @staticmethod
    def loads(str):
        obj = yaml.load(str)
        if isinstance(obj, Transaction):
            return obj
        else:
            raise ValueError('Given stream does not encode a Transaction')

    @staticmethod
    def dumps(tx):
        return yaml.dump(tx)