import json
import os
import time
import uuid

import docker
import requests
import yaml
from docker.errors import ImageNotFound

from halocoin import api
from halocoin import tools
from halocoin.ntwrk import Response
from halocoin.service import Service, threaded, lockit


class PowerService(Service):
    """
    This is the power service, designed for Coinami.
    Power service is similar to a miner. It solves problems and earns you coins.
    Power contacts with sub-authorities in the network to download problems that you are assigned.
    These problems are related to Bioinformatics, DNA mapping.
    After solving these problems, authority verifies the results and rewards you.
    """

    def __init__(self, engine):
        Service.__init__(self, "power")
        self.engine = engine
        self.blockchain = None
        self.clientdb = None
        self.statedb = None
        self.wallet = None
        self.status = "Loading"
        self.description = ""

    def set_wallet(self, wallet):
        self.wallet = wallet

    def on_register(self):
        self.clientdb = self.engine.clientdb
        self.blockchain = self.engine.blockchain
        self.statedb = self.engine.statedb

        if self.wallet is not None and hasattr(self.wallet, 'privkey'):
            return True
        else:
            return False

    def on_close(self):
        self.wallet = None
        print('Power is turned off')

    def get_job_status(self, job):
        job_name = job['auth'] + '_' + job['id']
        if self.clientdb.get('local_job_repo_' + job_name) is not None:
            job_directory = os.path.join(self.engine.working_dir, 'jobs', job_name)
            result_file = os.path.join(job_directory, 'result.zip')
            job_file = os.path.join(job_directory, 'job.cfq.gz')
            result_exists = os.path.exists(result_file)
            job_exists = os.path.exists(job_file)
            entry = self.clientdb.get('local_job_repo_' + job_name)
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

    @lockit('power')
    def get_status(self):
        return self.status

    @lockit('power')
    def set_status(self, status, description=""):
        self.status = status
        self.description = description
        api.power_status()

    def initiate_job(self, job):
        job_name = job['auth'] + '_' + job['id']
        print('Assigned {}'.format(job_name))
        self.clientdb.put('local_job_repo_' + job_name, {
            "status": "assigned",
        })

    def download_job(self, job):
        job_name = job['auth'] + '_' + job['id']
        print('Downloading {}'.format(job_name))
        job_directory = os.path.join(self.engine.working_dir, 'jobs', job_name)
        if not os.path.exists(job_directory):
            os.makedirs(job_directory)
        job_file = os.path.join(job_directory, 'job.cfq.gz')
        secret_message = str(uuid.uuid4())
        payload = yaml.dump({
            "message": tools.det_hash(secret_message),
            "signature": tools.sign(tools.det_hash(secret_message), self.wallet.privkey),
            "pubkey": self.wallet.get_pubkey_str()
        })
        r = requests.get(job['download_url'], stream=True, data={
            'payload': payload
        })
        if r.status_code != 200:
            time.sleep(1)
            return False
        downloaded = 0
        total_length = int(r.headers.get("Content-Length"))
        with open(job_file, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    downloaded += 1024*1024
                    self.set_status("Downloading... {}/{}".format(
                        tools.readable_bytes(downloaded),
                        tools.readable_bytes(total_length)))
        if os.path.exists(job_file):
            entry = self.clientdb.get('local_job_repo_' + job_name)
            entry['status'] = 'downloaded'
            self.clientdb.put('local_job_repo_' + job_name, entry)
            return True
        else:
            return False

    def execute_job(self, job):
        job_name = job['auth'] + '_' + job['id']
        print('Executing {}'.format(job_name))
        self.set_status("Executing...")
        import docker
        client = docker.from_env()
        job_directory = os.path.join(self.engine.working_dir, 'jobs', job_name)
        job_directory = os.path.abspath(job_directory)
        result_file = os.path.join(job_directory, 'result.zip')

        config_file = os.path.join(job_directory, 'config.json')
        json.dump(self.engine.config['coinami'], open(config_file, "w"))

        container = client.containers.run(job['image'], user=os.getuid(), volumes={
            job_directory: {'bind': '/input', 'mode': 'rw'}
        }, detach=True)
        while client.containers.get(container.id).status == 'running' or \
                        client.containers.get(container.id).status == 'created':
            self.set_status('Executing...', client.containers.get(container.id).logs().decode())
            if not self.threaded_running():
                client.containers.get(container.id).kill()
            time.sleep(1)
        if os.path.exists(result_file):
            self.set_status("Executed...")
            entry = self.clientdb.get('local_job_repo_' + job_name)
            entry['status'] = 'executed'
            self.clientdb.put('local_job_repo_' + job_name, entry)
            return True
        else:
            return False

    def upload_job(self, job):
        job_name = job['auth'] + '_' + job['id']
        print('Uploading {}'. format(job['id']))
        self.set_status("Uploading...")
        job_directory = os.path.join(self.engine.working_dir, 'jobs', job_name)
        result_file = os.path.join(job_directory, 'result.zip')
        secret_message = str(uuid.uuid4())
        payload = yaml.dump({
            "message": tools.det_hash(secret_message),
            "signature": tools.sign(tools.det_hash(secret_message), self.wallet.privkey),
            "pubkey": self.wallet.get_pubkey_str()
        })
        files = {'file': open(result_file, 'rb')}
        values = {'payload': payload}

        r = requests.post(job['upload_url'], files=files, data=values)
        if r.status_code == 200 and r.json()['success']:
            entry = self.clientdb.get('local_job_repo_' + job_name)
            self.set_status("Uploaded and Rewarded!")
            entry['status'] = 'uploaded'
            self.clientdb.put('local_job_repo_' + job_name, entry)

    def done_job(self, job):
        job_name = job['auth'] + '_' + job['id']
        job_directory = os.path.join(self.engine.working_dir, 'jobs', job_name)
        if os.path.exists(job_directory):
            self.set_status("Cleaning job...")
            import shutil
            shutil.rmtree(job_directory)

        entry = self.clientdb.get('local_job_repo_' + job_name)
        entry['status'] = 'done'
        self.clientdb.put('local_job_repo_' + job_name, entry)

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

        own_address = self.wallet.address
        own_account = self.statedb.get_account(own_address)
        assigned_job = own_account['assigned_job']
        if assigned_job['auth'] is None:
            self.set_status("No assignment!")
            time.sleep(1)
            return

        assigned_job = self.statedb.get_job(assigned_job['auth'], assigned_job['job_id'])
        job_status = self.get_job_status(assigned_job)
        if job_status == 'null':
            self.set_status("Job assigned! Initializing...")
            self.initiate_job(assigned_job)
        elif job_status == 'assigned':
            self.set_status("Downloading...")
            self.download_job(assigned_job)
        elif job_status == 'downloaded':
            self.execute_job(assigned_job)
        elif job_status == 'executed':
            self.upload_job(assigned_job)
        elif job_status == 'uploaded':
            self.done_job(assigned_job)
        elif job_status == 'done':
            self.set_status("Done!")

        time.sleep(0.1)

    @staticmethod
    def system_status():
        try:
            client = docker.from_env()
            if not client.ping():
                return Response(False, "Docker daemon is not responding")
        except:
            return Response(False, "An expection occurred")

        return Response(True, "Ready to go!")
