import copy

from halocoin import tools
from halocoin.service import Service, sync


class AccountService(Service):
    """
    AccountService is where we evaluate and store the current state of blockchain.
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
        'mined_blocks': [],
        'assigned_job': ''
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
            account = self.update_account_with_txs(address, account, txs)

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
    def check_tx_validity_to_blockchain(self, tx):
        current_length = self.db.get('length')
        send_address = tools.tx_owner_address(tx)
        send_account = self.get_account(send_address)

        if tx['type'] == 'mint':
            send_account['amount'] += tools.block_reward(current_length)
            return send_account['amount'] >= 0
        elif tx['type'] == 'spend':
            if tx['count'] != self.known_tx_count(send_address):
                return False

            recv_address = tx['to']
            recv_account = self.db.get(recv_address)

            send_account['amount'] -= tx['amount']
            send_account['count'] += 1

            recv_account['amount'] += tx['amount']
            return (recv_account['amount'] >= 0) and (send_account['amount'] >= 0)
        elif tx['type'] == 'reward':
            # TODO: Same auth
            # Check whether rewarding transaction has
            # (job_dump.auth=reward.auth), (reward = auction bidding), (receiver = auction winner)
            job = self.db.get('job_' + tx['job_id'])
            last_change = job['status_list'][-1]
            # This job is not assigned to anyone right now.
            if last_change['action'] != 'assign':
                return False

            # Reward is addressed to wrong address.
            if last_change['address'] != tx['to']:
                return False

            recv_account = self.db.get(last_change['address'])
            # Receiving account does not have the same assignment
            if recv_account['assigned_job'] != tx['job_id']:
                return False

            recv_account['amount'] += tx['amount']
            return recv_account['amount'] >= 0
        elif tx['type'] == 'auth_reg':
            cert_valid = tools.check_certificate_chain(tx['certificate'])
            early_reg = self.find_name_by_certificate(tx['certificate']) is None
            return cert_valid and early_reg
        elif tx['type'] == 'job_dump':
            return not self.db.exists('job_' + tx['job']['id'])
        elif tx['type'] == 'job_request':
            """
            Rules are simple: 
            - job should be newly added or unassigned.
            - requester must not have any other assigned job
            """
            job = self.db.get('job_' + tx['job_id'])
            first_condition = (job['status_list'][-1]['action'] == 'add' or job['status_list'][-1]['action'] == 'unassign')
            account = self.get_account(send_address)
            second_condition = (account['assigned_job'] == '')
            third_condition = job['min_amount'] <= tx['amount'] <= job['max_amount']
            return first_condition and second_condition and third_condition

    @sync
    def update_database_with_block(self, block):
        """
        This method should only be called after block passes every check.

        :param block:
        :return:
        """

        from collections import defaultdict
        requested_jobs = defaultdict(list)

        for tx in block['txs']:
            send_address = tools.tx_owner_address(tx)
            send_account = self.get_account(send_address)

            if tx['type'] == 'mint':
                send_account['amount'] += tools.block_reward(block['length'])
                #send_account['mined_blocks'].append(block['length'])
                self.update_account(send_address, send_account)
            elif tx['type'] == 'spend':
                recv_address = tx['to']
                recv_account = self.get_account(recv_address)

                send_account['amount'] -= tx['amount']
                send_account['count'] += 1
                send_account['tx_blocks'].append(block['length'])

                recv_account['amount'] += tx['amount']
                recv_account['tx_blocks'].append(block['length'])
                self.update_account(send_address, send_account)
                self.update_account(recv_address, recv_account)
            elif tx['type'] == 'reward':
                recv_address = tx['to']
                self.reward_job(tx['job_id'], recv_address, block['length'])

                recv_account = self.get_account(recv_address)
                recv_account['amount'] += tx['amount']
                recv_account['tx_blocks'].append(block['length'])
                self.update_account(recv_address, recv_account)
            elif tx['type'] == 'auth_reg':
                self.put_certificate(tx['certificate'])
            elif tx['type'] == 'job_dump':
                self.add_new_job(tx['job'], tx['auth'], block['length'])
            elif tx['type'] == 'job_request':
                requested_jobs[tx['job_id']].append((send_address, tx['amount']))

        """
         We go over the list of requested jobs in a deterministic way. Thus,
         every client will agree on how to evaluate multiple job bidding at the same block.
        """
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

    @sync
    def rollback_block(self, block):
        # TODO: Also rollback assignment and unassignment.
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
                owner_account['mined_blocks'].remove(block['length'])
                self.db.put(tx_owner_address, owner_account)
            elif tx['type'] == 'spend':
                owner_account['amount'] += tx['amount']
                owner_account['count'] -= 1
                owner_account['tx_blocks'].remove(block['length'])

                receiver_account = self.db.get(tx['to'])
                receiver_account['amount'] -= tx['amount']
                owner_account['tx_blocks'].remove(block['length'])

                self.db.put(tx_owner_address, owner_account)
                self.db.put(tx['to'], receiver_account)
            elif tx['type'] == 'auth_reg':
                self.delete_certificate(tx['certificate'])
            elif tx['type'] == 'job_dump':
                self.delete_job(tx['job']['id'])
            elif tx['type'] == 'job_request' or tx['type'] == 'reward':
                job = self.get_job(tx['request']['job_id'])
                for status in reversed(job['status_list']):
                    if status['block'] == block['length']:
                        job['status_list'].remove(status)
                    else:
                        break
                self.db.update_job(job)

    def update_account_with_txs(self, address, account, txs):
        """
        Not many use cases. Dont care
        """
        for tx in txs:
            owner = tools.tx_owner_address(tx)
            if tx['type'] == 'spend':
                if owner == address:
                    account['amount'] -= -tx['amount']
                    account['count'] += 1
                if tx['to'] == address:
                    account['amount'] += tx['amount']
        return account

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
                                               [tx] + self.blockchain.tx_pool())

        return account['amount'] >= 0

    @sync
    def put_certificate(self, cert_pem):
        if tools.check_certificate_chain(cert_pem):
            common_name = tools.get_commonname_from_certificate(cert_pem)
            self.db.put('cert_' + common_name, cert_pem)

    @sync
    def delete_certificate(self, cert_pem):
        common_name = tools.get_commonname_from_certificate(cert_pem)
        self.db.delete('cert_' + common_name, cert_pem)

    @sync
    def find_certificate_by_name(self, name):
        return self.db.get('cert_' + name)

    @sync
    def find_name_by_certificate(self, cert_pem):
        if tools.check_certificate_chain(cert_pem):
            common_name = tools.get_commonname_from_certificate(cert_pem)
            if self.db.exists('cert_' + common_name):
                return common_name
            else:
                return None
        else:
            return None

    @sync
    def get_available_jobs(self):
        job_list = self.db.get('job_list')
        result = {}
        for job_id in job_list:
            job = self.get_job(job_id)
            # Here we check last transaction made on the job.
            if job['status_list'][-1]['action'] == 'add' or job['status_list'][-1]['action'] == 'unassign':
                result[job_id] = self.db.get('job_'+job_id)
        return result

    @sync
    def get_assigned_jobs(self):
        job_list = self.db.get('job_list')
        result = {}
        for job_id in job_list:
            job = self.get_job(job_id)
            # Here we check last transaction made on the job.
            if job['status_list'][-1]['action'] == 'assign':
                result[job_id] = self.db.get('job_' + job_id)
        return result

    @sync
    def add_new_job(self, job, auth, block_number):
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

    @sync
    def assign_job(self, job_id, address, amount, block_number):
        job = self.db.get('job_' + job_id)
        if job['status_list'][-1]['action'] != 'add' and job['status_list'][-1]['action'] != 'unassign':
            return False
        if amount > job['max_amount'] or amount < job['min_amount']:
            return False
        account = self.get_account(address)
        if account['assigned_job'] != '':
            return False

        job['status_list'].append({
            'action': 'assign',
            'block': block_number,
            'address': address,
            'amount': amount
        })
        account['assigned_job'] = job_id
        self.db.put('job_' + job_id, job)
        self.db.put(address, account)
        return True

    @sync
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

    @sync
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

    @sync
    def get_job(self, job_id):
        return self.db.get('job_' + job_id)

    @sync
    def update_job(self, job):
        return self.db.put('job_' + job['id'], job)

    @sync
    def delete_job(self, job_id):
        job_list = self.db.get('job_list')
        job_list.remove(job_id)
        self.db.put('job_list', job_list)
        self.db.delete('job_' + job_id)
        return True
