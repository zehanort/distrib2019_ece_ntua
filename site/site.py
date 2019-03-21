from flask import Flask, flash, redirect, request, url_for, render_template
import requests
import sys
sys.path.append('../code')
import cfg
import subprocess

from itertools import count
from numpy import mean

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

# NBC network variables needed by our site

ring = None
n_nodes = 0
addresses = None
wallets = None

# needed for testing
availiable_tests = [3, 5, 10]

def site_init():
    global ring, n_nodes, addresses, wallets

    try:
        r = requests.get('http://' + cfg.BOOTSTRAP_ADDRESS + cfg.RING)
    except requests.exceptions.ConnectionError as e:
        n_nodes = 0
        ring, addresses, wallets = None, None, None
        return False
    else:
        ring = r.json()
        n_nodes = len(ring)
        addresses = [x[0] for x in ring]
        wallets = [x[1] for x in ring]
        return True

# home page

@app.route('/', methods=['GET'])
def index():
    site_init()
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

# network administration routes

@app.route('/network', methods=['GET'])
def network():
    # check if network is already up
    running = site_init()
    return render_template('network.html', nodes=n_nodes, running=running)

@app.route('/network/init', methods=['GET', 'POST'])
def network_init():

    if request.method == 'GET':
        return render_template('network_init.html', nodes=n_nodes)
    
    elif request.method == 'POST':
        n = request.form['n']
        d = request.form['d']
        c = request.form['c']
        common = '-n {} -d {} -c {}'.format(n, d, c)
        script = ' '.join(['python3 {nbc_dir}nbc.py -a {address} -p {port}', common])

        base, excess = divmod(int(n), len(cfg.addresses))

        for address in cfg.addresses:
            port = count(cfg.start_port)
            for i in range(base + bool(excess > 0)):
                subprocess.Popen([
                    'ssh',
                    '-i', cfg.key_dir,
                    '{}@{}'.format('user', address),
                    script.format(nbc_dir=cfg.nbc_dir, address=address, port=next(port))
                ])
            excess -= 1

        site_init()
        return redirect(url_for('index'))

@app.route('/network/terminate', methods=['GET'])
def network_terminate():
    for address in addresses:
        requests.get('http://' + address + cfg.TERMINATE)
    ring = None
    n_nodes = 0
    addresses = None
    wallets = None
    return redirect(url_for('index'))

# testing routes

@app.route('/testing', methods=['GET', 'POST'])
def testing():
    site_init()

    if request.method == 'POST':
        if int(request.form['marxify']):
            requests.get('http://' + cfg.BOOTSTRAP_ADDRESS + cfg.DISTRIBUTE_WEALTH)
        subprocess.Popen('python3 ../code/test.py {}'.format(n_nodes), shell=True)

    return render_template('testing.html', nodes=n_nodes)

@app.route('/stats', methods=['GET'])
def view_stats():
    throughputs, blocktimes = [], []

    for n in range(n_nodes):
        throughputs.append(requests.get('http://' + addresses[n] + cfg.THROUGHPUT).json())
        blocktimes.append(requests.get('http://' + addresses[n] + cfg.BLOCK_TIME).json())
    throughput, blocktime = map(mean, [throughputs, blocktimes])    
    
    return render_template('stats.html', nodes=n_nodes, throughput=throughput, blocktime=blocktime)

app.run(host='83.212.97.85', port=8080, debug=True)
