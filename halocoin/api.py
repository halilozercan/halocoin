import copy
import json
import os
import tempfile
import threading

import psutil as psutil
# WARNING! Do not remove below import line. PyInstaller depends on it
from engineio import async_threading
from flask import Flask, request, Response, send_file
from flask_socketio import SocketIO

from halocoin import tools, engine, custom
from halocoin.power import PowerService
from halocoin.service import Service

async_threading  # PyCharm automatically removes unused imports. This prevents it


class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (bytes, bytearray)):
            return obj.hex()
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


app = Flask(__name__)
socketio = SocketIO(app, async_mode='threading')
listen_thread = None


def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()


def run():
    def thread_target():
        socketio.run(app, host=host, port=engine.instance.config['port']['api'])

    global listen_thread
    host = os.environ.get('HALOCOIN_API_HOST', "localhost")
    listen_thread = threading.Thread(target=thread_target, daemon=True)
    listen_thread.start()
    print("Started API on {}:{}".format(host, engine.instance.config['port']['api']))


@socketio.on('connect')
def connect():
    print("%s connected" % request.sid)
    return ""


@app.route('/')
def hello():
    return "~Healthy and alive~"


@app.route("/upload_wallet", methods=['GET', 'POST'])
def upload_wallet():
    wallet_name = request.values.get('wallet_name', None)
    wallet_file = request.files['wallet_file']
    wallet_content = wallet_file.stream.read()
    success = engine.instance.clientdb.upload_wallet(wallet_name, wallet_content)
    return generate_json_response({
        "success": success,
        "wallet_name": wallet_name
    })


@app.route('/download_wallet', methods=['GET', 'POST'])
def download_wallet():
    wallet_name = request.values.get('wallet_name', None)
    if wallet_name is None:
        return generate_json_response({
            "success": False,
            "error": "Give a valid wallet name"
        })
    wallet_content = engine.instance.clientdb.get_wallet(wallet_name)
    if wallet_content is None:
        return generate_json_response({
            "success": False,
            "error": "Wallet doesn't exist"
        })
    f = tempfile.NamedTemporaryFile()
    f.write(wallet_content)
    f.seek(0)
    return send_file(f, as_attachment=True, attachment_filename=wallet_name)


@app.route('/info_wallet', methods=['GET', 'POST'])
def info_wallet():
    from halocoin.model.wallet import Wallet
    wallet_name = request.values.get('wallet_name', None)
    password = request.values.get('password', None)
    if wallet_name is None:
        default_wallet = engine.instance.clientdb.get_default_wallet()
        if default_wallet is not None:
            wallet_name = default_wallet['wallet_name']
            password = default_wallet['password']

    encrypted_wallet_content = engine.instance.clientdb.get_wallet(wallet_name)
    if encrypted_wallet_content is not None:
        try:
            wallet = Wallet.from_string(tools.decrypt(password, encrypted_wallet_content))
            account = engine.instance.statedb.get_account(wallet.address)
            return generate_json_response({
                "name": wallet.name,
                "pubkey": wallet.get_pubkey_str(),
                "privkey": wallet.get_privkey_str(),
                "address": wallet.address,
                "balance": account['amount'],
                "deposit": account['stake'],
                "assigned_job": account['assigned_job'],
            })
        except:
            return generate_json_response("Password incorrect")
    else:
        return generate_json_response("Error occurred")


@app.route('/remove_wallet', methods=['GET', 'POST'])
def remove_wallet():
    from halocoin.model.wallet import Wallet
    wallet_name = request.values.get('wallet_name', None)
    password = request.values.get('password', None)
    default_wallet = engine.instance.clientdb.get_default_wallet()
    if default_wallet is not None and default_wallet['wallet_name'] == wallet_name:
        return generate_json_response({
            'success': False,
            'error': 'Cannot remove default wallet. First remove its default state!'
        })

    encrypted_wallet_content = engine.instance.clientdb.get_wallet(wallet_name)
    if encrypted_wallet_content is not None:
        try:
            Wallet.from_string(tools.decrypt(password, encrypted_wallet_content))
            engine.instance.clientdb.remove_wallet(wallet_name)
            return generate_json_response({
                "success": True,
                "message": "Successfully removed wallet"
            })
        except:
            return generate_json_response({
                "success": False,
                "error": "Password incorrect"
            })
    else:
        return generate_json_response({
            "success": False,
            "error": "Unidentified error occurred!"
        })


@app.route('/new_wallet', methods=['GET', 'POST'])
def new_wallet():
    from halocoin.model.wallet import Wallet
    wallet_name = request.values.get('wallet_name', None)
    pw = request.values.get('password', None)
    set_default = request.values.get('set_default', None)
    wallet = Wallet(wallet_name)
    success = engine.instance.clientdb.new_wallet(pw, wallet)
    if set_default:
        engine.instance.clientdb.set_default_wallet(wallet_name, pw)

    return generate_json_response({
        "name": wallet_name,
        "success": success
    })


@app.route('/set_default_wallet', methods=['GET', 'POST'])
def set_default_wallet():
    wallet_name = request.values.get('wallet_name', None)
    password = request.values.get('password', None)
    return generate_json_response({
        "success": engine.instance.clientdb.set_default_wallet(wallet_name, password)
    })


@app.route('/remove_default_wallet', methods=['GET', 'POST'])
def remove_default_wallet():
    return generate_json_response({
        "success": engine.instance.clientdb.delete_default_wallet()
    })


@app.route('/wallets', methods=['GET', 'POST'])
def wallets():
    default_wallet = engine.instance.clientdb.get_default_wallet()
    if default_wallet is None:
        wallet_name = ''
    else:
        wallet_name = default_wallet['wallet_name']
    return generate_json_response({
        'wallets': engine.instance.clientdb.get_wallets(),
        'default_wallet': wallet_name
    })


@app.route('/peers', methods=['GET', 'POST'])
def peers():
    return generate_json_response(engine.instance.clientdb.get_peers())


@app.route('/node_id', methods=['GET', 'POST'])
def node_id():
    return generate_json_response(engine.instance.db.get('node_id'))

"""
@app.route('/history', methods=['GET', 'POST'])
def history():
    from halocoin.model.wallet import Wallet
    address = request.values.get('address', None)
    if address is None:
        default_wallet = engine.instance.clientdb.get_default_wallet()
        if default_wallet is not None:
            wallet_name = default_wallet['wallet_name']
            password = default_wallet['password']
            encrypted_wallet_content = engine.instance.clientdb.get_wallet(wallet_name)
            wallet = Wallet.from_string(tools.decrypt(password, encrypted_wallet_content))
            address = wallet.address
    account = engine.instance.statedb.get_account(wallet.address)
    txs = {
        "send": [],
        "recv": []
    }
    for block_index in reversed(list(account['tx_blocks'])):
        block = engine.instance.blockchain.get_block(block_index)
        for tx in block['txs']:
            if tx['type'] == 'mint':
                continue
            tx['block'] = block_index
            owner = tools.tx_owner_address(tx)
            if owner == address:
                txs['send'].append(tx)
            elif tx['type'] == 'spend' and tx['to'] == address:
                txs['recv'].append(tx)
            elif tx['type'] == 'reward' and tx['to'] == address:
                txs['recv'].append(tx)
    return generate_json_response(txs)
"""


@app.route('/jobs')
def jobs():
    type = request.values.get('type', 'available')
    page = int(request.values.get('page', 1))
    rows_per_page = int(request.values.get('rows_per_page', 5))
    result = {'total': 0, 'page': page, 'rows_per_page': rows_per_page, 'jobs': []}
    if type == 'available':
        jobs = list(engine.instance.statedb.get_available_jobs().values())
    elif type == 'assigned':
        jobs = list(engine.instance.statedb.get_assigned_jobs().values())

    result['total'] = len(jobs)
    result['jobs'] = jobs[((page - 1) * rows_per_page):(page * rows_per_page)]

    return generate_json_response(result)


@app.route('/send', methods=['GET', 'POST'])
def send():
    from halocoin.model.wallet import Wallet
    amount = int(request.values.get('amount', 0))
    address = request.values.get('address', None)
    message = request.values.get('message', '')
    wallet_name = request.values.get('wallet_name', None)
    password = request.values.get('password', None)

    if wallet_name is None:
        default_wallet = engine.instance.clientdb.get_default_wallet()
        if default_wallet is not None:
            wallet_name = default_wallet['wallet_name']

    response = {"success": False}
    if amount <= 0:
        response['error'] = "Amount cannot be lower than or equal to 0"
        return generate_json_response(response)
    elif address is None:
        response['error'] = "You need to specify a receiving address for transaction"
        return generate_json_response(response)
    elif wallet_name is None:
        response['error'] = "Wallet name is not given and there is no default wallet"
        return generate_json_response(response)
    elif password is None:
        response['error'] = "Password missing!"
        return generate_json_response(response)

    tx = {'type': 'spend', 'amount': int(amount),
          'to': address, 'message': message, 'version': custom.version}

    encrypted_wallet_content = engine.instance.clientdb.get_wallet(wallet_name)
    if encrypted_wallet_content is not None:
        try:
            wallet = Wallet.from_string(tools.decrypt(password, encrypted_wallet_content))
        except:
            response['error'] = "Wallet password incorrect"
            return generate_json_response(response)
    else:
        response['error'] = "Error occurred"
        return generate_json_response(response)

    if 'count' not in tx:
        try:
            tx['count'] = engine.instance.statedb.known_tx_count(wallet.address, count_pool=True)
        except:
            tx['count'] = 0
    if 'pubkeys' not in tx:
        tx['pubkeys'] = [wallet.get_pubkey_str()]  # We use pubkey as string
    if 'signatures' not in tx:
        tx['signatures'] = [tools.sign(tools.det_hash(tx), wallet.privkey)]
    engine.instance.blockchain.tx_queue.put(tx)
    response["success"] = True
    response["message"] = "Your transaction is successfully added to the queue"
    response["tx"] = tx
    return generate_json_response(response)


@app.route('/deposit', methods=['GET', 'POST'])
def deposit():
    from halocoin.model.wallet import Wallet
    amount = int(request.values.get('amount', 0))  # Bidding amount
    auth = request.values.get('auth', None)
    wallet_name = request.values.get('wallet_name', None)
    password = request.values.get('password', None)
    force = request.values.get('force', None)

    status = PowerService.system_status()
    if not status.getFlag() and force is None:
        return generate_json_response({
            'error': 'Power service is unavailable',
            'message': 'Power service cannot seem to function right now. '
                       'This probably means there is a problem with Docker connection or Docker is not installed.'
        })

    if wallet_name is None:
        default_wallet = engine.instance.clientdb.get_default_wallet()
        if default_wallet is not None:
            wallet_name = default_wallet['wallet_name']

    response = {"success": False}
    if amount <= 0:
        response['error'] = "Amount cannot be lower than or equal to 0"
        return generate_json_response(response)
    elif auth is None:
        response['error'] = "Auth is not given"
        return generate_json_response(response)
    elif wallet_name is None:
        response['error'] = "Wallet name is not given and there is no default wallet"
        return generate_json_response(response)
    elif password is None:
        response['error'] = "Password missing!"
        return generate_json_response(response)

    tx = {'type': 'deposit', 'amount': int(amount), 'version': custom.version, 'auth': auth}

    encrypted_wallet_content = engine.instance.clientdb.get_wallet(wallet_name)
    if encrypted_wallet_content is not None:
        try:
            wallet = Wallet.from_string(tools.decrypt(password, encrypted_wallet_content))
        except:
            response['error'] = "Wallet password incorrect"
            return generate_json_response(response)
    else:
        response['error'] = "Error occurred"
        return generate_json_response(response)

    if 'count' not in tx:
        try:
            tx['count'] = engine.instance.statedb.known_tx_count(wallet.address, count_pool=True)
        except:
            tx['count'] = 0
    if 'pubkeys' not in tx:
        tx['pubkeys'] = [wallet.get_pubkey_str()]  # We use pubkey as string
    if 'signatures' not in tx:
        tx['signatures'] = [tools.sign(tools.det_hash(tx), wallet.privkey)]
    engine.instance.blockchain.tx_queue.put(tx)
    response["success"] = True
    response["message"] = "Your transaction is successfully added to the queue"
    response["tx"] = tx
    return generate_json_response(response)


@app.route('/withdraw', methods=['GET', 'POST'])
def withdraw():
    from halocoin.model.wallet import Wallet
    amount = int(request.values.get('amount', 0))  # Bidding amount
    auth = request.values.get('auth', None)
    wallet_name = request.values.get('wallet_name', None)
    password = request.values.get('password', None)

    if wallet_name is None:
        default_wallet = engine.instance.clientdb.get_default_wallet()
        if default_wallet is not None:
            wallet_name = default_wallet['wallet_name']

    response = {"success": False}
    if amount <= 0:
        response['error'] = "Amount cannot be lower than or equal to 0"
        return generate_json_response(response)
    elif auth is None:
        response['error'] = "Auth is not given"
        return generate_json_response(response)
    elif wallet_name is None:
        response['error'] = "Wallet name is not given and there is no default wallet"
        return generate_json_response(response)
    elif password is None:
        response['error'] = "Password missing!"
        return generate_json_response(response)

    tx = {'type': 'withdraw', 'amount': int(amount), 'version': custom.version, 'auth': auth}

    encrypted_wallet_content = engine.instance.clientdb.get_wallet(wallet_name)
    if encrypted_wallet_content is not None:
        try:
            wallet = Wallet.from_string(tools.decrypt(password, encrypted_wallet_content))
        except:
            response['error'] = "Wallet password incorrect"
            return generate_json_response(response)
    else:
        response['error'] = "Error occurred"
        return generate_json_response(response)

    if 'count' not in tx:
        try:
            tx['count'] = engine.instance.statedb.known_tx_count(wallet.address, count_pool=True)
        except:
            tx['count'] = 0
    if 'pubkeys' not in tx:
        tx['pubkeys'] = [wallet.get_pubkey_str()]  # We use pubkey as string
    if 'signatures' not in tx:
        tx['signatures'] = [tools.sign(tools.det_hash(tx), wallet.privkey)]
    engine.instance.blockchain.tx_queue.put(tx)
    response["success"] = True
    response["message"] = "Your transaction is successfully added to the queue"
    response["tx"] = tx
    return generate_json_response(response)


@app.route('/reward', methods=['GET', 'POST'])
def reward():
    from ecdsa import SigningKey
    job_id = request.values.get('job_id', None)
    address = request.values.get('address', None)
    certificate = request.values.get('certificate', None)
    privkey = request.values.get('privkey', None)

    response = {"success": False}
    if job_id is None:
        response['error'] = "You need to specify a job id for the reward"
        return generate_json_response(response)
    elif address is None:
        response['error'] = "You need to specify a receiving address for the reward"
        return generate_json_response(response)
    elif privkey is None:
        response['error'] = "Reward transactions need to be signed by private key belonging to certificate"
        return generate_json_response(response)
    elif certificate is None:
        response['error'] = "To reward, you must specify a common name or certificate that is granted by root"
        return generate_json_response(response)

    tx = {'type': 'reward', 'job_id': job_id, 'to': address, 'version': custom.version}

    privkey = SigningKey.from_pem(privkey)
    common_name = tools.get_commonname_from_certificate(certificate)
    tx['auth'] = common_name

    tx['pubkeys'] = [privkey.get_verifying_key().to_string()]  # We use pubkey as string
    tx['signatures'] = [tools.sign(tools.det_hash(tx), privkey)]
    engine.instance.blockchain.tx_queue.put(tx)
    response["success"] = True
    response["message"] = "Your transaction is successfully added to the queue"
    response["tx"] = tx
    return generate_json_response(response)


@app.route('/job_dump', methods=['GET', 'POST'])
def job_dump():
    from ecdsa import SigningKey
    job = {
        'id': request.values.get('job_id', None),
        'timestamp': request.values.get('job_timestamp', None),
        'amount': int(request.values.get('amount', 0)),
        'download_url': request.values.get('download_url', None),
        'upload_url': request.values.get('upload_url', None),
        'hashsum': request.values.get('hashsum', None),
        'image': request.values.get('image', None),
    }
    certificate = request.values.get('certificate', None)
    privkey = request.values.get('privkey', None)

    response = {"success": False}
    if job['id'] is None:
        response['error'] = "Job id missing"
        return generate_json_response(response)
    elif privkey is None:
        response['error'] = "Job dumps need to be signed by private key belonging to certificate"
        return generate_json_response(response)
    elif certificate is None:
        response['error'] = "To give jobs, you must specify a certificate that is granted by root"
        return generate_json_response(response)
    elif job['amount'] == 0:
        response['error'] = "Reward amount is missing"
        return generate_json_response(response)

    tx = {'type': 'job_dump', 'job': job, 'version': custom.version}

    privkey = SigningKey.from_pem(privkey)
    common_name = tools.get_commonname_from_certificate(certificate)
    tx['auth'] = common_name

    tx['pubkeys'] = [privkey.get_verifying_key().to_string()]  # We use pubkey as string
    tx['signatures'] = [tools.sign(tools.det_hash(tx), privkey)]
    engine.instance.blockchain.tx_queue.put(tx)
    response["success"] = True
    response["message"] = "Your transaction is successfully added to the queue"
    response["tx"] = tx
    return generate_json_response(response)


@app.route('/auth_reg', methods=['GET', 'POST'])
def auth_reg():
    from ecdsa import SigningKey
    cert_pem = request.values.get('cert_pem', None)
    priv_key_pem = request.values.get('privkey_pem', None)
    host = request.values.get('host', None)
    supply = int(request.values.get('supply', 0))

    response = {"success": False}
    if priv_key_pem is None:
        response['error'] = "Auth registration transactions need to be signed by private key belonging to certificate"
        return generate_json_response(response)
    elif cert_pem is None:
        response['error'] = "Certificate is required for registration"
        return generate_json_response(response)
    elif host is None:
        response['error'] = "Authorities must provide a hosting address"
        return generate_json_response(response)
    elif supply == 0:
        response['error'] = "Authorities must register with an initial supply"
        return generate_json_response(response)

    tx = {'type': 'auth_reg', 'version': custom.version, 'host': host, 'supply': supply}

    privkey = SigningKey.from_pem(priv_key_pem)

    common_name = tools.get_commonname_from_certificate(cert_pem)
    if engine.instance.statedb.get_auth(common_name) is not None:
        response['error'] = "An authority with common name {} is already registered.".format(common_name)
        return generate_json_response(response)
    if not tools.check_certificate_chain(cert_pem):
        response['error'] = "Given certificate is not granted by root"
        return generate_json_response(response)

    tx['certificate'] = cert_pem

    tx['pubkeys'] = [privkey.get_verifying_key().to_string()]  # We use pubkey as string
    tx['signatures'] = [tools.sign(tools.det_hash(tx), privkey)]
    engine.instance.blockchain.tx_queue.put(tx)
    response["success"] = True
    response["message"] = "Your transaction is successfully added to the queue"
    response["tx"] = tx
    return generate_json_response(response)


@app.route('/blockcount', methods=['GET', 'POST'])
def blockcount():
    result = dict(length=engine.instance.db.get('length'),
                  known_length=engine.instance.clientdb.get('known_length'))
    result_text = json.dumps(result)
    return Response(response=result_text, headers={"Content-Type": "application/json"})


@app.route('/mempool', methods=['GET', 'POST'])
def mempool():
    purge = request.values.get('purge', None)
    if purge is not None:
        engine.instance.blockchain.tx_pool_pop_all()
    pool = copy.deepcopy(engine.instance.blockchain.tx_pool())
    for i, tx in enumerate(pool):
        if tx['type'] == 'spend':
            pool[i]['from'] = tools.tx_owner_address(tx)
        elif tx['type'] == 'reward':
            pool[i]['from'] = tools.reward_owner_name(tx)
        elif tx['type'] == 'job_request':
            pool[i]['from'] = tools.tx_owner_address(tx)
            pool[i]['to'] = tx['job_id']
        elif tx['type'] == 'job_dump':
            pool[i]['from'] = tools.reward_owner_name(tx)
            pool[i]['to'] = tx['job']['id']
            pool[i]['amount'] = 0
        elif tx['type'] == 'auth_reg':
            pool[i]['from'] = tools.reward_owner_name(tx)
            pool[i]['to'] = 'Network'
            pool[i]['amount'] = 0

    return generate_json_response(pool)


@app.route('/blocks', methods=['GET', 'POST'])
def blocks():
    start = int(request.values.get('start', '-1'))
    end = int(request.values.get('end', '-1'))
    length = engine.instance.db.get('length')
    if start == -1 and end == -1:
        end = length
        start = max(end - 20, 0)
    elif start == -1:
        start = max(end - 20, 0)
    elif end == -1:
        end = min(length, start + 20)

    result = {
        "start": start,
        "end": end,
        "blocks": []
    }
    for i in range(start, end + 1):
        block = engine.instance.blockchain.get_block(i)
        if block is None:
            break
        mint_tx = list(filter(lambda t: t['type'] == 'mint', block['txs']))[0]
        block['miner'] = tools.tx_owner_address(mint_tx)
        result["blocks"].append(block)
    result["blocks"] = list(reversed(result["blocks"]))
    return generate_json_response(result)


@app.route('/difficulty', methods=['GET', 'POST'])
def difficulty():
    diff = engine.instance.blockchain.target(engine.instance.db.get('length'))
    return generate_json_response({"difficulty": diff})


@app.route('/balance', methods=['GET', 'POST'])
def balance():
    from halocoin.model.wallet import Wallet
    address = request.values.get('address', None)
    if address is None:
        default_wallet = engine.instance.clientdb.get_default_wallet()
        if default_wallet is not None:
            wallet_name = default_wallet['wallet_name']
            password = default_wallet['password']
            encrypted_wallet_content = engine.instance.clientdb.get_wallet(wallet_name)
            wallet = Wallet.from_string(tools.decrypt(password, encrypted_wallet_content))
            address = wallet.address

    account = engine.instance.statedb.get_account(address)
    return generate_json_response({'balance': account['amount']})


@app.route('/stop', methods=['GET', 'POST'])
def stop():
    engine.instance.db.put('stop', True)
    shutdown_server()
    print('Closed API')
    engine.instance.stop()
    return generate_json_response('Shutting down')


@app.route('/start_miner', methods=['GET', 'POST'])
def start_miner():
    from halocoin.model.wallet import Wallet
    wallet_name = request.values.get('wallet_name', None)
    password = request.values.get('password', None)

    if wallet_name is None:
        default_wallet = engine.instance.clientdb.get_default_wallet()
        if default_wallet is not None:
            wallet_name = default_wallet['wallet_name']
            password = default_wallet['password']

    encrypted_wallet_content = engine.instance.clientdb.get_wallet(wallet_name)
    if encrypted_wallet_content is not None:
        try:
            wallet = Wallet.from_string(tools.decrypt(password, encrypted_wallet_content))
        except:
            return generate_json_response("Wallet password incorrect")
    else:
        return generate_json_response("Error occurred")

    if engine.instance.miner.get_state() == Service.RUNNING:
        return generate_json_response('Miner is already running.')
    elif wallet is None:
        return generate_json_response('Given wallet is not valid.')
    else:
        engine.instance.miner.set_wallet(wallet)
        engine.instance.miner.register()
        return generate_json_response('Running miner')


@app.route('/stop_miner', methods=['GET', 'POST'])
def stop_miner():
    if engine.instance.miner.get_state() == Service.RUNNING:
        engine.instance.miner.unregister()
        return generate_json_response('Closed miner')
    else:
        return generate_json_response('Miner is not running.')


@app.route('/status_miner', methods=['GET', 'POST'])
def status_miner():
    status = {
        'running': engine.instance.miner.get_state() == Service.RUNNING
    }
    if status['running']:
        status['cpu'] = psutil.cpu_percent()
    return generate_json_response(status)


@app.route('/power_available')
def power_available():
    status = PowerService.system_status()
    return generate_json_response({
        "success": status.getFlag(),
        "message": status.getData()
    })


@app.route('/start_power', methods=['GET', 'POST'])
def start_power():
    from halocoin.model.wallet import Wallet
    wallet_name = request.values.get('wallet_name', None)
    password = request.values.get('password', None)

    if wallet_name is None:
        default_wallet = engine.instance.clientdb.get_default_wallet()
        if default_wallet is not None:
            wallet_name = default_wallet['wallet_name']
            password = default_wallet['password']

    encrypted_wallet_content = engine.instance.clientdb.get_wallet(wallet_name)
    if encrypted_wallet_content is not None:
        try:
            wallet = Wallet.from_string(tools.decrypt(password, encrypted_wallet_content))
        except:
            return generate_json_response("Wallet password incorrect")
    else:
        return generate_json_response("Error occurred")

    if engine.instance.power.get_state() == Service.RUNNING:
        return generate_json_response('Power is already running.')
    elif wallet is None:
        return generate_json_response('Given wallet is not valid.')
    else:
        engine.instance.power.set_wallet(wallet)
        engine.instance.power.register()
        return generate_json_response('Running power')


@app.route('/stop_power', methods=['GET', 'POST'])
def stop_power():
    if engine.instance.power.get_state() == Service.RUNNING:
        engine.instance.power.unregister()
        return 'Closed power'
    else:
        return 'Power is not running.'


@app.route('/status_power', methods=['GET', 'POST'])
def status_power():
    return generate_json_response({
        "status": engine.instance.power.get_status(),
        "description": engine.instance.power.description
    })


def generate_json_response(obj):
    result_text = json.dumps(obj, cls=ComplexEncoder, sort_keys=True)
    return Response(response=result_text, headers={"Content-Type": "application/json"})


def changed_default_wallet():
    socketio.emit('changed_default_wallet')


def new_block():
    socketio.emit('new_block')


def peer_update():
    socketio.emit('peer_update')


def new_tx_in_pool():
    socketio.emit('new_tx_in_pool')


def power_status():
    socketio.emit('power_status')


def miner_status():
    socketio.emit('miner_status')


def cpu_usage(text):
    socketio.emit('cpu_usage', {'message': text})
