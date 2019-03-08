import blockchain
import datetime

class Block(object): 
	def __init__(self, **data):
		# args: index, previous_hash, transactions
		self.timestamp = str(datetime.datetime.now())
		for key, value in data.items():
            setattr(self, key, value)

		self.nonce = None
		self.current_hash = None
		
	def to_dict(self):
		d = OrderedDict({
			'index' : self.index, 
			'timestamp' : self.timestamp,
			'previous_hash' : self.previous_hash,
			'transactions' : [t.to_dict() for t in self.transactions],
			'nonce' : self.nonce
		})

		return d

	def hash():
		block_data = json.dumps(self.to_dict()).encode('utf8')
		block_hash = SHA.new(transaction_data).hexdigest()

		self.current_hash = block_hash

		return self.current_hash

class GenesisBlock(Block):
	"""
	A class for the first block of the blockchain
	"""
	def __init__(self, genesis_transaction):
		super(GenesisBlock, self).__init__(index=0)
		self.nonce = 0
		self.previous_hash = 1
		self.transactions = [genesis_transaction]
