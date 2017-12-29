import multiprocessing
import queue
import random
import time
from multiprocessing import Process

import os

from halocoin import blockchain
from halocoin import custom
from halocoin import tools
from halocoin.service import Service, threaded, sync


class PowerService(Service):
    """
    This is the power service, designed and developed for Coinami.
    Power service is similar to a miner. It solves problems and earns you currency.
    Power contacts with sub-authorities in the network to dowload problems that you are assigned.
    These problems are related to Bioinformatics, DNA mapping.
    After solving these problems, authority verifies the results and rewards you.
    """
    def __init__(self, engine):
        Service.__init__(self, "power")
        self.engine = engine
        self.db = None
        self.blockchain = None
        self.account = None
        self.wallet = None

    def set_wallet(self, wallet):
        self.wallet = wallet

    def on_register(self):
        self.db = self.engine.db
        self.blockchain = self.engine.blockchain
        self.account = self.engine.account

        if self.wallet is not None and hasattr(self.wallet, 'privkey'):
            return True
        else:
            return False

    def on_close(self):
        self.wallet = None
        print('Power is turned off')

    @sync
    def get_job_status(self, job_id):
        if self.db.exists('local_job_repo_' + job_id):
            job_directory = os.path.join(self.engine.working_dir, 'jobs', job_id)
            result_file = os.path.join(job_directory, 'result.zip')
            job_file = os.path.join(job_directory, job_id + '.1.fastq')
            result_exists = os.path.exists(result_file)
            job_exists = os.path.exists(job_file)
            entry = self.db.get('local_job_repo_' + job_id)
            if entry['status'] == 'executed' or entry['status'] == 'downloaded':
                if result_exists:
                    return "executed"
                elif job_exists:
                    return "downloaded"
                else:
                    return "assigned"
            else:
                return entry['status']
        else:
            return "null"

    @sync
    def initiate_job(self, job_id):
        self.db.put('local_job_repo_' + job_id, {
            "status": "assigned",
        })

    @sync
    def download_job(self, job_id):
        # TODO: Authorities must have a job endpoint template.
        # TODO: Add signature verification while requesting jobs to download.
        # TODO: implementation
        """
        from pget.down import Downloader
        job = self.account.get_job(job_id)
        endpoint = "http://0.0.0.0:5000/jobs/{}".format(job_id)
        job_directory = os.path.join(self.engine.working_dir, 'jobs', job_id)
        job_file = os.path.join(job_directory, 'job.zip')
        pget = Downloader(endpoint, job_file, 1)  # URL, file name, chunk count
        pget.start_sync()
        if os.path.exists(job_file):
            import zipfile
            zip_ref = zipfile.ZipFile(job_file, 'r')
            zip_ref.extractall(job_directory)
            zip_ref.close()
            entry = self.db.get('local_job_repo_' + job_id)
            entry['status'] = 'downloaded'
            self.db.put('local_job_repo_' + job_id, entry)
            return True
        else:
            return False
        """
        entry = self.db.get('local_job_repo_' + job_id)
        entry['status'] = 'downloaded'
        self.db.put('local_job_repo_' + job_id, entry)

    @sync
    def execute_job(self, job_id):
        """rabix --quiet --basedir coinami.cw -- --reads_1 jobid.1.fastq --reads_2 jobid.2.fastq --reference /reference/human.fa --threads 4 --output_loc result.zip"""
        import subprocess
        job_directory = os.path.join(self.engine.working_dir, 'jobs', job_id)
        result_file = os.path.join(job_directory, 'result.zip')
        result = subprocess.run([self.engine.config['coinami']['docker'],
                                 '--quiet', '--basedir',
                                 os.path.dirname(self.engine.config['coinami']['workflow_path']),
                                 self.engine.config['coinami']['workflow_path'],
                                 '--',
                                 '--reads_1', os.path.join(job_directory, job_id + '.1.fastq'),
                                 '--reads_2', os.path.join(job_directory, job_id + '.2.fastq'),
                                 '--reference', self.engine.config['coinami']['reference_path'],
                                 '--threads', '4',
                                 '--output_loc', 'result.zip'])
        if result.check_returncode() == 0 and os.path.exists(result_file):
            entry = self.db.get('local_job_repo_' + job_id)
            entry['status'] = 'executed'
            self.db.put('local_job_repo_' + job_id, entry)
            return True
        else:
            return False

    @sync
    def upload_job(self, job_id):
        # TODO: Implementation
        entry = self.db.get('local_job_repo_' + job_id)
        entry['status'] = 'uploaded'
        self.db.put('local_job_repo_' + job_id, entry)

    @sync
    def done_job(self, job_id):
        # TODO: Implementation
        entry = self.db.get('local_job_repo_' + job_id)
        entry['status'] = 'done'
        self.db.put('local_job_repo_' + job_id, entry)

    @threaded
    def worker(self):
        """
        - Find our assigned task.
        - Query Job repository for the task.
        - If job is not downloaded:
            - Download the job.
        - Start rabix process.
        - Upload the result.
        - Mark the job as done.
        - Return to beginning.
        """
        if self.blockchain.get_chain_state() == blockchain.BlockchainService.SYNCING:
            time.sleep(0.1)
            return

        own_address = self.wallet.address
        own_account = self.account.get_account(own_address)
        assigned_job = own_account['assigned_job']
        if assigned_job == '':
            time.sleep(5)
            return

        job_status = self.get_job_status(assigned_job)
        if job_status == 'null':
            self.initiate_job(assigned_job)
        elif job_status == 'assigned':
            self.download_job(assigned_job)
        elif job_status == 'downloaded':
            self.execute_job(assigned_job)
        elif job_status == 'executed':
            self.upload_job(assigned_job)
        elif job_status == 'uploaded':
            self.done_job(assigned_job)
        time.sleep(1)
