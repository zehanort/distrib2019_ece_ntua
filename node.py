import cfg
import requests
from block import *
from transaction import *
from wallet import *
from utils import *

from collections import defaultdict

from threading import Lock

validate_transaction_lock = Lock()

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

            print(">>>", self.blockchain.to_dict(), type(self.blockchain[0]))

            self.validate_chain(self.blockchain)

            print(">>>", self.utxo)

            if 'ring' in received_data:
                self.ring = [tuple(i) for i in received_data['ring']]
                print('Ring:', self.ring)
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

    # def create_new_block(self):

    def mine_block(self):
        index = self.last_block.index + 1
        previous_hash = self.last_block.current_hash
        new_block = Block(
            index=index,
            previous_hash=previous_hash,
            transactions=self.transaction_pool[:cfg.CAPACITY]
        )

        nonce = 0
        while True:
            new_block.nonce = nonce
            new_block_hash = new_block.hash()

            if bin(int(new_block_hash, 16)).startswith('0b' + '0' * cfg.DIFFICULTY):
                return new_block

            nonce += 1

    def validate_block(self, incoming_block):
        previous_hash = incoming_block.previous_hash
        current_hash = incoming_block.current_hash

        block_hash = incoming_block.hash()

        if not ((block_hash == current_hash) and 
               (bin(int(current_hash, 16)).startswith('0b' + '0' * cfg.DIFFICULTY))):
            return False

        if not (previous_hash == self.last_block.current_hash):
            self.resolve_conflicts()

        return True

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
        self.validate_transaction(t)
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

        # print('\t[] VERIFIER ATTRIBUTES')
        # print('\t[] transaction dict:', incoming_transaction.to_dict())
        # print('\t[] hash:', transaction_hash.hexdigest())
        # print('\t[] signature:', signature)
        if not verifier.verify(transaction_hash, binascii.unhexlify(signature)):
            # print('GAMITHIKE TO VERIFY!!!!!!!!!!!!!!!!!')
            return False
        else:
            # print('ETREKSE TO VERIFY!!!!!!!!!!!!!!!!')
        
        ### step 2: validate inputs
        with validate_transaction_lock:
            balance = 0 
            for i in inputs:
                print("\t[SKATA]", i, self.utxo[sender_address])
                print("\t", [i.to_dict() for i in self.utxo[sender_address]])
                
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
        #if enough transactions mine
        if not self.validate_transaction(transaction):
            return

        self.transaction_pool.append(transaction)
        if len(self.transaction_pool) == cfg.CAPACITY:
            mined_block = self.mine_block()
            self.last_block = mined_block
            self.transaction_pool = []

            self.blockchain.append(mined_block)

            self.broadcast_block(mined_block)

    # Wallet Methods

    def wallet_balance(self):
        return sum(my_utxo.amount for my_utxo in self.utxo[self.wallet.address])

    # Consensus Methods

    def validate_chain(self, blockchain):
        if not isinstance(blockchain[0], GenesisBlock):
            return False

        tmp_utxo = defaultdict(list)

        genesis_block = blockchain[0]
        genesis_transaction = genesis_block.transactions[0]

        tmp_utxo[genesis_transaction.recipient_address].append(genesis_transaction.utxo[1])

        for block in blockchain[1:]:
            curr_utxo = self.validate_block(block)

            if not curr_utxo:
                return False

            sender_utxo, recipient_utxo = curr_utxo
            
            tmp_utxo[sender_utxo.recipient_address].append(sender_utxo)
            tmp_utxo[recipient_utxo.recipient_address].append(recipient_utxo)

        self.utxo = tmp_utxo

        return True
