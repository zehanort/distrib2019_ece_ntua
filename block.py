import datetime
from utils import *
from transaction import *

@dict_attributes('index', 'timestamp', 'previous_hash', 'transactions', 'nonce')
class Block(Utilizable):
	def __init__(self, **data):
		# args: index, previous_hash, transactions
		self.timestamp = str(datetime.datetime.now())
		self.__dict__.update(data)
		self.transactions = UtilizableList([Transaction(**t) for t in self.transactions])
		self.nonce = None
		self.current_hash = None
		
	def hash(self, set_own=True, **kwargs):
		block_hash = super().hash(**kwargs)

		if set_own:
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
		self.transactions = UtilizableList([genesis_transaction])
