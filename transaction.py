from collections import OrderedDict

import binascii
import json

import Crypto
import Crypto.Random
from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5

class Transaction(object):
    def __init__(self, **data):
        # args: inputs, sender_address, recipient_address, amount
        for key, value in data.items():
            setattr(self, key, value)
        
        self.signature = None
        
        self.transaction_id = self.hash()

    def __eq__(self, other):
        if isinstance(other, Transaction):
            return (self.transaction_id == other.transaction_id)
        return False

    def to_dict(self, include_signature=False):
        d = OrderedDict([
            ('sender_address', sender_address),
            ('recipient_address', recipient_address),
            ('amount', amount),
            ('inputs', inputs)
        ])

        if include_signature:
            d['signature'] = self.signature
        return d

    @property
    def utxo(self):
        """
        Returns tuple of dictionaries (sender change, receiver amount)
        """
        change = sum(i.amount for i in inputs) - self.amount
        
        sender_utxo = TransactionOuput(self.transaction_id, self.sender_address, change)
        recipient_utxo = TransactionOuput(self.transaction_id, self.recipient_address, self.amount)

        return {
            sender_utxo.id    : sender_utxo,
            recipient_utxo.id : recipient_utxo
        }

    def hash(self, as_hex=True, include_signature=True):
        transaction_data = json.dumps(self.to_dict(include_signature)).encode('utf8')
        transaction_hash = SHA.new(transaction_data)

        if as_hex:
            return transaction_hash.hexdigest()
        else:
            return transaction_hash
    
class TransactionOuput(Transaction):
    """Transaction output class"""
    def __init__(self, parent_transaction_id, recipient_address, amount):
        self.parent_transaction_id = parent_transaction_id
        self.recipient_address = recipient_address
        self.amount = amount
        self.id = self.hash()

    def to_dict(self):
        d = OrderedDict([
            ('parent_transaction_id', self.parent_transaction_id),
            ('recipient_address', self.recipient_address),
            ('amount', self.amount)
        ])
        return d