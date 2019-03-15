import binascii
import Crypto
import Crypto.Random
from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from utils import *

@dict_attributes('sender_address', 'recipient_address', 'amount', 'inputs')
class Transaction(Utilizable):
    def __init__(self, **data):
        # args: inputs, sender_address, recipient_address, amount
        self.__dict__.update(data)        
        self.transaction_id = self.hash()

    def __eq__(self, other):
        if isinstance(other, Transaction):
            return (self.transaction_id == other.transaction_id)
        return False

    @property
    def utxo(self):
        """
        Returns tuple of dictionaries (sender change, receiver amount)
        """
        change = sum(i.amount for i in self.inputs) - self.amount
        
        sender_utxo = TransactionOuput(self.transaction_id, self.sender_address, change)
        recipient_utxo = TransactionOuput(self.transaction_id, self.recipient_address, self.amount)

        return sender_utxo, recipient_utxo

# signature!?!?!?
@dict_attributes('parent_transaction_id', 'recipient_address', 'amount')
class TransactionOuput(Utilizable):
    """Transaction output class"""

    def __init__(self, parent_transaction_id, recipient_address, amount):
        self.parent_transaction_id = parent_transaction_id
        self.recipient_address = recipient_address
        self.amount = amount
        self.id = self.hash()
