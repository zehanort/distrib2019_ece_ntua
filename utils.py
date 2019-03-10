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

class Utilizable(object):
	'''
		Instances of classes that inherit
		from Utilizable can be recursively
		{dict,JSON}-serialized.

		Instances of classes that inherit
		from Utilizable can be hashed based
		on their JSON serialization as defined
		by their .json() method.
		
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
		def helper(key):
			obj = getattr(self, key)
			if isinstance(obj, Utilizable):
				return obj.to_dict()
			else:
				return obj

		if append is None:
			append = []
		elif isinstance(append, str):
			append = [append]
		else:
			append = list(append)

		keys = list(type(self)._dict_attributes) + append
		values = (helper(a) for a in keys)
		return OrderedDict(zip(keys, values))

	def json(self, append=None, **kwargs):
		return json.dumps(self.to_dict(append=append), **kwargs).encode('utf8')

	def hash(self, as_hex=True, **kwargs):
		'''
			Generate SHA256 hash of python object

			as_hex : bool
					 False: return SHA object
					 True:  return hexdigest of hash

		'''
		obj_hash = SHA.new(self.json(**kwargs))

		if as_hex:
			return obj_hash.hexdigest()

		return obj_hash

class UtilizableList(list, Utilizable):
	def __getitem__(self, key):
		item = list.__getitem__(self, key)
		if isinstance(key, slice):
			return UtilizableList(item)
		return item
	def __add__(self, other):
		return UtilizableList(list.__add__(self,other))
	def __mul__(self, other):
		return UtilizableList(list.__mul__(self,other))

	def to_dict(self, **kwargs):
		return [obj.to_dict(**kwargs) for obj in self]

	def json(self, pointwise=True, **kwargs):
		if not pointwise:
			return super().json(**kwargs)
		return [obj.json(**kwargs) for obj in self]

	def hash(self, pointwise=True, **kwargs):
		if not pointwise:
			return super().hash(pointwise=False, **kwargs)
		return [obj.hash(**kwargs) for obj in self]
