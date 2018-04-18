import argparse
import json
import os
import signal
import time
import uuid

import docker
import requests
import sys
import yaml

from halocoin import tools, custom
from halocoin.db_client import ClientDB
from halocoin.halocoind import extract_configuration
from halocoin.model.wallet import Wallet
from halocoin.ntwrk import Response
from halocoin.service import Service, lockit

instance = None


class PowerService(Service):
    """
    This is the power service, designed for Coinami.
    Power service is similar to a miner. It solves problems and earns you coins.
    Power contacts with sub-authorities in the network to download problems that you are assigned.
    These problems are related to Bioinformatics, DNA mapping.
    After solving these problems, authority verifies the results and rewards you.
    """

    def __init__(self, config, workingdir):
        Service.__init__(self, "power")
        self.config = config
        self.workingdir = workingdir
        self.powerdb = ClientDB(self, 'power.db')
        self.jwtToken = None
        self.wallet = None
        self.status = "Not Started"
        self.description = "Closed"
        self.interrupted = False

    def on_register(self):
        if self.jwtToken is None or self.jwtToken == "":
            sys.stderr.write("Login credentials are invalid. Please login using halocoin CLI or GUI...\n")
            return False
        else:
            endpoint = "http://" + self.config['api']['host'] + ":" + str(self.config['api']['port']) + "/login/info"
            info = requests.get(endpoint, headers={"Authorization", "Bearer " + self.jwtToken})
            if info.status_code == 200 and info.json()['success']:
                self.wallet = Wallet.from_dict(info.json()['wallet'])
                return True
            else:
                return False

    def on_close(self):
        print('Power is turned off')
        Service.on_close(self)

    def stop(self):
        self.interrupted = True
        self.unregister()

    def get_job_status(self, job):
        job_name = job['auth'] + '_' + job['id']
        if self.powerdb.get('local_job_repo_' + job_name) is not None:
            job_directory = os.path.join(self.workingdir, 'jobs', job_name)
            result_file = os.path.join(job_directory, 'result.zip')
            job_file = os.path.join(job_directory, 'job.cfq.gz')
            result_exists = os.path.exists(result_file)
            job_exists = os.path.exists(job_file)
            entry = self.powerdb.get('local_job_repo_' + job_name)
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
        status = Service.get_status(self)
        status['title'] = self.status
        status['description'] = self.description

    @lockit('power')
    def set_status(self, status, description=""):
        self.status = status
        self.description = description

    def initiate_job(self, job):
        job_name = job['auth'] + '_' + job['id']
        print('Assigned {}'.format(job_name))
        self.powerdb.put('local_job_repo_' + job_name, {
            "status": "assigned",
        })

    def download_job(self, job):
        job_name = job['auth'] + '_' + job['id']
        print('Downloading {}'.format(job_name))
        job_directory = os.path.join(self.workingdir, 'jobs', job_name)
        if not os.path.exists(job_directory):
            os.makedirs(job_directory)
        job_file = os.path.join(job_directory, 'job.cfq.gz')
        secret_message = str(uuid.uuid4())
        payload = yaml.dump({
            "message": tools.det_hash(secret_message),
            "signature": tools.sign(tools.det_hash(secret_message), self.wallet.privkey),
            "pubkey": self.wallet.get_pubkey_str()
        })
        r = requests.get(job['download_url'], data={
            'payload': payload
        }, allow_redirects=False)

        if r.status_code != 302:
            time.sleep(1)
            print('Download was unsuccessful')
            return

        r2 = requests.get(r.headers['Location'], stream=True)
        downloaded = 0
        total_length = int(r.headers.get("Content-Length"))
        with open(job_file, 'wb') as f:
            for chunk in r2.iter_content(chunk_size=1024 * 1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    downloaded += 1024*1024
                    self.set_status("Downloading... {}/{}".format(
                        tools.readable_bytes(downloaded),
                        tools.readable_bytes(total_length)))
                if not self.get_state() == Service.RUNNING:
                    return False
        if os.path.exists(job_file):
            entry = self.powerdb.get('local_job_repo_' + job_name)
            entry['status'] = 'downloaded'
            self.powerdb.put('local_job_repo_' + job_name, entry)
            return True
        else:
            return False

    def execute_job(self, job):
        job_name = job['auth'] + '_' + job['id']
        print('Executing {}'.format(job_name))
        self.set_status("Executing...")
        import docker
        client = docker.from_env()
        job_directory = os.path.join(self.workingdir, 'jobs', job_name)
        job_directory = os.path.abspath(job_directory)
        result_file = os.path.join(job_directory, 'result.zip')

        config_file = os.path.join(job_directory, 'config.json')
        json.dump(self.config['coinami'], open(config_file, "w"))

        container = client.containers.run(job['image'], user=os.getuid(), volumes={
            job_directory: {'bind': '/input', 'mode': 'rw'}
        }, detach=True)
        while client.containers.get(container.id).status == 'running' or \
                        client.containers.get(container.id).status == 'created':
            self.set_status('Executing...', client.containers.get(container.id).logs().decode())
            if not self.get_state() == Service.RUNNING:
                client.containers.get(container.id).kill()
            time.sleep(1)
        if os.path.exists(result_file):
            self.set_status("Executed...")
            entry = self.powerdb.get('local_job_repo_' + job_name)
            entry['status'] = 'executed'
            self.powerdb.put('local_job_repo_' + job_name, entry)
            return True
        else:
            return False

    def upload_job(self, job):
        job_name = job['auth'] + '_' + job['id']
        print('Uploading {}'. format(job['id']))
        self.set_status("Uploading...")
        job_directory = os.path.join(self.workingdir, 'jobs', job_name)
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
            entry = self.powerdb.get('local_job_repo_' + job_name)
            self.set_status("Uploaded and Rewarded!")
            entry['status'] = 'uploaded'
            self.powerdb.put('local_job_repo_' + job_name, entry)

    def done_job(self, job):
        job_name = job['auth'] + '_' + job['id']
        job_directory = os.path.join(self.workingdir, 'jobs', job_name)
        if os.path.exists(job_directory):
            self.set_status("Cleaning job...")
            import shutil
            shutil.rmtree(job_directory)

        entry = self.powerdb.get('local_job_repo_' + job_name)
        entry['status'] = 'done'
        self.powerdb.put('local_job_repo_' + job_name, entry)

    def loop(self):
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

        if not PowerService.docker_status().getFlag():
            self.set_status("Docker Missing!", "Power service is not able to function due to a problem with docker!")
            time.sleep(1)
            return

        own_address = self.wallet.address
        own_account = self.statedb.get_account(own_address)
        assigned_job = own_account['assigned_job']

        if assigned_job['auth'] is None:
            self.set_status("No assignment!", "There is currently no assigment associated with this wallet")
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
    def docker_status():
        try:
            client = docker.from_env()
            if not client.ping():
                return Response(False, "Not Responding!")
        except Exception as e:
            return Response(False, "Closed")

        return Response(True, "Running!")

    @staticmethod
    def docker_images():
        running = PowerService.docker_status()
        if not running.getFlag():
            return Response(False, [])
        else:
            client = docker.from_env()
            return Response(True, [image.tags for image in client.images.list()])


def signal_handler(signal, frame):
    if instance is not None and not instance.interrupted:
        instance.stop()


def start(config, workingdir):
    global instance
    instance = PowerService(config, workingdir)
    if instance.register():
        print("Power Service is now operational")
        signal.signal(signal.SIGINT, signal_handler)
        instance.join()
        print("Shutting down")
    else:
        print("Couldn't start halocoin")


def run(argv):
    parser = argparse.ArgumentParser(description='Halocoin POWER module.')
    parser.add_argument('--version', action='version', version='%(prog)s ' + custom.power_version)
    parser.add_argument('--api-host', action="store", type=str, dest='api_host',
                        help='Hosting address of API')
    parser.add_argument('--api-port', action="store", type=int, dest='api_port',
                        help='Hosting port of API')
    parser.add_argument('--data-dir', action="store", type=str, dest='dir',
                        help='Data directory. Defaults to ' + tools.get_default_dir())
    args = parser.parse_args(argv[1:])

    config, workingdir = extract_configuration(args.dir)
    if args.api_host is not None and args.api_host != "":
        config['api']['host'] = args.api_host
    if args.api_port is not None and args.api_port != "":
        config['api']['port'] = args.api_port
    start(config, workingdir)
    return


def main():
    if sys.stdin.isatty():
        run(sys.argv)
    else:
        argv = sys.stdin.read().split(' ')
        run(argv)


if __name__ == '__main__':
    run(sys.argv)