import requests

BOOTSTRAP_ADDRESS = '192.168.0.2:5000'

# DIFFICULTY and CAPACITY will be set at runtime
DIFFICULTY = None
CAPACITY = None

# NODES needed only by bootstrap node during network initialization
NODES = None

def is_bootstrap(address):
    return address == BOOTSTRAP_ADDRESS

# routes

GET_ID = '/init/id/get'
GET_RING = '/init/ring/get'

