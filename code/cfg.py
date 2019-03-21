import requests

BOOTSTRAP_ADDRESS = '192.168.0.2:5000'

# DIFFICULTY and CAPACITY will be set at runtime
DIFFICULTY = None
CAPACITY = None

# NODES needed only by bootstrap node during network initialization
NODES = None

def is_bootstrap(address):
    return address == BOOTSTRAP_ADDRESS

CAN_DISTRIBUTE_WEALTH = False

# variables used for statistcs

start_time = None
end_time = 0
mean_mining_time = 0
n_mined_blocks = 0

# routes

GET_ID = '/init/id/get'
GET_RING = '/init/ring/get'
DISTRIBUTE_WEALTH = '/init/distribute/wealth'

CREATE_TRANSACTION = '/transaction/create'
NEW_TRANSACTION = '/transaction/new'
NEW_BLOCK = '/block/new'

WALLET_BALANCE = '/wallet/balance'

POOL = '/pool'
RING = '/ring'

BLOCKCHAIN = '/blockchain'
BLOCKCHAIN_LENGTH = '/blockchain/length'
BLOCKCHAIN_HASHES = '/blockchain/hashes'

# statistics

THROUGHPUT = '/stats/throughput'
BLOCK_TIME = '/stats/blocktime'

# needed by the site to initialize network

addresses = [
    '192.168.0.2',
    '192.168.0.3',
    '192.168.0.4',
    '192.168.0.5',
    '192.168.0.6'
]
start_port = 5000
key_dir = '~/.ssh/internal'
nbc_dir = '~/distrib2019_ece_ntua/code/'

# needed by the site to terminate network
TERMINATE = '/terminate'
