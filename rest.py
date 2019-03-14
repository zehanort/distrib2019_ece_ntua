from flask import Flask, jsonify, request, render_template
from flask_cors import CORS

import cfg
import requests
from node import *
from wallet import *
from block import *
from transaction import *

app = Flask(__name__)
CORS(app)

### ROUTES FOR ALL NBC NETWORK NODES ###

# run it once for every node

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
        bootstrap = Node(full_address, 0)
        
        ### ROUTES EXCLUSIVE TO BOOTSTRAP NODE ###

        # give ids to all other nodes
        @app.route(cfg.GET_ID, methods=['POST'])
        def assign_id_to_node():
            inet_address = request.form['inet_address']
            print('------->', inet_address)
            wallet_address = request.form['wallet_address']

            response = {
                'id' : bootstrap.register_node_to_ring(inet_address, wallet_address),
                'blockchain' : bootstrap.blockchain.to_dict()
            }

            print("------------------->", bootstrap.blockchain.to_dict())

            if response['id'] == cfg.NODES-1:
                # the last one receives the ring as well
                response['ring'] = bootstrap.ring
                # need different handling for broadcasting
                data = dict(bootstrap.ring)
                bootstrap.broadcast(data, cfg.GET_RING, 'POST', blacklist=[inet_address])
                print('INITIALIZATION COMPLETED SUCCESSFULLY!')
                print('ring is ->', data)

            print('served {} (gave it id {})'.format(inet_address, response['id']))

            return jsonify(response), 200

        # bootstrap node serves as frontend, too
        app.run(host='0.0.0.0', port=port, threaded=True, debug=True)

    else:
        node = Node(full_address)

        @app.route(cfg.GET_RING, methods=['POST'])
        def get_ring():
            node.ring = request.form['ring']
            return 'node {} received ring'.format(node.node_id), 200

        app.run(host=address, port=port, threaded=True, debug=True)
