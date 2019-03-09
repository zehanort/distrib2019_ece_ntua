import cfg

from block import *
from transaction import *
from wallet import *

class Node:
	def __init__(self, address, node_id=None):
		self.ring = []

		self.node_id = node_id
		self.blockchain = []
		self.last_block = None

		self.address = address
		self.wallet = Wallet()

		self.transaction_pool = []
		self.utxo = {}

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
			amount=100*NODES
		)
		_, genesis_utxo = genesis_transaction.utxo
		utxo.update(genesis_utxo)

		genesis_block = GenesisBlock(genesis_transaction)
		self.blockchain.append(genesis_block)
		# node_id is the index of the node in ring list
		self.ring = [(address, self.wallet.address)]

	def node_init(self):
		# request my id from bootstrap
		data = {'wallet_address': self.wallet.address}
		r = requests.post(cfg.BOOTSTRAP_ADDRESS + cfg.GET_ID, data=data)
		if r.status_code == 200:
			self.node_id = r.json()

	def register_node_to_ring(self, full_address, wallet_address):
		#add this node to the ring, only the bootstrap node can add a node to the ring after
		#checking his wallet and ip:port address
		#bootstrap node informs all other nodes and gives the request node an id and 100 NBCs

		for i, (full_addr, wallet_addr) in enumerate(self.ring):
			if full_addr == full_address or wallet_addr == wallet_address:
				return i
		
		self.ring.append((full_address, wallet_address))
		return next(node_ids)

	# Block Methods

	# def create_new_block(self):

	def broadcast_block():

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

		t = Transaction(
			inputs=inputs,
			sender_address=self.wallet.address,
			recipient_address=receiver,
			amount=amount
		)
		t.signature = self.wallet.sign_transaction(t.to_dict())
		self.validate_transaction(t)
		self.broadcast_transaction(t)

	def broadcast_transaction():

	def validate_transaction(self, incoming_transaction):
		sender_address = incoming_transaction.sender_address
		recipient_address = incoming_transaction.recipient_address
		amount = incoming_transaction.amount
		signature = incoming_transaction.signature
		inputs = incoming_transaction.inputs

		### step 1: validate signature
		public_key = RSA.importKey(binascii.unhexlify(sender_address))
		verifier = PKCS1_v1_5.new(public_key)
		transaction_hash = incoming_transaction.hash(to_hex=False)

		if not verifier.verify(transaction_hash, binascii.unhexlify(signature)):
			return False
		
		### step 2: validate inputs

		balance = 0 
		for i in inputs:
			if (not i in self.utxo) or (self.utxo[i].recipient_address != sender_address):
				return False
			else:
				balance += self.utxo[i].amount

		if balance < amount:
			return False

		# all inputs and the amount are valid, remove them from local utxo dict
		for i in inputs:
			self.utxo.pop(i)

		### step 3: calculate utxo
		self.utxo.update(incoming_transaction.utxo)

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
		balance = 0
		for utxo in self.utxo.values():
			if utxo.recipient_address == self.wallet.address:
				balance += utxo.amount
		return balance

	# Consensus Methods

	def validate_chain(self, chain):
		if not isinstance(chain[0], GenesisBlock):
			return False
		return all(self.validate_block(b) for b in chain[1:])

	def resolve_conflicts(self):
		#resolve correct chain


