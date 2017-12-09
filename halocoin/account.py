import copy

from halocoin import custom
from halocoin import tools
from halocoin.service import Service, sync


class AccountService(Service):
    default_account = {
        'amount': 0,
        'count': 0,
        'cache-length': -1,
        'tx_blocks': [],
        'mined_blocks': []
    }

    default_peer = {
        'node_id': 'Anon',
        'ip': '',
        'port': 0,
        'rank': 1,
        'diffLength': '',
        'length': -1
    }

    def __init__(self, engine):
        Service.__init__(self, name='account')
        self.engine = engine
        self.db = None
        self.blockchain = None

    def on_register(self):
        self.db = self.engine.db
        self.blockchain = self.engine.blockchain
        print("Started Account")
        return True

    @sync
    def get_account(self, address, apply_tx_pool=False):
        if self.db.exists(address):
            account = self.db.get(address)
        else:
            account = copy.deepcopy(AccountService.default_account)

        if apply_tx_pool:
            txs = self.blockchain.tx_pool()
            account = self.update_account_with_txs(address, account, txs, add_flag=True)

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
        :param add_flag: Is block being added or removed
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

    def update_account_with_txs(self, address, account, txs, add_flag=True, only_outgoing=False, block_number=-1):
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

        for i in range(int(self.db.get('length')) + 1):
            block = self.db.get(str(i))
            account = self.update_account_with_txs(address, account, block['txs'],
                                                   add_flag=True, block_number=block['length'])

        self.db.put(address, account)
        return 'Updated ' + str(account)

    def known_tx_count(self, address):
        # Returns the number of transactions that pubkey has broadcast.
        def number_of_unconfirmed_txs(_address):
            return len(list(filter(lambda t: _address == tools.tx_owner_address(t), txs_in_pool)))

        account = self.get_account(address)
        txs_in_pool = self.blockchain.tx_pool()
        return account['count'] + number_of_unconfirmed_txs(address)

    def is_tx_affordable(self, address, tx):
        account = self.update_account_with_txs(address,
                                               self.get_account(address),
                                               [tx] + self.blockchain.tx_pool(),
                                               add_flag=True)

        return account['amount'] >= 0

    @sync
    def get_peers(self):
        peers = self.db.get('peer_list')
        if peers is None:
            peers = list()
        peers = sorted(peers, key=lambda x: x['rank'])
        return peers

    @sync
    def add_peer(self, peer, type):
        """
        Add peer can be triggered by 2 different actions: Greetings, Friend of mine
        - Greetings:
          - Peer introduces itself
          - We find out their IP.
          - They report their node_id, port, length, diffLength
          - Rank is initialized to 1
          - If <node_id, ip, port> exists, do nothing.
          - If <node_id> exists, <ip, port> does not, update the peer at node_id.
          - If <ip, port> exists, <node_id> does not, remove all <ip, port> peers. Add new one.
        - Frind of mine:
          - Somebody reports their peer list.
          - Every detail including rank is given by peer.
          - If <node_id> exists, do nothing.
          - If <ip, port> exists, do nothing.
          - Otherwise, add.

        In this sceme, ultimate resolver is greetings messages.
        If we cannot communicate(greet) with a peer in last 24 hours or 50 tries, whichever comes later,
        we drop this peer from the list.
        :param peer: Peer dict to be added
        :param type: Its origin
        :return: None
        """
        if not self.is_peer(peer):
            return

        peers = self.get_peers()

        if type == 'greetings':
            same_node = []
            same_ip_port = []
            add_flag = True
            for i, _peer in enumerate(peers):
                if _peer['node_id'] == peer['node_id'] and _peer['ip'] == peer['ip'] and \
                                _peer['port'] == peer['port']:
                    peer['rank'] = _peer['rank']
                    peers[i] = peer
                    add_flag = False
                    break
                elif _peer['node_id'] == peer['node_id']:
                    same_node.append(i)
                elif _peer['port'] == peer['port'] and _peer['ip'] == peer['ip']:
                    same_ip_port.append(i)

            for i in same_node:
                peers[i]['ip'] = peer['ip']
                peers[i]['port'] = peer['port']
                add_flag = False

            for i in reversed(same_ip_port):
                del peers[i]

            if add_flag:
                peers.append(peer)

        elif type == 'friend_of_mine':
            for _peer in peers:
                if peer['node_id'] == _peer['node_id'] or \
                        (peer['ip'] == _peer['ip'] and peer['port'] == _peer['port']):
                    return
            peers.append(peer)

        self.db.put('peer_list', peers)

    @sync
    def update_peer(self, peer):
        """
        Update peer at node_id=peer['node_id']
        :param peer: A peer dictionary
        :return: None
        """
        if not self.is_peer(peer):
            return

        peers = self.db.get('peer_list')
        for i, _peer in enumerate(peers):
            if peer['node_id'] == _peer['node_id']:
                peers[i] = peer
                break

        from halocoin import api
        api.peer_update()
        self.db.put('peer_list', peers)

    def is_peer(self, peer):
        """
        Integrity check of a peer object.
        - It should be a dictionary
        - Keys must be same as default_peer
        - node_id needs to be valid uuid4
        - node_id must not be equal to our node_id
        :param peer: peer object to check
        :return: whether :param peer is a valid peer object.
        """
        if not isinstance(peer, dict):
            return False

        # Its key set must match default keys
        if set(peer.keys()) != set(AccountService.default_peer.keys()):
            return False

        if not tools.validate_uuid4(peer['node_id']):
            return False

        if peer['node_id'] == self.db.get('node_id'):
            return False

        return True

    @sync
    def get_wallets(self):
        if self.db.exists("wallets"):
            return self.db.get("wallets")
        return {}

    @sync
    def get_wallet(self, name):
        wallets = self.get_wallets()
        if name in wallets:
            return wallets[name]
        else:
            return None

    @sync
    def new_wallet(self, enc_key, wallet_obj):
        wallets = self.get_wallets()
        if wallet_obj.name in wallets:
            return False
        wallets[wallet_obj.name] = tools.encrypt(enc_key, wallet_obj.to_string())
        self.db.put("wallets", wallets)
        return True

    @sync
    def upload_wallet(self, wallet_name, wallet_str):
        wallets = self.get_wallets()
        if wallet_name in wallets:
            return False
        wallets[wallet_name] = wallet_str
        self.db.put("wallets", wallets)
        return True

    @sync
    def remove_wallet(self, name):
        try:
            wallets = self.get_wallets()
            del wallets[name]
            self.db.put("wallets", wallets)
            return True
        except Exception as e:
            return False

    @sync
    def get_default_wallet(self):
        if self.db.exists('default_wallet'):
            return self.db.get('default_wallet')
        else:
            return None

    @sync
    def set_default_wallet(self, wallet_name, password):
        try:
            from halocoin.model.wallet import Wallet
            encrypted_wallet_content = self.get_wallet(wallet_name)
            wallet = Wallet.from_string(tools.decrypt(password, encrypted_wallet_content))
            if wallet.name == wallet_name:
                self.db.put('default_wallet', {
                    "wallet_name": wallet_name,
                    "password": password
                })
                return True
            else:
                return False
        except Exception as e:
            tools.log(e)
            return False

    @sync
    def delete_default_wallet(self):
        self.db.delete('default_wallet')
        return True
