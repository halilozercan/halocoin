import copy
import json
import tempfile
import threading
import uuid

# WARNING! Do not remove below import line. PyInstaller depends on it
from engineio import async_threading
from flask import Flask, request, Response, send_file
from flask_socketio import SocketIO

from halocoin import tools, engine, custom
from halocoin.model.wallet import Wallet
from halocoin.power import PowerService
from halocoin.service import Service

async_threading  # PyCharm automatically removes unused imports. This prevents it


class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):

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
signals = dict()
responses = dict()


def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()


def run():
    def thread_target():
        socketio.run(app, host=engine.instance.config['api']['host'], port=engine.instance.config['api']['port'])

    global listen_thread
    listen_thread = threading.Thread(target=thread_target, daemon=True)
    listen_thread.start()
    print("Started API on {}:{}".format(engine.instance.config['api']['host'], engine.instance.config['api']['port']))


@socketio.on('connect')
def connect():
    print("%s connected" % request.sid)
    return ""


@app.route('/')
def hello():
    return "~Alive and healthy~"


def get_wallet():
    from halocoin.ntwrk import Response
    from halocoin.model.wallet import Wallet

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
    else:
        return Response(
            success=False,
            data="You have to give a wallet"
        )


@app.route("/wallet/upload", methods=['POST'])
def upload_wallet():
    wallet_name = request.values.get('wallet_name', None)
    wallet_content = request.values.get('wallet_file', None)
    success = engine.instance.clientdb.upload_wallet(wallet_name, wallet_content)
    return generate_json_response({
        "success": success,
        "wallet_name": wallet_name
    })


@app.route('/wallet/download', methods=['GET'])
def download_wallet():
    wallet_name = request.values.get('wallet_name', None)
    if wallet_name is None:
        return generate_json_response({
            "success": False,
            "error": "Give wallet name"
        })
    wallet_content = engine.instance.clientdb.get_wallet(wallet_name)
    f = tempfile.NamedTemporaryFile()
    f.write(wallet_content)
    f.seek(0)
    return send_file(f, as_attachment=True, attachment_filename=wallet_name)


@app.route('/wallet/info', methods=['GET'])
def wallet_info():
    walletResponse = get_wallet()
    if not walletResponse.getFlag():
        return generate_json_response({
            "success": False,
            "error": walletResponse.getData()
        })
    wallet = walletResponse.getData()
    return generate_json_response({
        "success": True,
        "wallet": wallet.as_dict(),
        "account": engine.instance.statedb.get_account(wallet.address)
    })


@app.route('/wallet/new', methods=['POST'])
def new_wallet():
    wallet_name = request.values.get('wallet_name', None)
    pw = request.values.get('password', None)
    wallet = Wallet(wallet_name)
    success = engine.instance.clientdb.new_wallet(pw, wallet)

    return generate_json_response({
        "name": wallet_name,
        "success": success
    })


@app.route('/wallet/list', methods=['GET'])
def wallet_list():
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
    for i, auth in enumerate(response):
        available_jobs = engine.instance.statedb.get_jobs(auth=auth['name'], type='available')
        auth['available_reward'] = 0
        for job in available_jobs:
            auth['available_reward'] += job['reward']
        response[i] = auth
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


def send_to_blockchain(tx):
    response = dict()
    api_key = str(uuid.uuid4())
    tx['api_key'] = api_key
    signals[api_key] = threading.Event()
    engine.instance.blockchain.tx_queue.put(tx)
    signals[api_key].wait()
    if api_key in responses and responses[api_key].getFlag():
        response["success"] = True
        response["message"] = "Your transaction is successfully added to the queue"
        response["tx"] = tx
    elif api_key in responses:
        response["success"] = False
        response["message"] = responses[api_key].getData()
        response["tx"] = tx
    else:
        response["success"] = False
        response["message"] = "Failed to add transaction"
        response["tx"] = tx

    del signals[api_key]
    del responses[api_key]
    return response


@app.route('/tx/send', methods=['POST'])
def send():
    walletResponse = get_wallet()
    if not walletResponse.getFlag():
        return generate_json_response({
            "success": False,
            "error": walletResponse.getData()
        })
    wallet = walletResponse.getData()

    amount = int(request.values.get('amount', 0))
    address = request.values.get('address', None)
    message = request.values.get('message', '')

    response = {"success": False}
    if amount <= 0:
        response['error'] = "Amount cannot be lower than or equal to 0"
        return generate_json_response(response)
    elif address is None:
        response['error'] = "You need to specify a receiving address for transaction"
        return generate_json_response(response)

    tx = {'type': 'spend', 'amount': int(amount),
          'to': address, 'message': message, 'version': custom.version}

    if 'count' not in tx:
        try:
            tx['count'] = engine.instance.statedb.known_tx_count(wallet.address, count_pool=True)
        except:
            tx['count'] = 0
    if 'pubkeys' not in tx:
        tx['pubkeys'] = [wallet.get_pubkey_str()]  # We use pubkey as string
    if 'signatures' not in tx:
        tx['signatures'] = [tools.sign(tools.det_hash(tx), wallet.privkey)]

    response = send_to_blockchain(tx)

    return generate_json_response(response)


@app.route('/tx/pool_reg', methods=['POST'])
def pool_reg():
    force = request.values.get('force', None)

    status = PowerService.docker_status()
    if not status.getFlag() and force is None:
        return generate_json_response({
            'error': 'Power service is unavailable',
            'message': 'Power service cannot seem to function right now. '
                       'This probably means there is a problem with Docker connection or Docker is not installed.'
        })

    walletResponse = get_wallet()
    if not walletResponse.getFlag():
        return generate_json_response({
            "success": False,
            "error": walletResponse.getData()
        })
    wallet = walletResponse.getData()

    tx = {'type': 'pool_reg', 'version': custom.version}

    if 'count' not in tx:
        try:
            tx['count'] = engine.instance.statedb.known_tx_count(wallet.address, count_pool=True)
        except:
            tx['count'] = 0
    if 'pubkeys' not in tx:
        tx['pubkeys'] = [wallet.get_pubkey_str()]  # We use pubkey as string
    if 'signatures' not in tx:
        tx['signatures'] = [tools.sign(tools.det_hash(tx), wallet.privkey)]

    response = send_to_blockchain(tx)

    return generate_json_response(response)


@app.route('/tx/application', methods=['POST'])
def application():
    walletResponse = get_wallet()
    if not walletResponse.getFlag():
        return generate_json_response({
            "success": False,
            "error": walletResponse.getData()
        })
    wallet = walletResponse.getData()

    _list = request.values.get('list', None)
    mode = request.values.get('mode', None)

    response = {"success": False}
    if _list is None:
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

    if 'count' not in tx:
        try:
            tx['count'] = engine.instance.statedb.known_tx_count(wallet.address, count_pool=True)
        except:
            tx['count'] = 0
    if 'pubkeys' not in tx:
        tx['pubkeys'] = [wallet.get_pubkey_str()]  # We use pubkey as string
    if 'signatures' not in tx:
        tx['signatures'] = [tools.sign(tools.det_hash(tx), wallet.privkey)]

    response = send_to_blockchain(tx)

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

    response = send_to_blockchain(tx)

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

    response = send_to_blockchain(tx)

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

    response = send_to_blockchain(tx)

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
        if tx['type'] == 'spend' or tx['type'] == 'application' or tx['type'] == 'pool_reg':
            pool[i]['issuer'] = tools.tx_owner_address(tx)
        elif tx['type'] == 'reward' or tx['type'] == 'auth_reg' or tx['type'] == 'job_dump':
            pool[i]['issuer'] = tools.reward_owner_name(tx)

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
        for i, tx in enumerate(block['txs']):
            if tx['type'] == 'spend' or tx['type'] == 'application' or tx['type'] == 'pool_reg':
                block['txs'][i]['issuer'] = tools.tx_owner_address(tx)
            elif tx['type'] == 'reward' or tx['type'] == 'auth_reg' or tx['type'] == 'job_dump':
                block['txs'][i]['issuer'] = tools.reward_owner_name(tx)
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


@app.route('/docker', methods=['GET'])
def docker_status():
    status = PowerService.docker_status()
    return generate_json_response({
        "success": status.getFlag(),
        "message": status.getData()
    })


@app.route('/docker/images', methods=['GET'])
def docker_images():
    status = PowerService.docker_images()
    return generate_json_response({
        "success": status.getFlag(),
        "message": status.getData()
    })


@app.route('/engine', methods=['GET'])
def engine_status():
    return generate_json_response({
        "blockchain": engine.instance.blockchain.get_state(readable=True),
        "peer_receive": engine.instance.peer_receive.get_state(readable=True),
        "peers_check": engine.instance.peers_check.get_state(readable=True),
        "power": engine.instance.power.get_state(readable=True),
        "miner": engine.instance.miner.get_state(readable=True)
    })


@app.route('/service/<service_name>/start', methods=['POST'])
def service_start(service_name):
    corresponding_service = None
    if service_name == "blockchain":
        corresponding_service = engine.instance.blockchain
    elif service_name == "peers_check":
        corresponding_service = engine.instance.peers_check
    elif service_name == "peer_receive":
        corresponding_service = engine.instance.peer_receive
    elif service_name == "power" or service_name == "miner":
        walletResponse = get_wallet()
        if not walletResponse.getFlag():
            return generate_json_response({
                "success": False,
                "error": walletResponse.getData()
            })
        wallet = walletResponse.getData()
        if service_name == "power":
            corresponding_service = engine.instance.power
        elif service_name == "miner":
            corresponding_service = engine.instance.miner
        corresponding_service.set_wallet(wallet)

    if corresponding_service is None:
        return generate_json_response({
            "success": False,
            "message": "There is no such service"
        })

    if corresponding_service.get_state() == Service.RUNNING:
        return generate_json_response('{} is already running.'.format(corresponding_service.name))
    else:
        corresponding_service.register()
        return generate_json_response('Started {}'.format(corresponding_service.name))


@app.route('/service/<service_name>/stop', methods=['POST'])
def service_stop(service_name):
    corresponding_service = None
    if service_name == "blockchain":
        corresponding_service = engine.instance.blockchain
    elif service_name == "peers_check":
        corresponding_service = engine.instance.peers_check
    elif service_name == "peer_receive":
        corresponding_service = engine.instance.peer_receive
    elif service_name == "power":
        corresponding_service = engine.instance.power
    elif service_name == "miner":
        corresponding_service = engine.instance.miner

    if corresponding_service is None:
        return generate_json_response({
            "success": False,
            "message": "There is no such service"
        })

    if corresponding_service.get_state() == Service.RUNNING:
        corresponding_service.unregister()
        return generate_json_response('Stopped {}'.format(corresponding_service.name))
    else:
        return generate_json_response('{} is already stopped.'.format(corresponding_service.name))


@app.route('/service/<service_name>/status', methods=['GET'])
def service_status(service_name):
    corresponding_service = None
    if service_name == "blockchain":
        corresponding_service = engine.instance.blockchain
    elif service_name == "peers_check":
        corresponding_service = engine.instance.peers_check
    elif service_name == "peer_receive":
        corresponding_service = engine.instance.peer_receive
    elif service_name == "power":
        corresponding_service = engine.instance.power
    elif service_name == "miner":
        corresponding_service = engine.instance.miner

    if corresponding_service is None:
        return generate_json_response({
            "success": False,
            "message": "There is no such service"
        })

    return generate_json_response(corresponding_service.get_status())


def generate_json_response(obj):
    result_text = json.dumps(obj, cls=ComplexEncoder, sort_keys=True)
    return Response(response=result_text, headers={"Content-Type": "application/json"})


def new_block():
    socketio.emit('new_block')


def peer_update():
    socketio.emit('peer_update')


def new_tx_in_pool():
    socketio.emit('new_tx_in_pool')


def power_status():
    socketio.emit('power_status', {
        "status": engine.instance.power.get_status(),
        "description": engine.instance.power.description,
        "running": engine.instance.power.get_state() == Service.RUNNING
    })


def docker_status_socket():
    socketio.emit('docker_status')


def miner_status():
    socketio.emit('miner_status')


def cpu_usage(text):
    socketio.emit('cpu_usage', {'message': text})
