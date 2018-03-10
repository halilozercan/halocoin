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
        from halocoin.model.wallet import Wallet
        if isinstance(obj, (bytes, bytearray)):
            return obj.hex()
        elif isinstance(obj, Wallet):
            return {
                "name": obj.name,
                "privkey": obj.get_privkey_str(),
                "pubkey": obj.get_pubkey_str(),
                "address": obj.address
            }
        elif isinstance(obj, set):
            return list(obj)
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


app = Flask(__name__)
socketio = SocketIO(app, async_mode='threading')
listen_thread = None
default_wallet = None


def get_wallet():
    from halocoin.ntwrk import Response
    from halocoin.model.wallet import Wallet
    global default_wallet

    wallet_name = request.values.get('wallet_name', None)
    password = request.values.get('password', None)
    if wallet_name is not None or password is not None:
        encrypted_wallet_content = engine.instance.clientdb.get_wallet(wallet_name)
        if encrypted_wallet_content is not None:
            try:
                wallet = Wallet.from_string(tools.decrypt(password, encrypted_wallet_content))
                return Response(
                    success=True,
                    data=wallet
                )
            except Exception as e:
                return Response(
                    success=False,
                    data=repr(e)
                )
        else:
            return Response(
                success=False,
                data="Wallet does not exist!"
            )
    elif default_wallet is not None:
        return Response(
            success=True,
            data=default_wallet
        )
    else:
        return Response(
            success=False,
            data="No wallet to work with"
        )


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
    return "~Alive and healthy~"


@app.route("/wallet/upload", methods=['POST'])
def upload_wallet():
    wallet_name = request.values.get('wallet_name', None)
    wallet_content = request.values.get('wallet_file', None)
    success = engine.instance.clientdb.upload_wallet(wallet_name, wallet_content)
    return generate_json_response({
        "success": success,
        "wallet_name": wallet_name
    })


@app.route('/wallet/<wallet_name>/download', methods=['GET'])
def download_wallet(wallet_name):
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


@app.route('/wallet/<wallet_name>/default', methods=['GET'])
def set_default_wallet(wallet_name):
    from halocoin.model.wallet import Wallet
    password = request.values.get('password', None)

    encrypted_wallet_content = engine.instance.clientdb.get_wallet(wallet_name)
    if encrypted_wallet_content is not None:
        try:
            wallet = Wallet.from_string(tools.decrypt(password, encrypted_wallet_content))
            global default_wallet
            default_wallet = copy.deepcopy(wallet)
            return generate_json_response({
                "success": True,
                "wallet": wallet
            })
        except Exception as e:
            return generate_json_response({
                "success": False,
                "error": repr(e)
            })
    else:
        return generate_json_response({
            "success": False,
            "error": "Unidentified error occurred!"
        })


@app.route('/wallet', methods=['GET'])
def info_wallet():
    wallet_result = get_wallet()

    if wallet_result.getFlag():
        wallet = wallet_result.getData()
        account = engine.instance.statedb.get_account(wallet.address)
        del account['tx_blocks']
        return generate_json_response({
            "success": True,
            "wallet": wallet,
            "account": account
        })
    else:
        return generate_json_response({
            "success": False,
            "error": wallet_result.getData()
        })


@app.route('/wallet/<wallet_name>/remove', methods=['POST'])
def remove_wallet(wallet_name):
    from halocoin.model.wallet import Wallet
    password = request.values.get('password', None)

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


@app.route('/wallet/new', methods=['POST'])
def new_wallet():
    from halocoin.model.wallet import Wallet
    wallet_name = request.values.get('wallet_name', None)
    pw = request.values.get('password', None)
    set_default = request.values.get('set_default', None)
    wallet = Wallet(wallet_name)
    success = engine.instance.clientdb.new_wallet(pw, wallet)
    if set_default and success:
        global default_wallet
        default_wallet = copy.deepcopy(wallet)

    return generate_json_response({
        "name": wallet_name,
        "success": success
    })


@app.route('/wallet/list', methods=['GET'])
def wallets():
    return generate_json_response({
        'wallets': engine.instance.clientdb.get_wallets()
    })


@app.route('/address/<address>', methods=['GET'])
def info_address(address):
    account = engine.instance.statedb.get_account(address)
    return generate_json_response({
        "address": address,
        "balance": account['amount'],
        "score": account['score'],
        "assigned_job": account['assigned_job'],
        "application": account['application']
    })


@app.route('/peers', methods=['GET'])
def peers():
    return generate_json_response(engine.instance.clientdb.get_peers())


@app.route('/node_id', methods=['GET'])
def node_id():
    return generate_json_response(engine.instance.db.get('node_id'))


@app.route('/subauths', methods=['GET'])
def auth_list():
    _list = engine.instance.statedb.get_auth_list()
    response = [engine.instance.statedb.get_auth(auth_name) for auth_name in _list]
    return generate_json_response(response)


@app.route('/job/list', methods=['GET'])
def jobs():
    type = request.values.get('type', 'available')
    page = int(request.values.get('page', 1))
    auth = request.values.get('auth', None)
    rows_per_page = int(request.values.get('rows_per_page', 5))
    result = {'total': 0, 'page': page, 'rows_per_page': rows_per_page, 'jobs': []}
    jobs = engine.instance.statedb.get_jobs(auth=auth, type=type)
    result['total'] = len(jobs)
    result['jobs'] = jobs[((page - 1) * rows_per_page):(page * rows_per_page)]

    return generate_json_response(result)


@app.route('/tx/send', methods=['POST'])
def send():
    amount = int(request.values.get('amount', 0))
    address = request.values.get('address', None)
    message = request.values.get('message', '')
    wallet_result = get_wallet()

    response = {"success": False}
    if not wallet_result.getFlag():
        response['error'] = wallet_result.getData()
        return generate_json_response(response)
    elif amount <= 0:
        response['error'] = "Amount cannot be lower than or equal to 0"
        return generate_json_response(response)
    elif address is None:
        response['error'] = "You need to specify a receiving address for transaction"
        return generate_json_response(response)

    tx = {'type': 'spend', 'amount': int(amount),
          'to': address, 'message': message, 'version': custom.version}

    wallet = wallet_result.getData()

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


@app.route('/tx/pool_reg', methods=['POST'])
def pool_reg():
    force = request.values.get('force', None)

    status = PowerService.system_status()
    if not status.getFlag() and force is None:
        return generate_json_response({
            'error': 'Power service is unavailable',
            'message': 'Power service cannot seem to function right now. '
                       'This probably means there is a problem with Docker connection or Docker is not installed.'
        })

    wallet_result = get_wallet()

    response = {"success": False}
    if not wallet_result.getFlag():
        response['error'] = wallet_result.getData()
        return generate_json_response(response)

    tx = {'type': 'pool_reg', 'version': custom.version}

    wallet = wallet_result.getData()

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


@app.route('/tx/application', methods=['POST'])
def application():
    _list = request.values.get('list', None)
    mode = request.values.get('mode', None)
    wallet_result = get_wallet()

    response = {"success": False}
    if not wallet_result.getFlag():
        response['error'] = wallet_result.getData()
        return generate_json_response(response)
    elif _list is None:
        response['error'] = "Application list is not given"
        return generate_json_response(response)
    elif mode is None or mode not in ['s', 'c']:
        response['error'] = "Application mode is not given or invalid"
        return generate_json_response(response)
    tx = {
        'type': 'application',
        'application':
            {
                'list': _list.split(',') if _list != '' else [],
                'mode': mode
            },
        'version': custom.version
    }

    wallet = wallet_result.getData()

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


@app.route('/tx/reward', methods=['POST'])
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


@app.route('/tx/job_dump', methods=['POST'])
def job_dump():
    from ecdsa import SigningKey
    job = {
        'id': request.values.get('id', None),
        'timestamp': request.values.get('timestamp', None),
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
    elif job['timestamp'] is None:
        response['error'] = "Job timestamp missing"
        return generate_json_response(response)
    elif job['amount'] == 0:
        response['error'] = "Reward amount is missing"
        return generate_json_response(response)
    elif job['download_url'] is None:
        response['error'] = "Job download url missing"
        return generate_json_response(response)
    elif job['upload_url'] is None:
        response['error'] = "Job upload url missing"
        return generate_json_response(response)
    elif job['hashsum'] is None:
        response['error'] = "Job hashsum missing"
        return generate_json_response(response)
    elif job['image'] is None:
        response['error'] = "Job image missing"
        return generate_json_response(response)
    elif privkey is None:
        response['error'] = "Job dumps need to be signed by private key belonging to certificate"
        return generate_json_response(response)
    elif certificate is None:
        response['error'] = "To give jobs, you must specify a certificate that is granted by root"
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


@app.route('/tx/auth_reg', methods=['POST'])
def auth_reg():
    from ecdsa import SigningKey
    certificate = request.values.get('certificate', None)
    privkey = request.values.get('privkey', None)
    host = request.values.get('host', None)
    description = request.values.get('description', None)
    supply = int(request.values.get('supply', 0))

    response = {"success": False}
    if privkey is None:
        response['error'] = "Auth registration transactions need to be signed by private key belonging to certificate"
        return generate_json_response(response)
    elif certificate is None:
        response['error'] = "Certificate is required for registration"
        return generate_json_response(response)
    elif host is None:
        response['error'] = "Authorities must provide a hosting address"
        return generate_json_response(response)
    elif description is None:
        response['error'] = "Authorities must provide a description"
        return generate_json_response(response)
    elif supply == 0:
        response['error'] = "Authorities must register with an initial supply"
        return generate_json_response(response)

    tx = {'type': 'auth_reg',
          'version': custom.version,
          'host': host,
          'supply': supply,
          'description': description}

    privkey = SigningKey.from_pem(privkey)

    common_name = tools.get_commonname_from_certificate(certificate)
    if engine.instance.statedb.get_auth(common_name) is not None:
        response['error'] = "An authority with common name {} is already registered.".format(common_name)
        return generate_json_response(response)
    if not tools.check_certificate_chain(certificate):
        response['error'] = "Given certificate is not granted by root"
        return generate_json_response(response)

    tx['certificate'] = certificate

    tx['pubkeys'] = [privkey.get_verifying_key().to_string()]  # We use pubkey as string
    tx['signatures'] = [tools.sign(tools.det_hash(tx), privkey)]
    engine.instance.blockchain.tx_queue.put(tx)
    response["success"] = True
    response["message"] = "Your transaction is successfully added to the queue"
    response["tx"] = tx
    return generate_json_response(response)


@app.route('/blockcount', methods=['GET'])
def blockcount():
    result = dict(length=engine.instance.db.get('length'),
                  known_length=engine.instance.clientdb.get('known_length'))
    result_text = json.dumps(result)
    return Response(response=result_text, headers={"Content-Type": "application/json"})


@app.route('/mempool', methods=['GET'])
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


@app.route('/blocks', methods=['GET'])
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


@app.route('/difficulty', methods=['GET'])
def difficulty():
    diff = engine.instance.blockchain.target(engine.instance.db.get('length'))
    return generate_json_response({"difficulty": diff})


@app.route('/stop', methods=['POST'])
def stop():
    engine.instance.db.put('stop', True)
    shutdown_server()
    print('Closed API')
    engine.instance.stop()
    return generate_json_response('Shutting down')


@app.route('/miner/start', methods=['POST'])
def start_miner():
    response = {"success": False}

    wallet_result = get_wallet()
    if not wallet_result.getFlag():
        response['error'] = wallet_result.getData()
        return generate_json_response(response)

    if engine.instance.miner.get_state() == Service.RUNNING:
        return generate_json_response('Miner is already running.')
    else:
        engine.instance.miner.set_wallet(wallet_result.getData())
        engine.instance.miner.register()
        return generate_json_response('Running miner')


@app.route('/miner/stop', methods=['POST'])
def stop_miner():
    if engine.instance.miner.get_state() == Service.RUNNING:
        engine.instance.miner.unregister()
        return generate_json_response('Closed miner')
    else:
        return generate_json_response('Miner is not running.')


@app.route('/miner', methods=['GET'])
def status_miner():
    status = {
        'running': engine.instance.miner.get_state() == Service.RUNNING
    }
    if status['running']:
        status['cpu'] = psutil.cpu_percent()
    return generate_json_response(status)


@app.route('/power/available', methods=['GET'])
def power_available():
    status = PowerService.system_status()
    return generate_json_response({
        "success": status.getFlag(),
        "message": status.getData()
    })


@app.route('/power/start', methods=['POST'])
def start_power():
    response = {"success": False}

    wallet_result = get_wallet()
    if not wallet_result.getFlag():
        response['error'] = wallet_result.getData()
        return generate_json_response(response)

    if engine.instance.power.get_state() == Service.RUNNING:
        return generate_json_response('Power is already running.')
    else:
        engine.instance.power.set_wallet(wallet_result.getData())
        engine.instance.power.register()
        return generate_json_response('Running power')


@app.route('/power/stop', methods=['POST'])
def stop_power():
    if engine.instance.power.get_state() == Service.RUNNING:
        engine.instance.power.unregister()
        return 'Closed power'
    else:
        return 'Power is not running.'


@app.route('/power', methods=['GET'])
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
