import cfg
import requests
from block import *
from transaction import *
from wallet import *
from utils import *

from operator import itemgetter
from itertools import count, takewhile, accumulate
from collections import defaultdict
from copy import deepcopy
from time import time

from threading import Lock, Thread
from queue import Queue

validate_transaction_lock = Lock()
blockchain_lock = Lock()
add_transaction_lock = Lock()
mining_lock = Lock()

class Node(object):
    """
    Base node class, NOT MEANT to be used directly
    """
    def __init__(self, address):
        self.address = address
        self.wallet = Wallet()

        self.transaction_pool = UtilizableList()
        self.block_queue = Queue()

        # key: wallet address, value: list of utxo for key
        self.utxo = defaultdict(UtilizableList)

    #  Node Methods

    def broadcast(self, message, dest_url, method, blacklist=[]):
        if method not in ['POST', 'GET']:
            raise NotImplementedError('Method {} not supported'.format(method))

        recipients = (addr for addr, _ in self.ring if addr not in blacklist + [self.address])
        full_urls = ('http://' + addr + dest_url for addr in recipients)
        payload = {'json': message} if method == 'POST' else {}

        req = getattr(requests, method.lower())

        return [req(full_url, **payload) for full_url in full_urls]

    # Block Methods

    def mine_block(self):
        with mining_lock:
            if not len(self.transaction_pool) >= cfg.CAPACITY:
                return

            last_block = self.blockchain[-1]
            new_block = Block(
                index=last_block.index+1,
                previous_hash=last_block.current_hash,
                transactions=self.transaction_pool[:cfg.CAPACITY],
                nonce=0,
                local=True
            )

            # count mining time
            mining_start_time = time()

            new_block.hash(set_own=True)
            while not new_block.valid_proof():
                new_block.nonce += 1
                new_block.hash(set_own=True)

            # mining done
            mining_time = time() - mining_start_time
            cfg.n_mined_blocks += 1

            cfg.mean_mining_time = cfg.mean_mining_time * (cfg.n_mined_blocks - 1) + mining_time
            cfg.mean_mining_time /= cfg.n_mined_blocks

        self.block_queue.put(new_block)
        self.broadcast(new_block.to_dict(append='current_hash', append_rec='signature'), cfg.NEW_BLOCK, 'POST')
        self.resolve_block_queue()

    def validate_block(self, incoming_block, previous_hash):
        return  (
                    incoming_block.previous_hash == previous_hash and
                    incoming_block.valid_proof() and
                    incoming_block.current_hash == incoming_block.hash()
                )

    def resolve_block_queue(self):
        with mining_lock:
            while not self.block_queue.empty():
                incoming_block = self.block_queue.get()

                # is it the next block of our blockchain?
                if self.validate_block(incoming_block, self.blockchain[-1].current_hash):
                    for t in incoming_block.transactions:
                        self.validate_transaction(t)

                    with blockchain_lock:
                        self.blockchain.append(incoming_block)
                        # set end_time
                        cfg.end_time = time()
                    
                    self.fix_transaction_pool(validate=False)
                elif incoming_block.local:
                    continue
                elif self.resolve_conflicts():
                    # if resolve_conflicts is True, then at least a block was added
                    cfg.end_time = time()
                    
                    self.fix_transaction_pool(validate=True)

        self.mine_block()

    # Transaction Methods

    def create_transaction(self, receiver, amount):
        # we do not remove used utxos, this will be done
        # during transaction validation
        my_utxo = self.utxo[self.wallet.address]

        cumsum = accumulate(utxo.amount for utxo in my_utxo)
        cut = next((i for i, s in enumerate(cumsum, 1) if s >= amount), len(my_utxo))

        t = Transaction(
            inputs=UtilizableList(my_utxo[:cut]),
            sender_address=self.wallet.address,
            recipient_address=receiver,
            amount=amount
        )
        
        self.wallet.sign_transaction(t)

        Thread(target=self.add_transaction, args=(t,)).start()

        self.broadcast(t.to_dict(append='signature'), cfg.NEW_TRANSACTION, 'POST')

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
            if any(i not in self.utxo[sender_address] for i in inputs):
                return False

            balance = sum(i.amount for i in inputs)

            if balance < amount:
                return False

            # all inputs and the amount are valid, remove them from local utxo dict
            self.utxo[sender_address] = UtilizableList(i for i in self.utxo[sender_address] if i not in inputs)

            ### step 3: calculate utxo
            self.utxo[sender_address].append(incoming_transaction.utxo[0])
            self.utxo[recipient_address].append(incoming_transaction.utxo[1])

        return True

    def add_transaction(self, transaction):
        with add_transaction_lock:

            # start a timer for throughput
            if cfg.start_time is None:
                cfg.start_time = time()

            if not self.validate_transaction(transaction):
                return

            self.transaction_pool.append(transaction)

        self.mine_block()

    def calculate_utxo(self, blockchain):
        backup_utxo = deepcopy(self.utxo)
        self.utxo = defaultdict(UtilizableList)

        genesis_block = blockchain[0]
        genesis_transaction = genesis_block.transactions[0]

        self.utxo[genesis_transaction.recipient_address].append(genesis_transaction.utxo[1])

        if all(self.validate_transaction(t) for b in blockchain[1:] for t in b.transactions):
            return True

        self.utxo = backup_utxo
        return False

    # Wallet Methods

    def wallet_balance(self):
        return sum(my_utxo.amount for my_utxo in self.utxo[self.wallet.address])

    # Consensus Methods

    def validate_chain(self, chain):
        if not isinstance(chain[0], GenesisBlock):
            return False

        return all(self.validate_block(b, p.current_hash) for b, p in zip(chain[1:], chain))

    @property
    def blockchain_length(self):
        with blockchain_lock:
            return len(self.blockchain)

    def blockchain_diff(self, hashes):
        with blockchain_lock:
            my_hashes = [b.current_hash for b in self.blockchain]
            # diffs = (i for i, h1, h2 in zip(count(), my_hashes, hashes) if h1 != h2)
            # cut = next(diffs, len(my_hashes))

            # return self.blockchain[cut:].to_dict(append='current_hash', append_rec='signature')
            for i, (my_hash, other_hash) in enumerate(zip(my_hashes, hashes)):
                if my_hash != other_hash:
                    break

            return self.blockchain[i:].to_dict(append='current_hash', append_rec='signature')

    def resolve_conflicts(self):
        ### step 1: ask for blockchain length
        responses = self.broadcast(None, cfg.BLOCKCHAIN_LENGTH, 'GET')
        dominant_length, dominant_node = max([(r.json(), r.url) for r in responses], key=itemgetter(0))

        # do nothing if there is no clear winner
        if dominant_length <= len(self.blockchain):
            return False

        ### step 2: send list of blockchain hashes to dominant node
        dominant_node = dominant_node.rstrip(cfg.BLOCKCHAIN_LENGTH)
        blockchain_hashes = [b.current_hash for b in self.blockchain]
        r = requests.post(dominant_node + cfg.BLOCKCHAIN_HASHES, json=blockchain_hashes)

        ### step 3: get correct chain
        new_blocks = [Block(**b) for b in r.json()]
        cut = new_blocks[0].index
        tmp_blockchain = deepcopy(self.blockchain[:cut]) + new_blocks

        ### step 4: validate temp blockchain
        if not self.validate_chain(tmp_blockchain):
            return False

        ### step 5: calculate utxo and, if everything ok, update blockchain
        if not self.calculate_utxo(tmp_blockchain):
            return False

        # add transactions that would be purged by blockchain replacement
        my_transactions = [t for b in self.blockchain[cut:] for t in b.transactions]
        new_transactions = [t for b in new_blocks for t in b.transactions]
        with add_transaction_lock:
            self.transaction_pool += [t for t in my_transactions if t not in new_transactions]

        # replace blockchain
        with blockchain_lock:
            self.blockchain = tmp_blockchain

        return True

    def fix_transaction_pool(self, validate):
        blockchain_transactions = [t for b in self.blockchain for t in b.transactions]

        with add_transaction_lock:
            if not validate:
                self.transaction_pool = UtilizableList(
                    t for t in self.transaction_pool
                    if t not in blockchain_transactions
                )
            else:
                self.transaction_pool = UtilizableList(
                    t for t in self.transaction_pool
                    if t not in blockchain_transactions
                    and self.validate_transaction(t)
                )

class BootstrapNode(Node):
    """
    A special node that is responsible for the NBC network initialization
    (just a simple node after initialization is done)
    """
    def __init__(self, address):
        
        super(BootstrapNode, self).__init__(address)

        # bootstrap node ID is always 0
        self.node_id = 0
        self.node_ids = count(start=1)

        genesis_transaction = Transaction(
            inputs=UtilizableList(),
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

    def register_node_to_ring(self, full_address, wallet_address):
        #add this node to the ring, only the bootstrap node can add a node to the ring after
        #checking his wallet and ip:port address
        #bootstrap node informs all other nodes and gives the request node an id and 100 NBCs

        for i, (f, w) in enumerate(self.ring):
            if f == full_address or w == wallet_address:
                return i
        
        self.ring.append((full_address, wallet_address))
        return next(self.node_ids)

class SimpleNode(Node):
    """
    A simple node of the NBC network
    """
    def __init__(self, address):

        super(SimpleNode, self).__init__(address)

        # request my id from bootstrap
        data = {
            'inet_address'   : self.address,
            'wallet_address' : self.wallet.address
            }
        r = requests.post('http://' + cfg.BOOTSTRAP_ADDRESS + cfg.GET_ID, data=data)

        if r.status_code == requests.codes.ok:
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
