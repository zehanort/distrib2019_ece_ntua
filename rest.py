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

@app.route(cfg.NEW_TRANSACTION, methods=['POST'])
def get_new_transaction():
    new_transaction = Transaction(**request.get_json())
    new_transaction.inputs = UtilizableList(
        [TransactionOuput(**i) for i in new_transaction.inputs]
    )

    # assign handling of incoming transaction to a new thread
    transaction_thread = Thread(
        target=node.add_transaction,
        args=(new_transaction,)
    )
    transaction_thread.start()
    return 'new transaction received\n', 200

@app.route(cfg.WALLET_BALANCE, methods=['GET'])
def report_wallet_balance():
    return jsonify(node.wallet_balance()), 200

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
    port = args.port
    full_address = address + ':' + str(port)

    # set global variables
    cfg.DIFFICULTY = args.difficulty
    cfg.CAPACITY = args.capacity

    if cfg.is_bootstrap(address + ':' + str(port)):
        cfg.NODES = args.nodes
        node = Node(full_address, 0)
        
        ### ROUTES EXCLUSIVE TO BOOTSTRAP NODE ###

        # give ids to all other nodes
        @app.route(cfg.GET_ID, methods=['POST'])
        def assign_id_to_node():
            inet_address = request.form['inet_address']
            wallet_address = request.form['wallet_address']

            with assign_id_lock:
                response = {
                    'id' : node.register_node_to_ring(inet_address, wallet_address),
                    'genesis_block' : node.blockchain[0].to_dict()
                }

            if response['id'] == cfg.NODES-1:
                # the last one receives the ring as well
                response['ring'] = node.ring

                # need different handling for broadcasting
                data = { 'ring' : node.ring }
                node.broadcast(data, cfg.GET_RING, 'POST', blacklist=[inet_address])
                
                cfg.CAN_DISTRIBUTE_WEALTH = True

            print('served {} (gave it id {})'.format(inet_address, response['id']))

            return jsonify(response), 200

        # send 100 NBC to every node after network initialization
        @app.route(cfg.DISTRIBUTE_WEALTH, methods=['GET'])
        def distribute_wealth():
            if not cfg.CAN_DISTRIBUTE_WEALTH:
                return 'Distribution of wealth has been done already!\n', 200

            else:
                for inet_addr, wallet_addr in node.ring:
                    if cfg.is_bootstrap(inet_addr):
                        continue
                    node.create_transaction(wallet_addr, 100)

                    from time import sleep
                    sleep(2)

                cfg.CAN_DISTRIBUTE_WEALTH = False
                return 'Distribution of wealth completed successfully!\n', 200

        # bootstrap node serves as frontend, too
        app.run(host='0.0.0.0', port=port, threaded=True)

    else:
        node = Node(full_address)

        @app.route(cfg.GET_RING, methods=['POST'])
        def get_ring():
            node.ring = [tuple(n) for n in request.get_json()['ring']]
            print('Ring:', node.ring)
            return 'node {} received ring'.format(node.node_id), 200

        app.run(host=address, port=port, threaded=True)
