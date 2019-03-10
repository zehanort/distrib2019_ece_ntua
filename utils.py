import json
from Crypto.Hash import SHA
from collections import OrderedDict

def dict_attributes(*attributes):
	'''
		Specify attributes to be included
		in order-preserving dict-serialized
		view of object
	'''

	def wrap(cls):
		cls._dict_attributes = attributes
		return cls
	return wrap

class Dictable(object):
	'''
		Instances of classes that inherit
		from Dictable can be recursively
		dict-serialized.
		
		Use dict_attributes decorator to
		specify attributes to be included
		
		Comments: Useful for JSON serialization 
	'''

	def to_dict(self, append=None):
		'''
			Serialize python object as dict

			append : str or iterable of str
					 Append attribute(s) not initially
					 registered with @dict_attributes
					 to result
		'''
		def recurse(obj):
			if isinstance(obj, Dictable):
				return obj.to_dict()

			# CODE STINK ALERT: breaks if obj is bytestring
			# 					or other funky iterable.
			# 					Probably OK though...

			if not isinstance(obj, str) and hasattr(type(obj), '__iter__'):
				return [recurse(o) for o in obj]
			return obj


		if append is None:
			append = []
		elif isinstance(append, str):
			append = [append]
		else:
			append = list(append)

		keys = list(type(self)._dict_attributes) + append
		values = (recurse(getattr(self, a)) for a in keys)
		return OrderedDict(zip(keys, values))

class JSONable(Dictable):
	'''
		Instances of classes that inherit
		from JSONable can be recursively
		JSON-serialized. They also inherit
		from Dictable for free!
	'''

	def json(self, append=None, **kwargs):
		return json.dumps(self.to_dict(append), **kwargs).encode('utf8')

class Hashable(JSONable):
	'''
		Instances of classes that inherit
		from Hashable can be hashed based
		on their JSON serialization as defined
		by their .json() method.
	'''

	def hash(self, as_hex=True, append=None):
		'''
			Generate SHA256 hash of python object

			as_hex : bool
					 False: return SHA object
					 True:  return hexdigest of hash

		'''
		obj_hash = SHA.new(self.json(append))

		if as_hex:
			return obj_hash.hexdigest()

		return obj_hash
