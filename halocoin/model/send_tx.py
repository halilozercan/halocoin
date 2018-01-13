from halocoin import tools
from halocoin.model.tx import Transaction


class SendTransaction(Transaction):
    def __init__(self, pubkeys, amount, to, privkey=None):
        Transaction.__init__(self, pubkeys, privkey)
        self.amount = amount
        self.to = to

    def is_valid(self):
        if not Transaction.is_valid(self):
            return False

        if not isinstance(self.amount, (int, float)):
            return False

        if self.amount <= 0:
            tools.log('Transaction cannot have negative value')
            return False

        if not tools.is_address_valid(self.to):
            tools.log('Transaction address is not valid')
            return False
