import cfg
import requests
from block import *
from transaction import *
from wallet import *
from utils import *

from collections import defaultdict
from copy import deepcopy

from threading import Lock
from queue import Queue

validate_transaction_lock = Lock()
blockchain_lock = Lock()
add_transaction_lock = Lock()
mining_lock = Lock()

class Node:
    def __init__(self, address, node_id=None):
        # ring: list of (full_address, wallet_address)
        self.ring = []

        self.node_id = node_id
        self.blockchain = None
        self.last_block = None

        self.address = address
        self.wallet = Wallet()

        self.transaction_pool = UtilizableList()
        self.block_queue = Queue()

        # key: wallet address, value: list of utxo for key
        self.utxo = defaultdict(list)

        # Am I the bootstrap node?
        if cfg.is_bootstrap(address):
            self.bootstrap_init()
        else:
            self.node_init()

    #  Node Methods

    def bootstrap_init(self):
        from itertools import count
        self.node_ids = count(start=1)

        genesis_transaction = Transaction(
            inputs=[],
            sender_address=0,
            recipient_address=self.wallet.address,
            amount=100*cfg.NODES
        )
        _, genesis_utxo = genesis_transaction.utxo
        self.utxo[self.wallet.address].append(genesis_utxo)

        genesis_block = GenesisBlock(genesis_transaction)
        self.blockchain = UtilizableList([genesis_block])
        # node_id is the index of the node in ring list
        self.ring = [(self.address, self.wallet.address)]

    def node_init(self):
        # request my id from bootstrap
        data = {
            'inet_address'   : self.address,
            'wallet_address' : self.wallet.address
            }
        r = requests.post('http://' + cfg.BOOTSTRAP_ADDRESS + cfg.GET_ID, data=data)

        if r.status_code == 200:
            received_data = r.json()
            
            self.node_id = received_data['id']
            self.blockchain = UtilizableList(
                [GenesisBlock.parse(received_data['genesis_block'])]
            )

            self.validate_chain(self.blockchain)
            self.calculate_utxo(self.blockchain)

            if 'ring' in received_data:
                self.ring = [tuple(i) for i in received_data['ring']]
        else:
            raise RuntimeError('Could not get ID from bootstrap node')

    def register_node_to_ring(self, full_address, wallet_address):
        #add this node to the ring, only the bootstrap node can add a node to the ring after
        #checking his wallet and ip:port address
        #bootstrap node informs all other nodes and gives the request node an id and 100 NBCs

        for i, (full_addr, wallet_addr) in enumerate(self.ring):
            if full_addr == full_address or wallet_addr == wallet_address:
                return i
        
        self.ring.append((full_address, wallet_address))
        return next(self.node_ids)

    def broadcast(self, message, dest_url, method, blacklist=[]):
        responses = []
        for (addr, _) in self.ring:
            if addr in blacklist or addr == self.address:
                continue
            if method == 'POST':
                responses.append(requests.post('http://' + addr + dest_url, json=message))
            elif method == 'GET':
                responses.append(requests.get('http://' + addr + dest_url))
            else:
                raise NotImplementedError('Method {} not supported'.format(method))
        return responses

    # Block Methods

    def mine_block(self):
        with mining_lock:
            if not len(self.transaction_pool) >= cfg.CAPACITY:
                print('I don\'t have many Transactions')
                return

            last_block = self.blockchain[-1]
            index = last_block.index + 1
            previous_hash = last_block.current_hash
            transactions = self.transaction_pool[:cfg.CAPACITY]

            new_block = Block(
                index=index,
                previous_hash=previous_hash,
                transactions=transactions
            )

            nonce = 0
            while True:
                new_block.nonce = nonce
                new_block_hash = new_block.hash()

                # print('>>>', bin(int(new_block_hash, 16)), nonce)

                if bin(int(new_block_hash, 16)).startswith('0b' + '1' * cfg.DIFFICULTY):
                    # print('[FOUND NONCE!] ->', new_block.to_dict(append='current_hash'))
                    break

                nonce += 1

        self.block_queue.put(new_block)
        self.broadcast(new_block.to_dict(append='current_hash', append_rec='signature'), cfg.NEW_BLOCK, 'POST')
        self.resolve_block_queue()

    def validate_block(self, incoming_block, previous_hash):
        current_hash = incoming_block.current_hash
        block_hash = incoming_block.hash(set_own=False)

        if not ((block_hash == current_hash) and 
               (bin(int(current_hash, 16)).startswith('0b' + '1' * cfg.DIFFICULTY))):
            return False

        if not (previous_hash == incoming_block.previous_hash):
            return False

        return True

    def resolve_block_queue(self):
        with mining_lock:
            while not self.block_queue.empty():
                incoming_block = self.block_queue.get()

                print('>> Incoming_block hash from queue:', incoming_block.current_hash, incoming_block.previous_hash)
                # is it the next block of our blockchain?

                self.print_chain()
                if self.validate_block(incoming_block, self.blockchain[-1].current_hash):
                    for t in incoming_block.transactions:
                        self.validate_transaction(t)

                    print('\t[**] New valid block from queue')
                    with blockchain_lock:
                        self.blockchain.append(incoming_block)
                else:
                    print('\t[!!] Error occcured: let\'s run resolve_conflicts')
                    self.resolve_conflicts()

                self.fix_transaction_pool()

        self.mine_block()

    # Transaction Methods

    def create_transaction(self, receiver, amount):
        #remember to broadcast it

        inputs = UtilizableList([])
        unspent_amount = 0

        # we do not remove used utxos, this will be done
        # during transaction validation
        for my_utxo in self.utxo[self.wallet.address]:
            unspent_amount += my_utxo.amount
            inputs.append(my_utxo)
            if unspent_amount >= amount:
                break

        t = Transaction(
            inputs=inputs,
            sender_address=self.wallet.address,
            recipient_address=receiver,
            amount=amount
        )
        
        self.wallet.sign_transaction(t)
        self.broadcast(t.to_dict(append='signature'), cfg.NEW_TRANSACTION, 'POST')
        self.add_transaction(t)

    def validate_transaction(self, incoming_transaction):
        sender_address = incoming_transaction.sender_address
        recipient_address = incoming_transaction.recipient_address
        amount = incoming_transaction.amount
        signature = incoming_transaction.signature
        inputs = incoming_transaction.inputs

        ### step 1: validate signature
        public_key = RSA.importKey(binascii.unhexlify(sender_address))
        verifier = PKCS1_v1_5.new(public_key)
        transaction_hash = incoming_transaction.hash(as_hex=False)

        if not verifier.verify(transaction_hash, binascii.unhexlify(signature)):
            return False

        ### step 2: validate inputs
        with validate_transaction_lock:
            balance = 0 
            for i in inputs:
                if not i in self.utxo[sender_address]:
                    print('eskasa edw')
                    return False
                else:
                    balance += i.amount

            if balance < amount:
                print('eskasa edw omws')
                return False

            # all inputs and the amount are valid, remove them from local utxo dict
            self.utxo[sender_address] = [i for i in self.utxo[sender_address] if i not in inputs]

            ### step 3: calculate utxo
            self.utxo[sender_address].append(incoming_transaction.utxo[0])
            self.utxo[recipient_address].append(incoming_transaction.utxo[1])

        return True

    def add_transaction(self, transaction):
        with add_transaction_lock:
            if not self.validate_transaction(transaction):
                print('Couldn\'t validate transaction')
                return

            self.transaction_pool.append(transaction)

        self.mine_block()

    def calculate_utxo(self, blockchain):
        backup_utxo = deepcopy(self.utxo)
        self.utxo = defaultdict(list)

        genesis_block = blockchain[0]
        genesis_transaction = genesis_block.transactions[0]

        self.utxo[genesis_transaction.recipient_address].append(genesis_transaction.utxo[1])

        for block in blockchain[1:]:
            for t in block.transactions:
                if not self.validate_transaction(t):
                    self.utxo = backup_utxo
                    return False

        return True

    def print_chain(self):
        print('GenesisBlock ->', end='')
        for b in self.blockchain:
            print(b.current_hash, '->', end='')

    # Wallet Methods

    def wallet_balance(self):
        return sum(my_utxo.amount for my_utxo in self.utxo[self.wallet.address])

    # Consensus Methods

    def validate_chain(self, blockchain):
        if not isinstance(blockchain[0], GenesisBlock):
            return False

        if not all(self.validate_block(block, blockchain[i].current_hash) 
                                       for i, block in enumerate(blockchain[1:])):
            return False

        return True

    @property
    def blockchain_length(self):
        with blockchain_lock:
            return len(self.blockchain)

    def blockchain_diff(self, hashes):
        with blockchain_lock:
            my_hashes = [b.current_hash for b in self.blockchain]
            for i, (my_hash, other_hash) in enumerate(zip(my_hashes, hashes)):
                if my_hash != other_hash:
                    break

            return self.blockchain[i:].to_dict(append='current_hash', append_rec='signature')

    def resolve_conflicts(self):
        ### step 1: ask for blockchain length
        responses = self.broadcast(None, cfg.BLOCKCHAIN_LENGTH, 'GET')
        length = len(self.blockchain)
        dominant_node = None

        for r in responses:
            curr_length = r.json()

            if curr_length > length:
                length = curr_length
                dominant_node = r.url

        if dominant_node is None:
            return False

        ### step 2: send list of blockchain hashes to dominant node
        dominant_node = dominant_node.rstrip(cfg.BLOCKCHAIN_LENGTH)
        blockchain_hashes = [b.current_hash for b in self.blockchain]
        r = requests.post(dominant_node + cfg.BLOCKCHAIN_HASHES, json=blockchain_hashes)

        ### step 3: get correct chain
        new_blocks = UtilizableList([Block(**b) for b in r.json()])
        cut = new_blocks[0].index
        tmp_blockchain = deepcopy(self.blockchain[:cut]) + new_blocks

        ### step 4: validate temp blockchain
        if not self.validate_chain(tmp_blockchain):
            return False

        ### step 5: calculate utxo and, if everything ok, update blockchain
        if self.calculate_utxo(tmp_blockchain):
            # add transactions that would be purged by blockchain replacement
            my_transactions = UtilizableList()
            for b in self.blockchain[cut:]:
                my_transactions += b.transactions

            new_transactions = UtilizableList()
            for b in new_blocks:
                new_transactions += b.transactions

            # new_transactions = set(new_transactions)
            diff = UtilizableList(
                [t for t in my_transactions if t not in new_transactions]
            )

            with add_transaction_lock:
                self.transaction_pool += diff

            # replace blockchain
            with blockchain_lock:
                self.blockchain = tmp_blockchain

            return True

        return False

    def fix_transaction_pool(self):
        print('AAAAAAAA:', self.transaction_pool.to_dict())
        blockchain_transactions = []
        for b in self.blockchain:
            blockchain_transactions += b.transactions
        # blockchain_transactions = set(blockchain_transactions)

        with add_transaction_lock:
            self.transaction_pool = UtilizableList([
                t for t in self.transaction_pool
                if t not in blockchain_transactions and self.validate_transaction(t)
            ])
        print('BBBBBBBB:', self.transaction_pool.to_dict())
