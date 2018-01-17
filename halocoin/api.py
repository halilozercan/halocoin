import json
import os
import tempfile
import threading

import psutil as psutil
from flask import Flask, request, Response, send_file
from flask_socketio import SocketIO

from halocoin import tools, engine, custom
from halocoin.blockchain import BlockchainService
from halocoin.service import Service


class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (bytes, bytearray)):
            return obj.hex()
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


def blockchain_synced(func):
    def wrapper(*args, **kwargs):
        if engine.instance.blockchain.get_chain_state() == BlockchainService.IDLE:
            return func(*args, **kwargs)
        else:
            return 'Blockchain is syncing. This method is not reliable while operation continues.\n' + \
                   str(engine.instance.db.get('length')) + '-' + str(engine.instance.db.get('known_length'))

    # To keep the function name same for RPC helper
    wrapper.__name__ = func.__name__

    return wrapper


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
    host = os.environ.get('COINAMI_API_HOST', "localhost")
    listen_thread = threading.Thread(target=thread_target, daemon=True)
    listen_thread.start()
    print("Started API on {}:{}".format(host, engine.instance.config['port']['api']))
    """
    Deprecated in favor of electron app
    import webbrowser
    webbrowser.open('http://' + host + ':' + str(engine.instance.config['port']['api']))
    """


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
            account = engine.instance.account.get_account(wallet.address, apply_tx_pool=True)
            return generate_json_response({
                "name": wallet.name,
                "pubkey": wallet.get_pubkey_str(),
                "privkey": wallet.get_privkey_str(),
                "address": wallet.address,
                "balance": account['amount'],
                "deposit": account['stake']
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


@app.route('/set_default_wallet', methods=['GET', 'POST'])
def set_default_wallet():
    wallet_name = request.values.get('wallet_name', None)
    password = request.values.get('password', None)
    delete = request.values.get('delete', None)
    if delete is not None:
        return generate_json_response({
            "success": engine.instance.clientdb.delete_default_wallet()
        })
    else:
        return generate_json_response({
            "success": engine.instance.clientdb.set_default_wallet(wallet_name, password)
        })


@app.route('/history', methods=['GET', 'POST'])
# @blockchain_synced
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
    account = engine.instance.account.get_account(wallet.address)
    txs = {
        "send": [],
        "recv": []
    }
    for block_index in reversed(account['tx_blocks']):
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


@app.route('/jobs')
def jobs():
    type = request.values.get('type', 'all')
    result = {'available': None, 'assigned': None}
    if type == 'available' or type == 'all':
        result['available'] = engine.instance.account.get_available_jobs()

    if type == 'assigned' or type == 'all':
        result['assigned'] = engine.instance.account.get_assigned_jobs()

    return generate_json_response(result)


@app.route('/send', methods=['GET', 'POST'])
# @blockchain_synced
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
            tx['count'] = engine.instance.account.known_tx_count(wallet.address)
        except:
            tx['count'] = 0
    if 'pubkeys' not in tx:
        tx['pubkeys'] = [wallet.get_pubkey_str()]  # We use pubkey as string
    if 'signatures' not in tx:
        tx['signatures'] = [tools.sign(tools.det_hash(tx), wallet.privkey)]
    engine.instance.blockchain.tx_queue.put(tx)
    response["success"] = True
    response["message"] = 'Tx amount:{} to:{} added to the pool'.format(tx['amount'], tx['to'])
    return generate_json_response(response)


@app.route('/deposit', methods=['GET', 'POST'])
# @blockchain_synced
def deposit():
    from halocoin.model.wallet import Wallet
    amount = int(request.values.get('amount', 0))  # Bidding amount
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
    elif wallet_name is None:
        response['error'] = "Wallet name is not given and there is no default wallet"
        return generate_json_response(response)
    elif password is None:
        response['error'] = "Password missing!"
        return generate_json_response(response)

    tx = {'type': 'deposit', 'amount': int(amount), 'version': custom.version}

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
            tx['count'] = engine.instance.account.known_tx_count(wallet.address)
        except:
            tx['count'] = 0
    if 'pubkeys' not in tx:
        tx['pubkeys'] = [wallet.get_pubkey_str()]  # We use pubkey as string
    if 'signatures' not in tx:
        tx['signatures'] = [tools.sign(tools.det_hash(tx), wallet.privkey)]
    engine.instance.blockchain.tx_queue.put(tx)
    response["success"] = True
    if response['success']:
        response["message"] = 'Your deposit with amount {} is added to the pool'\
            .format(tx['amount'])
    else:
        response["error"] = 'Your deposit request failed to pass integrity check'
    return generate_json_response(response)


@app.route('/withdraw', methods=['GET', 'POST'])
# @blockchain_synced
def withdraw():
    from halocoin.model.wallet import Wallet
    amount = int(request.values.get('amount', 0))  # Bidding amount
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
    elif wallet_name is None:
        response['error'] = "Wallet name is not given and there is no default wallet"
        return generate_json_response(response)
    elif password is None:
        response['error'] = "Password missing!"
        return generate_json_response(response)

    tx = {'type': 'withdraw', 'amount': int(amount), 'version': custom.version}

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
            tx['count'] = engine.instance.account.known_tx_count(wallet.address)
        except:
            tx['count'] = 0
    if 'pubkeys' not in tx:
        tx['pubkeys'] = [wallet.get_pubkey_str()]  # We use pubkey as string
    if 'signatures' not in tx:
        tx['signatures'] = [tools.sign(tools.det_hash(tx), wallet.privkey)]
    engine.instance.blockchain.tx_queue.put(tx)
    response["success"] = True
    if response['success']:
        response["message"] = 'Your deposit with amount {} is added to the pool'\
            .format(tx['amount'])
    else:
        response["error"] = 'Your deposit request failed to pass integrity check'
    return generate_json_response(response)


@app.route('/reward', methods=['GET', 'POST'])
def reward():
    from ecdsa import SigningKey
    job_id = request.values.get('job_id', None)
    address = request.values.get('address', None)
    cert_pem = request.values.get('cert_pem', None)
    priv_key_pem = request.values.get('privkey_pem', None)

    response = {"success": False}
    if job_id is None:
        response['error'] = "You need to specify a job id for the reward"
        return generate_json_response(response)
    elif address is None:
        response['error'] = "You need to specify a receiving address for the reward"
        return generate_json_response(response)
    elif priv_key_pem is None:
        response['error'] = "Reward transactions need to be signed by private key belonging to certificate"
        return generate_json_response(response)
    elif cert_pem is None:
        response['error'] = "To reward, you must specify a common name or certificate that is granted by root"
        return generate_json_response(response)

    tx = {'type': 'reward', 'job_id': job_id, 'to': address, 'version': custom.version}

    privkey = SigningKey.from_pem(priv_key_pem)
    common_name = tools.get_commonname_from_certificate(cert_pem)
    tx['auth'] = common_name

    tx['pubkeys'] = [privkey.get_verifying_key().to_string()]  # We use pubkey as string
    tx['signatures'] = [tools.sign(tools.det_hash(tx), privkey)]
    engine.instance.blockchain.tx_queue.put(tx)
    response["success"] = True
    response["message"] = 'Reward to:{} sent to the pool'.format(tx['job_id'])
    return generate_json_response(response)


@app.route('/job_dump', methods=['GET', 'POST'])
def job_dump():
    from ecdsa import SigningKey
    job = {
        'id': request.values.get('job_id', None),
        'timestamp': request.values.get('job_timestamp', None),
        'amount': int(request.values.get('amount', 0))
    }
    cert_pem = request.values.get('cert_pem', None)
    priv_key_pem = request.values.get('privkey_pem', None)

    response = {"success": False}
    if job['id'] is None:
        response['error'] = "Job id missing"
        return generate_json_response(response)
    elif priv_key_pem is None:
        response['error'] = "Job dumps need to be signed by private key belonging to certificate"
        return generate_json_response(response)
    elif cert_pem is None:
        response['error'] = "To give jobs, you must specify a certificate that is granted by root"
        return generate_json_response(response)
    elif job['amount'] == 0:
        response['error'] = "Reward amount is missing"
        return generate_json_response(response)

    tx = {'type': 'job_dump', 'job': job, 'version': custom.version}

    privkey = SigningKey.from_pem(priv_key_pem)
    common_name = tools.get_commonname_from_certificate(cert_pem)
    tx['auth'] = common_name

    tx['pubkeys'] = [privkey.get_verifying_key().to_string()]  # We use pubkey as string
    tx['signatures'] = [tools.sign(tools.det_hash(tx), privkey)]
    engine.instance.blockchain.tx_queue.put(tx)
    response["success"] = True
    response["message"] = 'Job dump succesfully is added to the transaction pool'
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
    if engine.instance.account.get_auth(common_name) is not None:
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
    response["message"] = 'Auth registration is added to the pool'
    return generate_json_response(response)


@app.route('/blockcount', methods=['GET', 'POST'])
def blockcount():
    result = dict(length=engine.instance.db.get('length'),
                  known_length=engine.instance.db.get('known_length'))
    result_text = json.dumps(result)
    return Response(response=result_text, headers={"Content-Type": "application/json"})


@app.route('/txs', methods=['GET', 'POST'])
def txs():
    purge = request.values.get('purge', None)
    if purge is not None:
        engine.instance.blockchain.tx_pool_pop_all()
    pool = engine.instance.blockchain.tx_pool()
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


@app.route('/block', methods=['GET', 'POST'])
def block():
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
# @blockchain_synced
def difficulty():
    diff = engine.instance.blockchain.target(engine.instance.db.get('length'))
    return generate_json_response({"difficulty": diff})


@app.route('/balance', methods=['GET', 'POST'])
# @blockchain_synced
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

    account = engine.instance.account.get_account(address, apply_tx_pool=True)
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
        return 'Closed miner'
    else:
        return 'Miner is not running.'


@app.route('/status_miner', methods=['GET', 'POST'])
def status_miner():
    status = {
        'running': engine.instance.miner.get_state() == Service.RUNNING
    }
    if status['running']:
        status['cpu'] = psutil.cpu_percent()
    return generate_json_response(status)


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
    from halocoin.model.wallet import Wallet
    status = {
        'running': engine.instance.power.get_state() == Service.RUNNING,
        'assigned': ''
    }
    default_wallet_props = engine.instance.clientdb.get_default_wallet()
    default_wallet = engine.instance.clientdb.get_wallet(default_wallet_props['wallet_name'])
    default_wallet = Wallet.from_string(tools.decrypt(default_wallet_props['password'], default_wallet))
    own_address = default_wallet.address
    own_account = engine.instance.account.get_account(own_address)
    assigned_job = own_account['assigned_job']
    status['assigned'] = assigned_job
    return generate_json_response(status)


def generate_json_response(obj):
    result_text = json.dumps(obj, cls=ComplexEncoder)
    return Response(response=result_text, headers={"Content-Type": "application/json"})


def changed_default_wallet():
    socketio.emit('changed_default_wallet')


def new_block():
    socketio.emit('new_block')


def peer_update():
    socketio.emit('peer_update')


def new_tx_in_pool():
    socketio.emit('new_tx_in_pool')
