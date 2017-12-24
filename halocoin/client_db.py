import copy

from halocoin import tools, api
from halocoin.service import Service, sync


class ClientDBService(Service):
    default_peer = {
        'node_id': 'Anon',
        'ip': '',
        'port': 0,
        'rank': 1,
        'diffLength': '',
        'length': -1
    }

    def __init__(self, engine):
        Service.__init__(self, name='client_db')
        self.engine = engine
        self.db = None
        self.blockchain = None

    def on_register(self):
        self.db = self.engine.db
        self.blockchain = self.engine.blockchain
        print("Started ClientDB")
        return True

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
            peer['rank'] = 10
            peers.append(peer)

        api.peer_update()
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
    def get_peer_history(self, node_id):
        if self.db.exists('peer_history_' + node_id):
            return self.db.get('peer_history_' + node_id)
        else:
            return {
                "greetings": 0,
                "peer_transfer": 0
            }

    @sync
    def set_peer_history(self, node_id, peer_history):
        self.db.put('peer_history_' + node_id, peer_history)

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
                api.changed_default_wallet()
                return True
            else:
                return False
        except Exception as e:
            tools.log(e)
            return False

    @sync
    def delete_default_wallet(self):
        self.db.delete('default_wallet')
        api.changed_default_wallet()
        return True
