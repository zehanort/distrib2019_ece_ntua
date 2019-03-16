import datetime
from utils import *
from transaction import *

@dict_attributes('index', 'timestamp', 'previous_hash', 'transactions', 'nonce')
class Block(Utilizable):
    def __init__(self, **data):
        # args: index, previous_hash, transactions
        self.timestamp = str(datetime.datetime.now())
        self.__dict__.update(data)
        if 'transactions' in data and not isinstance(data['transactions'], UtilizableList):
            self.transactions = UtilizableList([Transaction(**t) for t in self.transactions])
        
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
        self.current_hash = self.hash()

    @classmethod
    def parse(cls, data):
        obj = cls(Transaction(**data['transactions'][0]))
        obj.index = data['index']
        obj.nonce = data['nonce']
        obj.timestamp = data['timestamp']
        obj.previous_hash = data['previous_hash']
        obj.current_hash = data['current_hash']

        return obj
