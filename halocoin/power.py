import multiprocessing
import queue
import random
import time
import uuid
import docker
from multiprocessing import Process

import os

import pwd
import requests
import yaml

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
            result_file = os.path.join(job_directory, 'output', 'result.zip')
            job_file = os.path.join(job_directory, 'coinami.job.json')
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
        print('Assigned {}'.format(job_id))
        self.db.put('local_job_repo_' + job_id, {
            "status": "assigned",
        })

    @sync
    def download_job(self, job_id):
        print('Downloading {}'.format(job_id))
        # TODO: Authorities must have a job endpoint template.
        # TODO: Add signature verification while requesting jobs to download.
        # TODO: implementation
        job = self.account.get_job(job_id)
        endpoint = "http://139.179.21.17:5000/job_download/{}".format(job_id)
        job_directory = os.path.join(self.engine.working_dir, 'jobs', job_id)
        if not os.path.exists(job_directory):
            os.makedirs(job_directory)
        job_file = os.path.join(job_directory, 'job.zip')
        secret_message = str(uuid.uuid4())
        payload = yaml.dump({
            "message": tools.det_hash(secret_message),
            "signature": tools.sign(tools.det_hash(secret_message), self.wallet.privkey),
            "pubkey": self.wallet.get_pubkey_str()
        })
        r = requests.get(endpoint, stream=True, data={
            'payload': payload
        })
        with open(job_file, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
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

    @sync
    def execute_job(self, job_id):
        print('Executing {}'.format(job_id))
        import docker
        client = docker.from_env()
        job_directory = os.path.join(self.engine.working_dir, 'jobs', job_id)
        output_directory = os.path.join(job_directory, 'output')
        job_directory = os.path.abspath(job_directory)
        output_directory = os.path.abspath(output_directory)
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)
        result_file = os.path.join(output_directory, 'result.zip')
        client.containers.run(self.engine.config['coinami']['container'], user=os.getuid(), volumes={
            job_directory: {'bind': '/input', 'mode': 'rw'},
            output_directory: {'bind': '/output', 'mode': 'rw'}
        })
        if os.path.exists(result_file):
            entry = self.db.get('local_job_repo_' + job_id)
            entry['status'] = 'executed'
            self.db.put('local_job_repo_' + job_id, entry)
            return True
        else:
            return False

    @sync
    def upload_job(self, job_id):
        print('Uploading {}'. format(job_id))
        job = self.account.get_job(job_id)
        endpoint = "http://139.179.21.17:5000/job_upload/{}".format(job_id)
        result_directory = os.path.join(self.engine.working_dir, 'jobs', job_id, 'output')
        if not os.path.exists(result_directory):
            os.makedirs(result_directory)
        result_file = os.path.join(result_directory, 'result.zip')
        secret_message = str(uuid.uuid4())
        payload = yaml.dump({
            "message": tools.det_hash(secret_message),
            "signature": tools.sign(tools.det_hash(secret_message), self.wallet.privkey),
            "pubkey": self.wallet.get_pubkey_str()
        })
        files = {'file': open(result_file, 'rb')}
        values = {'payload': payload}

        r = requests.post(endpoint, files=files, data=values)
        if r.status_code == 200 and r.json()['success']:
            entry = self.db.get('local_job_repo_' + job_id)
            entry['status'] = 'uploaded'
            self.db.put('local_job_repo_' + job_id, entry)

    @sync
    def done_job(self, job_id):
        job = self.account.get_job(job_id)
        job_directory = os.path.join(self.engine.working_dir, 'jobs', job_id)
        if os.path.exists(job_directory):
            os.removedirs(job_directory)

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
        - Start container.
        - Upload the result.
        - Mark the job as done.
            - Remove the downloaded files
        - Repeat
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
