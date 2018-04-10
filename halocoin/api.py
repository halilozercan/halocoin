import copy
import json
import os
import tempfile
import threading
import uuid

import psutil as psutil
# WARNING! Do not remove below import line. PyInstaller depends on it
from engineio import async_threading
from flask import Flask, request, Response, send_file
from flask_socketio import SocketIO

from halocoin import tools, engine, custom
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
signals = dict()
responses = dict()
_login_info = None


def get_login_info():
    global _login_info
    if _login_info is None:
        return {
            "name": None,
            "address": None
        }
    else:
        return copy.deepcopy(_login_info)


def set_login_info(info):
    global _login_info
    _login_info = copy.deepcopy(info)
    changed_login_info()


def get_wallet():
    # If wallet_name is not given, use default_wallet instead.
    # If default_wallet is also missing, raise an error.
    # default_wallet should just be a name. Every single action that requires private key,
    # must provide wallet password.
    from halocoin.ntwrk import Response
    from halocoin.model.wallet import Wallet

    login_name = get_login_info()['name']
    wallet_name = request.values.get('wallet_name', None)
    password = request.values.get('password', None)
    if wallet_name is None:
        wallet_name = login_name

    if wallet_name is not None and password is not None:
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


@app.route('/login', methods=['POST'])
def login():
    wallet_result = get_wallet()

    if wallet_result.getFlag():
        wallet = wallet_result.getData()
        set_login_info({
            "name": wallet.name,
            "address": wallet.address
        })

        return generate_json_response({
            "success": True,
            "wallet": wallet
        })
    else:
        return generate_json_response({
            "success": False,
            "error": wallet_result.getData()
        })


@app.route('/logout', methods=['POST'])
def logout():
    set_login_info(None)
    return generate_json_response({
        "success": True,
        "message": "Unset the default wallet"
    })


@app.route('/login/info', methods=['GET'])
def account():
    login_info = get_login_info()
    if login_info['name'] is None:
        return generate_json_response({
            "success": False,
            "wallet_name": None,
            "account": None
        })
    else:
        return generate_json_response({
            "success": True,
            "wallet_name": login_info['name'],
            "account": engine.instance.statedb.get_account(login_info['address'])
        })


@app.route('/wallet/info', methods=['GET'])
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


@app.route('/wallet/remove', methods=['POST'])
def remove_wallet():
    wallet_result = get_wallet()

    if wallet_result.getFlag():
        wallet = wallet_result.getData()
        engine.instance.clientdb.remove_wallet(wallet.name)
        return generate_json_response({
            "success": True,
            "message": "Removed wallet"
        })
    else:
        return generate_json_response({
            "success": False,
            "error": wallet_result.getData()
        })


@app.route('/wallet/new', methods=['POST'])
def new_wallet():
    from halocoin.model.wallet import Wallet
    wallet_name = request.values.get('wallet_name', None)
    pw = request.values.get('password', None)
    login = request.values.get('login', None)
    wallet = Wallet(wallet_name)
    success = engine.instance.clientdb.new_wallet(pw, wallet)
    if login and success:
        set_login_info({
            'name': wallet.name,
            'address': wallet.address
        })

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


@app.route('/miner', methods=['GET'])
def status_miner():
    status = {
        'running': engine.instance.miner.get_state() == Service.RUNNING
    }
    if status['running']:
        status['cpu'] = psutil.cpu_percent()
    return generate_json_response(status)


@app.route('/engine', methods=['GET'])
def engine_status():
    return generate_json_response({
        "blockchain": engine.instance.blockchain.get_state(readable=True),
        "peer_receive": engine.instance.peer_receive.get_state(readable=True),
        "peers_check": engine.instance.peers_check.get_state(readable=True),
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
    elif service_name == "miner":
        corresponding_service = engine.instance.miner
        wallet = get_wallet()
        if wallet.getFlag():
            corresponding_service.set_wallet(wallet.getData())
        else:
            return generate_json_response({
                "success": False,
                "message": "This service requires a valid wallet"
            })

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


def changed_login_info():
    socketio.emit('changed_default_wallet')


def new_block():
    socketio.emit('new_block')


def peer_update():
    socketio.emit('peer_update')


def new_tx_in_pool():
    socketio.emit('new_tx_in_pool')


def miner_status():
    socketio.emit('miner_status')


def cpu_usage(text):
    socketio.emit('cpu_usage', {'message': text})
