#!/usr/bin/env python3
import io
import json
import os
import subprocess
import sys

from pygments import highlight
from pygments.formatters import TerminalFormatter
from pygments.lexers import JsonLexer


def run_command(command):
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=FNULL)
    content = io.TextIOWrapper(proc.stdout, encoding="utf-8").read()
    content = json.loads(content)
    return json.dumps(content, indent=4, sort_keys=True)


sys.argv = sys.argv[1:]
FNULL = open(os.devnull, 'w')
if sys.argv[0] == 'new_wallet':
    wallet_name = sys.argv[1]
    password = sys.argv[2]
    content = run_command(
        ['curl', "http://0.0.0.0:7001/new_wallet?wallet_name=" + wallet_name + "&password=" + password +
         "&set_default=1"])
elif sys.argv[0] == "info_wallet":
    content = run_command(['curl', 'http://0.0.0.0:7001/info_wallet'])
elif sys.argv[0] == "mempool":
    content = run_command(['curl', 'http://0.0.0.0:7001/mempool'])
elif sys.argv[0] == "blockcount":
    content = run_command(['curl', 'http://0.0.0.0:7001/blockcount'])
elif sys.argv[0] == "deposit":
    amount = sys.argv[1]
    password = sys.argv[2]
    content = run_command(['curl', 'http://0.0.0.0:7001/deposit?amount=' + amount + "&password=" + password])
elif sys.argv[0] == "send":
    address = sys.argv[1]
    amount = sys.argv[2]
    password = sys.argv[3]
    content = run_command(['curl', 'http://0.0.0.0:7001/send?address=' + address + '&amount=' + amount +
                           "&password=" + password])
elif sys.argv[0] == "start_miner":
    content = run_command(['curl', 'http://0.0.0.0:7001/start_miner'])
elif sys.argv[0] == "stop_miner":
    content = run_command(['curl', 'http://0.0.0.0:7001/stop_miner'])

print(highlight(content, JsonLexer(), TerminalFormatter()))
