from halocoin.model.tx import Transaction


class MintTransaction(Transaction):
    def __init__(self, pubkeys, privkey, amount):
        Transaction.__init__(self, pubkeys)
        self.amount = amount
        self.sign(privkey)

    def is_valid(self):
        if not Transaction.is_valid(self):
            return False
        if not isinstance(self.amount, (int, float)):
            return False
        if not self.amount <= 0:
            return False
