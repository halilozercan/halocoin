from halocoin import tools
from halocoin.model.tx import Transaction


class AuthRegTransaction(Transaction):
    def __init__(self, certificate, host, privkey=None):
        pubkeys = [tools.get_pubkey_from_certificate(certificate).to_string()]
        Transaction.__init__(self, pubkeys, privkey)
        self.certificate = certificate

    def is_valid(self):
        if not Transaction.is_valid(self):
            return False
