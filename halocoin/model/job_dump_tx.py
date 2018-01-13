from halocoin import tools
from halocoin.model.tx import Transaction


class JobDumpTransaction(Transaction):
    def __init__(self, pubkeys, jobid,  privkey=None):
        Transaction.__init__(self, pubkeys, privkey)


    def is_valid(self):
        if not Transaction.is_valid(self):
            return False
