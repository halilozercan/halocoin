import copy

from halocoin import tools, custom
from halocoin.service import lockit


class StateDatabase:
    """
    StateDatabase is where we evaluate and store the current state of blockchain.
    User accounts referring addresses, jobs, authorities and many more are stored here.
    State change can be triggered by only adding or removing a block.
    A state can be simulated against a transaction, multiple transactions or blocks.
    These simulations can be recorded or removed upon the result of simulation.
    Simulations are basically not committed database changes.
    """
    default_account = {
        'amount': 0,
        'count': 0,
        'tx_blocks': set(),
        'assigned_job': {
            'auth': None,
            'job_id': None
        },
        'stakes': {

        }
    }

    def __init__(self, engine):
        self.engine = engine
        self.db = self.engine.db
        self.blockchain = self.engine.blockchain

    @lockit('kvstore')
    def get_account(self, address):
        if self.db.exists(address):
            account = self.db.get(address)
        else:
            account = copy.deepcopy(StateDatabase.default_account)
        return account

    def update_account(self, address, new_account):
        if new_account['amount'] < 0:
            return False
        for auth_name, stake in new_account['stakes'].items():
            if stake < 0:
                return False
        self.db.put(address, new_account)
        return True

    @lockit('kvstore')
    def get_auth_list(self):
        if self.db.exists('auth_list'):
            return self.db.get('auth_list')
        else:
            return list()

    def update_auth_list(self, auth_list):
        self.db.put('auth_list', auth_list)

    @lockit('kvstore')
    def get_auth(self, auth_name):
        return self.db.get('auth_' + auth_name)

    def put_auth(self, **kwargs):
        """
        Register a new subauthority.
        :param kwargs:
            - certificate: Certificate in PEM format
            - description: Description of new authority
            - block_number: At which block is this authority registered
            - host: Main page of authority website
            - supply: Initial supply
        :return:
        """
        if tools.check_certificate_chain(kwargs['certificate']):
            common_name = tools.get_commonname_from_certificate(kwargs['certificate'])
            auth = {
                'name': common_name,
                'description': kwargs['description'],
                'register_block': kwargs['block_number'],
                'certificate': kwargs['certificate'],
                'host': kwargs['host'],
                'initial_supply': kwargs['supply'],
                'current_supply': kwargs['supply'],
                'pubkeys': [tools.get_pubkey_from_certificate(kwargs['certificate']).to_string()]
            }
            self.db.put('auth_' + common_name, auth)
            auth_list = self.get_auth_list()
            auth_list.append(common_name)
            self.update_auth_list(auth_list)

    def update_auth(self, auth_name, auth):
        self.db.put('auth_' + auth_name, auth)

    def delete_auth(self, cert_pem):
        common_name = tools.get_commonname_from_certificate(cert_pem)
        self.db.delete('auth_' + common_name)

    @lockit('kvstore')
    def get_job(self, auth_name, job_id):
        return self.db.get('job_' + auth_name + '_' + job_id)

    def update_job(self, job):
        return self.db.put('job_' + job['auth'] + '_' + job['id'], job)

    def delete_job(self, auth_name, job_id):
        job_list = self.db.get('auth_' + auth_name + '_jobs')
        job_list.remove(job_id)
        self.db.put('auth_' + auth_name + '_jobs', job_list)
        self.db.delete('job_' + auth_name + '_' + job_id)
        return True

    @lockit('kvstore')
    def get_stake_pool(self):
        result = self.db.get('stake_pool')
        if result is None:
            return set()
        else:
            return set(self.db.get('stake_pool'))

    def put_address_in_stake_pool(self, address):
        stake_pool = self.get_stake_pool()
        stake_pool.add(address)
        self.db.put('stake_pool', stake_pool)

    def remove_address_from_stake_pool(self, address):
        stake_pool = self.get_stake_pool()
        stake_pool.remove(address)
        self.db.put('stake_pool', stake_pool)

    @lockit('kvstore')
    def get_available_jobs(self):
        auth_list = self.db.get('auth_list')
        result = {}
        for auth_name in auth_list:
            job_list = self.db.get('auth_' + auth_name + '_jobs')
            for job_id in job_list:
                job = self.get_job(auth_name, job_id)
                # Here we check last transaction made on the job.
                if job['status_list'][-1]['action'] == 'add' or job['status_list'][-1]['action'] == 'unassign':
                    result[job_id] = self.db.get('job_' + job_id)
        return result

    @lockit('kvstore')
    def get_assigned_jobs(self):
        auth_list = self.db.get('auth_list')
        result = {}
        for auth_name in auth_list:
            job_list = self.db.get('auth_' + auth_name + '_jobs')
            for job_id in job_list:
                job = self.get_job(auth_name, job_id)
                # Here we check last transaction made on the job.
                if job['status_list'][-1]['action'] == 'assign':
                    result[job_id] = self.db.get('job_' + job_id)
        return result

    @lockit('kvstore')
    def get_rewarded_jobs(self):
        auth_list = self.db.get('auth_list')
        result = {}
        for auth_name in auth_list:
            job_list = self.db.get('auth_' + auth_name + '_jobs')
            for job_id in job_list:
                job = self.get_job(auth_name, job_id)
                # Here we check last transaction made on the job.
                if job['status_list'][-1]['action'] == 'reward':
                    result[job_id] = self.db.get('job_' + job_id)
        return result

    def add_new_job(self, **kwargs):
        """

        :param kwargs:
            - auth: Which authority supplied this job
            - reward: Amount of reward
            - id: Original job id
            - timestamp: Unique timestamp given by supplying auth
            - image: Which docker image is going to be used
            - download_url:
            - upload_url:
            - hashsum: SHA256 hashsum of the job. It is not necessarily exact file hashsum.
            - block_number: At which block this job was added
        :return:
        """
        job = {
            'auth': kwargs['auth'],
            'reward': kwargs['reward'],
            'id': kwargs['id'],
            'timestamp': kwargs['timestamp'],
            'image': kwargs['image'],
            'download_url': kwargs['download_url'],
            'upload_url': kwargs['upload_url'],
            'hashsum': kwargs['hashsum'],
            'status_list': [{
                'action': 'add',
                'block': kwargs['block_number']
            }]
        }
        job_list = self.db.get('auth_' + kwargs['auth'] + '_jobs')
        job_list.append(job['id'])
        self.update_auth_list(job_list)
        self.update_job(job)
        return True

    def assign_job(self, job, address, block_number):
        if job['status_list'][-1]['action'] != 'add' and job['status_list'][-1]['action'] != 'unassign':
            return False
        account = self.get_account(address)
        if account['assigned_job']['auth'] is not None:
            return False

        job['status_list'].append({
            'action': 'assign',
            'block': block_number,
            'address': address
        })
        account['assigned_job'] = {
            'auth': job['auth'],
            'job_id': job['id']
        }
        account['stakes'][job['auth']] -= int(job['amount'] * custom.assignment_stake_burn)
        self.update_job(job)
        self.update_account(address, account)
        self.check_stake_pool(account)
        return True

    def reward_job(self, job, address, block_number):
        job['status_list'].append({
            'action': 'reward',
            'block': block_number,
            'address': address
        })
        self.db.update_job(job)
        return True

    def unassign_job(self, job, block_number):
        if job['status_list'][-1]['action'] != 'assign':
            return False

        last_assigned_address = job['status_list'][-1]['address']
        last_assigned_account = self.get_account(last_assigned_address)

        job['status_list'].append({
            'action': 'unassign',
            'block': block_number
        })
        last_assigned_account['assigned_job'] = ''
        self.update_job(job)
        self.update_account(last_assigned_address, last_assigned_account)
        return True

    def update_database_with_tx(self, tx, block_length):
        send_address = tools.tx_owner_address(tx)
        send_account = self.get_account(send_address)

        if tx['type'] == 'mint':
            send_account['amount'] += tools.block_reward(block_length)
            self.update_account(send_address, send_account)
        elif tx['type'] == 'spend':
            if tx['count'] < self.known_tx_count(send_address):
                return False

            recv_address = tx['to']
            recv_account = self.get_account(recv_address)

            send_account['amount'] -= tx['amount']
            send_account['count'] = (tx['count'] + 1)
            send_account['tx_blocks'].add(block_length)

            recv_account['amount'] += tx['amount']
            recv_account['tx_blocks'].add(block_length)

            if (recv_account['amount'] < 0) or (send_account['amount'] < 0):
                return False

            self.update_account(send_address, send_account)
            self.update_account(recv_address, recv_account)
        elif tx['type'] == 'reward':
            auth = self.get_auth(tx['auth'])
            if auth is None:
                return False
            if tx['pubkeys'] != auth['pubkeys']:
                return False
            job = self.get_job(tx['auth'], tx['job_id'])
            last_change = job['status_list'][-1]
            # This job is not assigned to anyone right now.
            if last_change['action'] != 'assign':
                return False
            # Reward address is not currently assigned to the job.
            if last_change['address'] != tx['to']:
                return False
            if job['auth'] != tx['auth']:
                return False

            recv_account = self.get_account(tx['to'])
            # Receiving account does not have the same assignment
            if recv_account['assigned_job']['auth'] != tx['auth'] or \
                recv_account['assigned_job']['job_id'] != tx['job_id']:
                return False

            self.reward_job(job, tx['to'], block_length)

            recv_account['assigned_job'] = {
                'auth': None,
                'job_id': None
            }
            recv_account['stakes'][tx['auth']] += int(job['amount'] * custom.assignment_stake_burn)
            recv_account['amount'] += int(job['amount'] * (1 - custom.assignment_stake_burn))
            recv_account['tx_blocks'].add(block_length)
            self.update_account(tx['to'], recv_account)
        elif tx['type'] == 'auth_reg':
            cert_valid = tools.check_certificate_chain(tx['certificate'])
            common_name = tools.get_commonname_from_certificate(tx['certificate'])
            early_reg = self.get_auth(common_name) is None
            if not cert_valid or not early_reg:
                return False

            self.put_auth(certificate=tx['certificate'], host=tx['host'],
                          supply=tx['supply'], block_number=block_length)
        elif tx['type'] == 'job_dump':
            # Check if auth is known
            auth = self.get_auth(tx['auth'])
            if auth is None:
                return False
            elif tx['pubkeys'] != auth['pubkeys']:
                return False
            # Check if job already exists
            if self.get_job(tx['auth'], tx['job']['id']) is not None:
                return False

            # Check if authority has remaining supply
            if auth['supply'] < tx['job']['amount']:
                return False
            auth['supply'] -= tx['job']['amount']

            self.add_new_job(auth=tx['auth'], reward=tx['job']['amount'], id=tx['job']['id'],
                             timestamp=tx['job']['timestamp'], image=tx['job']['image'],
                             download_url=tx['job']['download_url'], upload_url=tx['job']['upload_url'],
                             hashsum=tx['job']['hashsum'], block_number=block_length)
            self.update_auth(tx['auth'], auth)
        elif tx['type'] == 'deposit':
            auth = self.get_auth(tx['auth'])
            if auth is None:
                return False
            if tx['count'] < self.known_tx_count(send_address):
                return False
            send_account['amount'] -= tx['amount']
            if tx['auth'] in send_account['stakes']:
                send_account['stakes'][tx['auth']] += tx['amount']
            else:
                send_account['stakes'][tx['auth']] = tx['amount']
            send_account['count'] = (tx['count'] + 1)
            send_account['tx_blocks'].add(block_length)

            if not (send_account['amount'] >= 0) and (send_account['stake'] >= 0):
                return False

            self.update_account(send_address, send_account)
            self.check_stake_pool(send_account)
        elif tx['type'] == 'withdraw':
            auth = self.get_auth(tx['auth'])
            if auth is None:
                return False
            if tx['count'] < self.known_tx_count(send_address):
                return False
            send_account['amount'] -= tx['amount']
            if tx['auth'] in send_account['stakes']:
                send_account['stakes'][tx['auth']] -= tx['amount']
            else:
                return False
            send_account['count'] = (tx['count'] + 1)
            send_account['tx_blocks'].add(block_length)

            if not (send_account['amount'] >= 0) and (send_account['stake'] >= 0):
                return False

            self.update_account(send_address, send_account)
            self.check_stake_pool(send_account)
        else:
            return False
        return True

    def update_database_with_block(self, block):
        """
        This method should only be called after block passes every check.

        :param block:
        :return: Whether it was a successfull add operation
        """

        txs = sorted(block['txs'], key=lambda x: x['count'] if 'count' in x else -1)

        for tx in txs:
            result = self.update_database_with_tx(tx, block['length'])
            if not result:
                return False

        # Version 0.0012c: Job assignment is now dynamic.
        # Unassign jobs at T, reassign jobs whenever available
        #
        if block['length'] % custom.assignment_period == 0:
            assigned_jobs = self.get_assigned_jobs().values()
            for job in assigned_jobs:
                assigned_block = job['status_list'][-1]['block']
                if assigned_block <= (block['length'] - custom.unassignment_after*custom.assignment_period):
                    self.unassign_job(job['id'], block['length'])

            available_jobs = sorted(self.get_available_jobs().values(),
                                    key=lambda x: (x['amount'], x['id']),
                                    reverse=True)

            accounts = [(self.get_account(address), address) for address in self.get_stake_pool()]
            accounts = sorted(accounts,
                              key=lambda x: (x[0]['stake'], x[1]),
                              reverse=True)
            ji = 0
            ai = 0
            while ji < len(available_jobs) and ai < len(accounts):
                if available_jobs[ji]['amount'] > accounts[ai][0]['stake']:
                    ji += 1
                else:
                    self.assign_job(available_jobs[ji], accounts[ai][1], block['length'])
                    ji += 1
                    ai += 1

        return True

    def get_valid_txs_for_next_block(self, txs, new_length):
        txs = sorted(txs, key=lambda x: x['count'] if 'count' in x else -1)
        valid_txs = []
        self.db.simulate()
        for tx in txs:
            result = self.update_database_with_tx(tx, new_length)
            if result:
                valid_txs.append(tx)
        self.db.rollback()
        return valid_txs

    def rollback_block(self, block):
        # TODO: 0.007-12c changes
        """
        A block rollback means removing the block from chain.
        A block is defined by its transactions. Here we rollback every object in database to the version
        that existed before this block. Blocks must be removed one by one.

        :param block: Block to be removed
        :return: Success of removal
        """
        current_length = self.db.get('length')
        if block['length'] != current_length:
            # Block is not at the top the chain
            return False

        for tx in block['txs']:
            tx_owner_address = tools.tx_owner_address(tx)
            owner_account = self.get_account(tx_owner_address)
            if tx['type'] == 'mint':
                owner_account['amount'] -= tools.block_reward(block['length'])
                self.db.put(tx_owner_address, owner_account)
            elif tx['type'] == 'spend':
                owner_account['amount'] += tx['amount']
                owner_account['count'] -= 1
                owner_account['tx_blocks'].remove(block['length'])

                receiver_account = self.db.get(tx['to'])
                receiver_account['amount'] -= tx['amount']
                receiver_account['tx_blocks'].remove(block['length'])

                self.db.put(tx_owner_address, owner_account)
                self.db.put(tx['to'], receiver_account)
            elif tx['type'] == 'deposit':
                owner_account['amount'] += tx['amount']
                owner_account['stake'] -= tx['amount']
                owner_account['count'] -= 1
                owner_account['tx_blocks'].remove(block['length'])

                self.update_account(tx_owner_address, owner_account)
                if owner_account['stake'] == 0:
                    self.remove_address_from_stake_pool(tx_owner_address)
            elif tx['type'] == 'withdraw':
                owner_account['amount'] -= tx['amount']
                owner_account['stake'] += tx['amount']
                owner_account['count'] -= 1
                owner_account['tx_blocks'].remove(block['length'])

                self.update_account(tx_owner_address, owner_account)
                if owner_account['stake'] > 0:
                    self.put_address_in_stake_pool(tx_owner_address)
            elif tx['type'] == 'auth_reg':
                self.delete_auth(tx['certificate'])
            elif tx['type'] == 'job_dump':
                self.delete_job(tx['auth'], tx['job']['id'])
            elif tx['type'] == 'reward':
                job = self.get_job(tx['auth'], tx['job_id'])
                for status in reversed(job['status_list']):
                    if status['block'] == block['length']:
                        job['status_list'].remove(status)
                    else:
                        break
                self.db.update_job(job)

    @lockit('kvstore')
    def known_tx_count(self, address, count_pool=False):
        # Returns the number of transactions that pubkey has broadcast.
        def highest_order_unconfirmed_tx(_address):
            # Find the transactions that include 'count', broadcasted from _address
            txs = list(filter(lambda t: _address == tools.tx_owner_address(t) and 'count' in t, txs_in_pool))
            if len(txs) > 0:
                tx = max(txs, key=lambda t: t['count'])
                return tx['count']
            else:
                return -1

        account = self.get_account(address)
        if count_pool:
            txs_in_pool = self.blockchain.tx_pool()
            pool_winner = highest_order_unconfirmed_tx(address) + 1
            if account['count'] < pool_winner:
                account['count'] = pool_winner
        return account['count']
