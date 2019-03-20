from flask import Flask, flash, redirect, request, url_for, render_template
import requests
import sys
sys.path.append('../code')
import cfg

import subprocess

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

ring = requests.get('http://' + cfg.BOOTSTRAP_ADDRESS + cfg.RING).json()
n_nodes = len(ring)
addresses = [x[0] for x in ring]
wallets = [x[1] for x in ring]

# home page

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', nodes=n_nodes)

# node routes

@app.route('/<int:node>', methods=['GET'])
def node_info(node):
    return render_template('node.html', n=node, nodes=n_nodes)

@app.route('/<int:node>/wallet/balance', methods=['GET'])
def wallet_balance(node):
    balance = requests.get('http://' + addresses[node] + cfg.WALLET_BALANCE).json()   
    return render_template('wallet_balance.html', n=node, nodes=n_nodes, balance=balance)

@app.route('/<int:node>/transaction/new', methods=['GET', 'POST'])
def make_transaction(node):

    if request.method == 'GET':
        balance = requests.get('http://' + addresses[node] + cfg.WALLET_BALANCE).json()
        return render_template('make_transaction.html',
            n=node,
            balance=balance,
            nodes=n_nodes,
            recipients=[n for n in range(n_nodes) if node != n]
        )

    elif request.method == 'POST':
        recipient_id = int(request.form['node_id'])
        amount = request.form['amount']

        data = {
        'recipient_address' : wallets[recipient_id],
        'amount' : int(amount)
        }
        r = requests.post('http://' + addresses[node] + cfg.CREATE_TRANSACTION, json=data)
        flash('Transaction successfully created!')
        return redirect(url_for('node_info', node=node))

@app.route('/<int:node>/bc', methods=['GET'])
def view_blockchain(node):

    # get ring from bootstrap
    node_inet_address = addresses[0]
    
    # get target blockchain
    bc = requests.get('http://' + node_inet_address + cfg.BLOCKCHAIN).json()
    col_names = ['index', 'timestamp', 'previous_hash', 'current_hash', 'nonce']
    bc_table = [[b[a] for a in col_names] for b in bc]

    return render_template('table_immutable.html', n=node, nodes=n_nodes, col_names=col_names, rows=bc_table)

# testing routes

@app.route('/init', methods=['GET'])
def init():
    return 'Under construction...', 200

@app.route('/test', methods=['GET', 'POST'])
def run_test(marxify=False):
    if request.method == 'POST':
        if marxify:
            print('asked to distribute wealth!')
            requests.get('http://' + cfg.BOOTSTRAP_ADDRESS + cfg.DISTRIBUTE_WEALTH)
        subprocess.run(['python3', '../code/test.py', str(n_nodes)])
    return render_template('testing.html', nodes=n_nodes)

@app.route('/stats', methods=['GET'])
def view_stats():
    from numpy import mean
    
    throughputs, blocktimes = [], []
    for n in range(n_nodes):
        throughputs.append(requests.get('http://' + addresses[n] + cfg.THROUGHPUT).json())
        blocktimes.append(requests.get('http://' + addresses[n] + cfg.BLOCK_TIME).json())
    throughput, blocktime = map(mean, [throughputs, blocktimes])
    
    return render_template('stats.html', nodes=n_nodes, throughput=throughput, blocktime=blocktime)

app.run(host='127.0.0.1', port=8080, debug=True)
