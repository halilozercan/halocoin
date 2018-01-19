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
        'cache-length': -1,
        'tx_blocks': [],
        'assigned_job': '',
        'stake': 0
    }

    def __init__(self, engine):
        self.engine = engine
        self.db = self.engine.db
        self.blockchain = self.engine.blockchain

    @lockit('kvstore')
    def get_account(self, address, apply_tx_pool=False):
        def update_account_with_txs(address, account, txs):
            for tx in txs:
                owner = tools.tx_owner_address(tx)
                if tx['type'] == 'spend':
                    if owner == address:
                        account['amount'] -= -tx['amount']
                        account['count'] += 1
                    if tx['to'] == address:
                        account['amount'] += tx['amount']
                elif tx['type'] == 'reward':
                    # TODO: implement if reward is for this account
                    pass
                elif tx['type'] == 'deposit':
                    if owner == address:
                        account['amount'] -= tx['amount']
                        account['stake'] += tx['amount']
                        account['count'] += 1
                elif tx['type'] == 'withdraw':
                    if owner == address:
                        account['amount'] += tx['amount']
                        account['stake'] -= tx['amount']
                        account['count'] += 1

            return account

        if self.db.exists(address):
            account = self.db.get(address)
        else:
            account = copy.deepcopy(StateDatabase.default_account)

        if apply_tx_pool:
            txs = self.blockchain.tx_pool()
            account = update_account_with_txs(address, account, txs)

        if 'tx_blocks' not in account:
            account['tx_blocks'] = []

        return account

    @lockit('kvstore')
    def remove_account(self, address):
        self.db.delete(address)
        return True

    def update_account(self, address, new_account):
        if new_account['amount'] < 0 or new_account['stake'] < 0:
            return False
        self.db.put(address, new_account)
        return True

    def update_database_with_block(self, block):
        """
        This method should only be called after block passes every check.

        :param block:
        :return: Whether it was a successfull add operation
        """

        txs = sorted(block['txs'], key=lambda x: x['count'] if 'count' in x else -1)

        for tx in txs:
            send_address = tools.tx_owner_address(tx)
            send_account = self.get_account(send_address)

            if tx['type'] == 'mint':
                send_account['amount'] += tools.block_reward(block['length'])
                self.update_account(send_address, send_account)
            elif tx['type'] == 'spend':
                if tx['count'] != self.known_tx_count(send_address, count_pool=False):
                    return False

                recv_address = tx['to']
                recv_account = self.get_account(recv_address)

                send_account['amount'] -= tx['amount']
                send_account['count'] += 1
                send_account['tx_blocks'].append(block['length'])

                recv_account['amount'] += tx['amount']
                recv_account['tx_blocks'].append(block['length'])

                if (recv_account['amount'] < 0) or (send_account['amount'] < 0):
                    return False

                self.update_account(send_address, send_account)
                self.update_account(recv_address, recv_account)
            elif tx['type'] == 'reward':
                auth = self.get_auth(tx['auth'])
                if auth is None:
                    return False
                if tx['pubkeys'] != [tools.get_pubkey_from_certificate(auth['certificate']).to_string()]:
                    return False
                job = self.db.get('job_' + tx['job_id'])
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
                if recv_account['assigned_job'] != tx['job_id']:
                    return False

                self.reward_job(tx['job_id'], tx['to'], block['length'])

                recv_account = self.get_account(tx['to'])
                recv_account['amount'] += job['amount']
                recv_account['tx_blocks'].append(block['length'])
                self.update_account(tx['to'], recv_account)
            elif tx['type'] == 'auth_reg':
                cert_valid = tools.check_certificate_chain(tx['certificate'])
                common_name = tools.get_commonname_from_certificate(tx['certificate'])
                early_reg = self.get_auth(common_name) is None
                if not cert_valid or not early_reg:
                    return False

                self.put_auth(tx['certificate'], tx['host'], tx['supply'])
            elif tx['type'] == 'job_dump':
                # Check if auth is known
                auth = self.get_auth(tx['auth'])
                if auth is None:
                    return False
                elif tx['pubkeys'] != [tools.get_pubkey_from_certificate(auth['certificate']).to_string()]:
                    return False
                # Check if job already exists
                if self.db.exists('job_' + tx['job']['id']):
                    return False

                # Check if authority has remaining supply
                if auth['supply'] < tx['job']['amount']:
                    return False
                auth['supply'] -= tx['job']['amount']

                self.add_new_job(tx['job'], tx['auth'], block['length'])
                self.update_auth(tx['auth'], auth)
            elif tx['type'] == 'deposit':
                if tx['count'] != self.known_tx_count(send_address, count_pool=False):
                    return False
                send_account['amount'] -= tx['amount']
                send_account['stake'] += tx['amount']
                send_account['count'] += 1
                send_account['tx_blocks'].append(block['length'])

                if not (send_account['amount'] >= 0) and (send_account['stake'] >= 0):
                    return False

                self.update_account(send_address, send_account)
                if send_account['stake'] > 0:
                    self.put_address_in_stake_pool(send_address)
            elif tx['type'] == 'withdraw':
                if tx['count'] != self.known_tx_count(send_address, count_pool=False):
                    return False
                send_account['amount'] += tx['amount']
                send_account['stake'] -= tx['amount']
                send_account['count'] += 1
                send_account['tx_blocks'].append(block['length'])

                if not (send_account['amount'] >= 0) and (send_account['stake'] >= 0):
                    return False

                self.update_account(send_address, send_account)
                if send_account['stake'] == 0:
                    self.remove_address_from_stake_pool(send_address)
        """
        # We go over the list of requested jobs in a deterministic way. Thus,
        # every client will agree on how to evaluate multiple job bidding at the same block.
        
        for requested_job_id in sorted(requested_jobs.keys()):
            for bid in sorted(requested_jobs[requested_job_id], key=lambda x: x[1]):
                bidder = bid[0]
                bid_amount = bid[1]
                if self.assign_job(requested_job_id, bidder, bid_amount, block['length']):
                    break

        # Now we take a look at back, we unassign jobs that are still not rewarded
        from halocoin import custom
        assigned_jobs = self.get_assigned_jobs()
        for job in assigned_jobs.values():
            if job['status_list'][-1]['block'] <= (block['length'] - custom.drop_job_block_count):
                self.unassign_job(job['id'], block['length'])
        """
        # Version 0.0007c: Change of job assignment to stakes
        # Unassign all jobs and redistribute
        if block['length'] % custom.assignment_period == 0:
            assigned_jobs = self.get_assigned_jobs().values()
            for job in assigned_jobs:
                self.unassign_job(job['id'], block['length'])

            available_jobs = sorted(self.get_available_jobs().values(), key=lambda x: x['amount'], reverse=True)
            accounts = [(self.get_account(address), address) for address in self.get_stake_pool()]
            accounts = sorted(accounts,
                              key=lambda x: x[0]['stake'],
                              reverse=True)
            ji = 0
            ai = 0
            while ji < len(available_jobs) and ai < len(accounts):
                if available_jobs[ji]['amount'] > accounts[ai][0]['stake']:
                    ji += 1
                else:
                    self.assign_job(available_jobs[ji]['id'], accounts[ai][1], block['length'])
                    ji += 1
                    ai += 1

        return True

    def rollback_block(self, block):
        # TODO: 0.007-9c changes
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
                self.delete_job(tx['job']['id'])
            elif tx['type'] == 'reward':
                job = self.get_job(tx['request']['job_id'])
                for status in reversed(job['status_list']):
                    if status['block'] == block['length']:
                        job['status_list'].remove(status)
                    else:
                        break
                self.db.update_job(job)

    @lockit('kvstore')
    def known_tx_count(self, address, count_pool=True, txs_in_pool=None):
        # Returns the number of transactions that pubkey has broadcast.
        def number_of_unconfirmed_txs(_address):
            return len(list(filter(lambda t: _address == tools.tx_owner_address(t), txs_in_pool)))

        account = self.get_account(address)
        surplus = 0
        if count_pool:
            txs_in_pool = self.blockchain.tx_pool()
            surplus += number_of_unconfirmed_txs(address)
        return account['count'] + surplus

    @lockit('kvstore')
    def get_auth(self, auth_name):
        return self.db.get('auth_' + auth_name)

    def put_auth(self, cert_pem, host, supply):
        if tools.check_certificate_chain(cert_pem):
            common_name = tools.get_commonname_from_certificate(cert_pem)
            auth = {
                'certificate': cert_pem,
                'host': host,
                'supply': supply
            }
            self.db.put('auth_' + common_name, auth)

    def update_auth(self, auth_name, auth):
        self.db.put('auth_' + auth_name, auth)

    def delete_auth(self, cert_pem):
        common_name = tools.get_commonname_from_certificate(cert_pem)
        self.db.delete('auth_' + common_name)

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
        job_list = self.db.get('job_list')
        result = {}
        for job_id in job_list:
            job = self.get_job(job_id)
            # Here we check last transaction made on the job.
            if job['status_list'][-1]['action'] == 'add' or job['status_list'][-1]['action'] == 'unassign':
                result[job_id] = self.db.get('job_' + job_id)
        return result

    @lockit('kvstore')
    def get_assigned_jobs(self):
        job_list = self.db.get('job_list')
        result = {}
        for job_id in job_list:
            job = self.get_job(job_id)
            # Here we check last transaction made on the job.
            if job['status_list'][-1]['action'] == 'assign':
                result[job_id] = self.db.get('job_' + job_id)
        return result

    def add_new_job(self, tx_job, auth, block_number):
        job = copy.deepcopy(tx_job)
        job['auth'] = auth
        job['status_list'] = [{
            'action': 'add',
            'block': block_number
        }]
        job_list = self.db.get('job_list')
        job_list.append(job['id'])
        self.db.put('job_list', job_list)
        self.db.put('job_' + job['id'], job)
        return True

    def assign_job(self, job_id, address, block_number):
        job = self.db.get('job_' + job_id)
        if job['status_list'][-1]['action'] != 'add' and job['status_list'][-1]['action'] != 'unassign':
            return False
        account = self.get_account(address)
        if account['assigned_job'] != '':
            return False

        job['status_list'].append({
            'action': 'assign',
            'block': block_number,
            'address': address
        })
        account['assigned_job'] = job_id
        account['stake'] -= (job['amount'] // 2)
        self.db.put('job_' + job_id, job)
        self.update_account(address, account)
        if account['stake'] == 0:
            self.remove_address_from_stake_pool(address)
        return True

    def reward_job(self, job_id, address, block_number):
        job = self.db.get('job_' + job_id)
        if job['status_list'][-1]['action'] != 'assign':
            return False
        account = self.get_account(address)
        if account['assigned_job'] != job_id:
            return False

        job['status_list'].append({
            'action': 'reward',
            'block': block_number,
            'address': address
        })
        account['assigned_job'] = ''
        self.db.put('job_' + job_id, job)
        self.update_account(address, account)
        return True

    def unassign_job(self, job_id, block_number):
        job = self.db.get('job_' + job_id)
        if job['status_list'][-1]['action'] != 'assign':
            return False

        last_assigned_address = job['status_list'][-1]['address']
        last_assigned_account = self.get_account(last_assigned_address)

        job = self.db.get('job_' + job_id)
        job['status_list'].append({
            'action': 'unassign',
            'block': block_number
        })
        last_assigned_account['assigned_job'] = ''
        self.db.put('job_' + job_id, job)
        self.update_account(last_assigned_address, last_assigned_account)
        return True

    @lockit('kvstore')
    def get_job(self, job_id):
        return self.db.get('job_' + job_id)

    def update_job(self, job):
        return self.db.put('job_' + job['id'], job)

    def delete_job(self, job_id):
        job_list = self.db.get('job_list')
        job_list.remove(job_id)
        self.db.put('job_list', job_list)
        self.db.delete('job_' + job_id)
        return True
