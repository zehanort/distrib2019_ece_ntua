import requests
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS

import cfg
import block
import node
import transaction
import wallet

### JUST A BASIC EXAMPLE OF A REST API WITH FLASK

app = Flask(__name__)
CORS(app)
blockchain = Blockchain()

#.......................................................................................

# get all transactions in the blockchain

@app.route('/transactions/get', methods=['GET'])
def get_transactions():
    transactions = blockchain.transactions

    response = {'transactions': transactions}
    return jsonify(response), 200

# run it once fore every node

if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    
    # define command line arguments
    required = parser.add_argument_group('required arguments')
    required.add_argument('-a', '--address', type=str, help='IP address used by node to connect to NBC network', required=True)
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    parser.add_argument('-n', '--nodes', default=5, type=int, help='number of nodes in the NBC network')
    parser.add_argument('-d', '--difficulty', default=1, type=int, help="number of leading 0's of a nonce")
    parser.add_argument('-c', '--capacity', default=1, type=int, help='number of transactions per block')
    
    # parse command line arguments
    args = parser.parse_args()
    address = args.address
    port = args.address

    # set global variables
    cfg.DIFFICULTY = args.difficulty
    cfg.CAPACITY = args.capacity

    if cfg.is_bootstrap(address + ':' + port):
        cfg.NODES = args.nodes

    app.run(host=args.address, port=args.port)
