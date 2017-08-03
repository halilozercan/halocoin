import copy
import json
import leveldb
import os

import tools, custom
from service import Service, sync


class AccountService(Service):
    default_account = {
        'amount': 0,
        'count': 0,
        'cache-length': -1,
        'tx_blocks': [],
        'mined_blocks': []
    }

    def __init__(self, engine):
        Service.__init__(self, name='account')
        self.engine = engine
        self.db = None
        self.blockchain = None

    def on_register(self):
        self.db = self.engine.db
        self.blockchain = self.engine.blockchain
        return True

    @sync
    def get_account(self, address, apply_tx_pool=False):
        if self.db.exists(address):
            account = self.db.get(address)
        else:
            account = copy.deepcopy(AccountService.default_account)

        if apply_tx_pool:
            txs = self.blockchain.tx_pool()
            account = AccountService.update_account_with_txs(address, account, txs, add_flag=True)

        if 'tx_blocks' not in account:
            account['tx_blocks'] = []
        if 'mined_blocks' not in account:
            account['mined_blocks'] = []

        return account

    @sync
    def remove_account(self, address):
        self.db.delete(address)
        return True

    @sync
    def update_account(self, address, new_account):
        if new_account['amount'] < 0:
            return False
        self.db.put(address, new_account)
        return True

    @sync
    def update_accounts_with_block(self, block, add_flag=True, simulate=False):
        """

        :param block:
        :param add_flag:
        :param simulate: Do not actually update the accounts, return any irregularity
        :return:
        """

        def apply(a, b):
            if isinstance(a, int):
                if add_flag:
                    a += b
                else:
                    a -= b
            elif isinstance(a, list):
                if add_flag:
                    a.append(b)
                else:
                    a.remove(b)
            return a

        def get_acc(address):
            if not simulate:
                account = self.get_account(address)
            else:
                if address not in account_sandbox:
                    account = self.get_account(address)
                    account_sandbox[address] = account
                account = account_sandbox[address]
            return account

        def update_acc(address, account):
            if not simulate:
                self.update_account(address, account)
            else:
                account_sandbox[address] = account
            return True

        flag = True
        account_sandbox = {}

        for tx in block['txs']:
            send_address = tools.tx_owner_address(tx)
            send_account = get_acc(send_address)

            if tx['type'] == 'mint':
                send_account['amount'] = apply(send_account['amount'], custom.block_reward)
                send_account['mined_blocks'] = apply(send_account['mined_blocks'], block['length'])
            elif tx['type'] == 'spend':
                recv_address = tx['to']
                recv_account = get_acc(recv_address)

                send_account['amount'] = apply(send_account['amount'], -tx['amount'])
                send_account['amount'] = apply(send_account['amount'], -custom.fee)
                send_account['count'] = apply(send_account['count'], 1)
                send_account['tx_blocks'] = apply(send_account['tx_blocks'], block['length'])

                recv_account['amount'] = apply(recv_account['amount'], tx['amount'])
                recv_account['tx_blocks'] = apply(recv_account['tx_blocks'], block['length'])
                flag &= (recv_account['amount'] >= 0)

            flag &= (send_account['amount'] >= 0)

            if not flag:
                return False
            else:
                update_acc(send_address, send_account)
                if tx['type'] == 'spend':
                    update_acc(recv_address, recv_account)

        return flag

    @staticmethod
    def update_account_with_txs(address, account, txs, add_flag=True, only_outgoing=False, block_number=-1):
        def apply(a, b):
            if isinstance(a, int):
                if add_flag:
                    a += b
                else:
                    a -= b
            elif isinstance(a, list):
                if add_flag:
                    a.append(b)
                else:
                    a.remove(b)
            return a

        for tx in txs:
            owner = tools.tx_owner_address(tx)
            if tx['type'] == 'mint' and owner == address:
                account['amount'] = apply(account['amount'], custom.block_reward)
                if block_number != -1:
                    account['mined_blocks'] = apply(account['mined_blocks'], block_number)
            elif tx['type'] == 'spend':
                if owner == address:
                    account['amount'] = apply(account['amount'], -tx['amount'])
                    account['amount'] = apply(account['amount'], -custom.fee)
                    account['count'] = apply(account['count'], 1)
                    if block_number != -1:
                        account['tx_blocks'] = apply(account['tx_blocks'], block_number)
                elif tx['to'] == address and not only_outgoing:
                    account['amount'] = apply(account['amount'], tx['amount'])
                    if block_number != -1:
                        account['tx_blocks'] = apply(account['tx_blocks'], block_number)
        return account

    def invalidate_cache(self, address):
        account = copy.deepcopy(AccountService.default_account)

        for i in range(int(self.db.get('length'))+1):
            block = self.db.get(str(i))
            account = AccountService.update_account_with_txs(address, account, block['txs'],
                                                             add_flag=True, block_number=block['length'])

        self.db.put(address, account)
        return 'Updated ' + str(account)

    def known_tx_count(self, address):
        # TODO: address is a address object from database. Find the real address string inside
        # Returns the number of transactions that pubkey has broadcast.
        def number_of_unconfirmed_txs(address):
            return len(filter(lambda t: address == tools.tx_owner_address(t), txs_in_pool))

        account = self.get_account(address)
        txs_in_pool = self.blockchain.tx_pool()
        return account['count'] + number_of_unconfirmed_txs(address)

    def is_tx_affordable(self, address, tx):
        account = AccountService.update_account_with_txs(address,
                                                         self.get_account(address),
                                                         [tx] + self.blockchain.tx_pool(),
                                                         add_flag=True)

        return account['amount'] >= 0