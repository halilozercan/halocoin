import os
import pickle
import sys

import plyvel

from halocoin import tools, api, custom
from halocoin.service import lockit


class ClientDB:
    """
    This is a separate database from blockchain related data.
    Anything that needs to be stored on client side that doesn't depend on blockchain
    should be managed by here.
    """

    default_peer = {
        'node_id': 'Anon',
        'ip': '',
        'port': 0,
        'rank': 1,
        'diffLength': '',
        'length': -1
    }

    def __init__(self, engine):
        self.engine = engine
        self.DB = None
        self.blockchain = None
        try:
            db_location = os.path.join(self.engine.working_dir, 'client.db')
            DB = plyvel.DB(db_location, create_if_missing=True)
            self.DB = DB.prefixed_db(custom.version.encode())
        except Exception as e:
            tools.log(e)
            sys.stderr.write('Database connection cannot be established!\n')

    def get(self, key):
        try:
            return pickle.loads(self.DB.get(str(key).encode()))
        except Exception as e:
            return None

    def put(self, key, value):
        try:
            self.DB.put(str(key).encode(), pickle.dumps(value))
            return True
        except Exception as e:
            return False

    def delete(self, key):
        try:
            self.DB.delete(str(key).encode())
            return True
        except:
            return False

    @lockit('peers')
    def get_peer(self, node_id):
        peers = self.get_peers()
        for _peer in peers:
            if _peer['node_id'] == node_id:
                return _peer
        return None

    @lockit('peers')
    def get_peers(self):
        peers = self.get('peer_list')
        if peers is None:
            peers = list()
        peers = sorted(peers, key=lambda x: x['rank'])
        return peers

    @lockit('peers')
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
                    peer['rank'] *= _peer['rank']
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
        self.put('peer_list', peers)

    @lockit('peers')
    def update_peer(self, peer):
        """
        Update peer at node_id=peer['node_id']
        :param peer: A peer dictionary
        :return: None
        """
        if not self.is_peer(peer):
            return

        peers = self.get('peer_list')
        for i, _peer in enumerate(peers):
            if peer['node_id'] == _peer['node_id']:
                peers[i] = peer
                break

        api.peer_update()
        self.put('peer_list', peers)

    @lockit('peers')
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
        if set(peer.keys()) != set(ClientDB.default_peer.keys()):
            return False

        if not tools.validate_uuid4(peer['node_id']):
            return False

        if peer['node_id'] == self.get('node_id'):
            return False

        return True

    @lockit('peers')
    def get_peer_history(self, node_id):
        if self.get('peer_history_' + node_id) is not None:
            return self.get('peer_history_' + node_id)
        else:
            return {
                "greetings": 0,
                "peer_transfer": 0
            }

    @lockit('peers')
    def set_peer_history(self, node_id, peer_history):
        self.put('peer_history_' + node_id, peer_history)

    @lockit('wallets')
    def get_wallets(self):
        if self.get("wallets") is not None:
            return self.get("wallets")
        return {}

    @lockit('wallets')
    def get_wallet(self, name):
        wallets = self.get_wallets()
        if name in wallets:
            return wallets[name]
        else:
            return None

    @lockit('wallets')
    def new_wallet(self, enc_key, wallet_obj):
        wallets = self.get_wallets()
        if wallet_obj.name in wallets:
            return False
        wallets[wallet_obj.name] = tools.encrypt(enc_key, wallet_obj.to_string())
        self.put("wallets", wallets)
        return True

    @lockit('wallets')
    def upload_wallet(self, wallet_name, wallet_str):
        wallets = self.get_wallets()
        if wallet_name in wallets:
            return False
        wallets[wallet_name] = wallet_str
        self.put("wallets", wallets)
        return True

    @lockit('wallets')
    def remove_wallet(self, name):
        try:
            wallets = self.get_wallets()
            del wallets[name]
            self.put("wallets", wallets)
            return True
        except Exception as e:
            return False

    @lockit('wallets')
    def get_default_wallet(self):
        return self.get('default_wallet')

    @lockit('wallets')
    def set_default_wallet(self, wallet_name, password):
        try:
            from halocoin.model.wallet import Wallet
            encrypted_wallet_content = self.get_wallet(wallet_name)
            wallet = Wallet.from_string(tools.decrypt(password, encrypted_wallet_content))
            if wallet.name == wallet_name:
                self.put('default_wallet', {
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

    @lockit('wallets')
    def delete_default_wallet(self):
        self.delete('default_wallet')
        api.changed_default_wallet()
        return True
