import requests

BOOTSTRAP_ADDRESS = '192.168.1.2:5000'

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

CREATE_TRANSACTION = '/transaction/create'
NEW_TRANSACTION = '/transaction/new'
NEW_BLOCK = '/block/new'

WALLET_BALANCE = '/wallet/balance'

POOL = '/pool'

BLOCKCHAIN = '/blockchain'
BLOCKCHAIN_LENGTH = '/blockchain/length'
BLOCKCHAIN_HASHES = '/blockchain/hashes'