import requests

BOOTSTRAP_ADDRESS = '192.168.1.39:5000'

# DIFFICULTY and CAPACITY will be set at runtime
DIFFICULTY = None
CAPACITY = None

# NODES needed only by bootstrap node during network initialization
NODES = None

def is_bootstrap(address):
    return address == BOOTSTRAP_ADDRESS

CAN_DISTRIBUTE_WEALTH = False

# routes

GET_ID = '/init/id/get'
GET_RING = '/init/ring/get'
DISTRIBUTE_WEALTH = '/init/distribute/wealth'

NEW_TRANSACTION = '/transaction/new'

WALLET_BALANCE = '/wallet/balance'
