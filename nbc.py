from flask import Flask, jsonify, request, render_template
from flask_cors import CORS

import cfg
import requests
from node import *
from wallet import *
from block import *
from transaction import *
from utils import *

from threading import Thread, Lock

assign_id_lock = Lock()

app = Flask(__name__)
CORS(app)

# node will be defined later (bootstrap or simple)
node = None

### ROUTES FOR ALL NBC NETWORK NODES ###

@app.route('/ring', methods=['GET'])
def print_ring():
    return jsonify(node.ring), 200

@app.route(cfg.CREATE_TRANSACTION, methods=['POST'])
def create_new_transaction():
    node.create_transaction(request.json['recipient_address'], request.json['amount'])
    return 'Transaction created successfully.\n', 200

@app.route(cfg.NEW_TRANSACTION, methods=['POST'])
def get_new_transaction():
    t = Transaction(**request.get_json())

    # assign handling of incoming transaction to a new thread
    Thread(target=node.add_transaction, args=(t,)).start()

    return 'New transaction received\n', 200

@app.route(cfg.NEW_BLOCK, methods=['POST'])
def get_new_block():
    new_block = Block(**request.get_json())

    print('----> Received new block from network', new_block.current_hash)
    
    # append new_block to node block_queue
    node.block_queue.put(new_block)
    
    # spawn a thread to resolve block_queue after mining_lock is released
    block_queue_resolver = Thread(target=node.resolve_block_queue)
    block_queue_resolver.start()

    return 'New block received\n', 200

@app.route(cfg.POOL, methods=['GET'])
def return_pool():
    return jsonify(node.transaction_pool.to_dict()), 200

@app.route(cfg.BLOCKCHAIN, methods=['GET'])
def return_blockchain():
    return jsonify(node.blockchain[1:].to_dict(append='current_hash', append_rec='signature')), 200

@app.route(cfg.BLOCKCHAIN_LENGTH, methods=['GET'])
def report_blockchain_length():
    return jsonify(node.blockchain_length), 200

@app.route(cfg.BLOCKCHAIN_HASHES, methods=['POST'])
def report_blockchain_diffs():
    hashes = request.get_json()
    return jsonify(node.blockchain_diff(hashes)), 200

@app.route(cfg.WALLET_BALANCE, methods=['GET'])
def report_wallet_balance():
    return jsonify(node.wallet_balance()), 200

if __name__ == '__main__':
    from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

    parser = ArgumentParser(
        description='A simple node and miner of the NoobCoin network.',
        formatter_class=ArgumentDefaultsHelpFormatter
    )

    # define command line arguments
    required = parser.add_argument_group('required arguments')
    required.add_argument('-a', '--address', type=str, help='IP address used by node to connect to NBC network', required=True)
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    parser.add_argument('-n', '--nodes', default=5, type=int, help='number of nodes in the NBC network')
    parser.add_argument('-d', '--difficulty', default=3, type=int, help="number of leading 0's of a nonce")
    parser.add_argument('-c', '--capacity', default=1, type=int, help='number of transactions per block')

    # parse command line arguments
    args = parser.parse_args()
    address = args.address
    port = args.port
    full_address = address + ':' + str(port)

    # set global variables
    cfg.DIFFICULTY = args.difficulty
    cfg.CAPACITY = args.capacity

    if cfg.is_bootstrap(full_address):
        cfg.NODES = args.nodes
        node = BootstrapNode(full_address)
        
        ### ROUTES EXCLUSIVE TO BOOTSTRAP NODE ###

        # give ids to all other nodes
        @app.route(cfg.GET_ID, methods=['POST'])
        def assign_id_to_node():
            with assign_id_lock:
                inet_address = request.form['inet_address']
                wallet_address = request.form['wallet_address']

                response = {
                    'id' : node.register_node_to_ring(inet_address, wallet_address),
                    'genesis_block' : node.blockchain[0].to_dict(append='current_hash')
                }

                if response['id'] == cfg.NODES-1:
                    # the last one receives the ring as well
                    response['ring'] = node.ring

                    # need different handling for broadcasting
                    data = { 'ring' : node.ring }
                    node.broadcast(data, cfg.GET_RING, 'POST', blacklist=[inet_address])
                    
                    cfg.CAN_DISTRIBUTE_WEALTH = True

                print('Served {} (gave it id {})'.format(inet_address, response['id']))

                return jsonify(response), 200

        # send 100 NBC to every node after network initialization
        @app.route(cfg.DISTRIBUTE_WEALTH, methods=['GET'])
        def distribute_wealth():
            if not cfg.CAN_DISTRIBUTE_WEALTH:
                return 'Distribution of wealth has been done already!\n', 200

            for inet_addr, wallet_addr in node.ring:
                if cfg.is_bootstrap(inet_addr):
                    continue
                node.create_transaction(wallet_addr, 100)

            cfg.CAN_DISTRIBUTE_WEALTH = False
            return 'Distribution of wealth completed successfully!\n', 200

        # bootstrap node serves as frontend, too
        app.run(host='0.0.0.0', port=port, threaded=True)

    else:
        node = SimpleNode(full_address)

        @app.route(cfg.GET_RING, methods=['POST'])
        def get_ring():
            node.ring = [tuple(n) for n in request.get_json()['ring']]
            # print('Ring:', node.ring)
            return 'Node {} received ring'.format(node.node_id), 200

        app.run(host=address, port=port, threaded=True)
