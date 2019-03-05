import binascii

import Crypto
import Crypto.Random
from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5

import hashlib
import json
from time import time
from urllib.parse import urlparse
from uuid import uuid4

class Wallet:
	"""
	Wallet is a pair of public/private RSA keys
	"""
	def __init__(self):
		rand_gen = Crypto.Random.new().read
		self._private_key = RSA.generate(1024, rand_gen)

		self.public_key = self._private_key.publickey()

	@property
	def address(self):
		"""
		Returns address of wallet in ASCII form (as attribute)
		"""
		return binascii.hexlify(self._public_key.exportKey(format='DER')).decode('ascii')
   
    def sign_transaction(self, transaction):
        """
        Sign transaction with private key
        """
        signature_data = json.dumps(transaction.to_dict()).encode('utf8')
        signature_hash = SHA.new(signature_data)

        return binascii.hexlify(self._signer(signature_hash)).decode('ascii')
