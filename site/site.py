from flask import Flask, redirect, request, url_for, render_template
import requests
import sys
sys.path.append('..')
import cfg

app = Flask(__name__)

ring = requests.get('http://' + cfg.BOOTSTRAP_ADDRESS + cfg.RING).json()
n_nodes = len(ring)
addresses = [x[0] for x in ring]
wallets = [x[1] for x in ring]

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', nodes=n_nodes)

@app.route('/<int:node>', methods=['GET'])
def node_info(node):
    title = 'Current wallet amount of node ' + str(node) + ':'
    balance = requests.get('http://' + addresses[node] + cfg.WALLET_BALANCE).json()
    return render_template('node.html', nodes=n_nodes, title=title, balance=balance)

@app.route('/<int:node>/bc', methods=['GET'])
def print_blockchain(node):

    # get ring from bootstrap
    node_inet_address = addresses[0]
    
    # get target blockchain
    bc = requests.get('http://' + node_inet_address + cfg.BLOCKCHAIN).json()
    col_names = ['index', 'timestamp', 'previous_hash', 'current_hash', 'nonce']
    bc_table = [[b[a] for a in col_names] for b in bc]
    title = 'Blockchain of node ' + str(node)

    return render_template('table_immutable.html', title=title, addresses=addresses, col_names=col_names, rows=bc_table)

@app.route('/trolia', methods=['GET'])
def trolia():
    return render_template('vehicle_insert.html', vtypes=['type1', 'deadpool', 'redbool'])

app.run(host='0.0.0.0', debug=True)
