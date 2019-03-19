from threading import Thread
from sys import argv
import cfg
import requests

def usage():
    print('usage:', argv[0], '<nodes (5 or 10 only)>')
    exit(1)

def create_all_node_transactions(n, tests_dir, ring):
    with open(tests_dir + 'transactions' + str(n) + '.txt', 'r') as transactions:

        transaction = transactions.readline().strip().split()

        while transaction:
            # get transaction data from line of file
            recipient_node = transaction[0].lstrip('id')
            amount = int(transaction[1])

            # make the transaction
            data = {
                'recipient_address' : ring[n][1],
                'amount' : amount
            }
            requests.post('http://' + ring[n][0] + cfg.CREATE_TRANSACTION, json=data)

            # to the next one!
            transaction = transactions.readline().strip().split()

if __name__ == '__main__':
    if len(argv) < 2:
        usage()

    nodes = int(argv[1])

    if nodes != 5 and nodes != 10:
        usage()

    tests_dir = '../transactions/' + str(nodes) + 'nodes/'

    transaction_threads = []

    # get ring from bootstrap
    r = requests.get('http://' + cfg.BOOTSTRAP_ADDRESS + cfg.RING)
    ring = r.json()

    for n in range(nodes):
        transaction_threads.append(
            Thread(
                target=create_all_node_transactions,
                args=(n, tests_dir, ring)
            )
        )

    list(map(lambda t: t.start(), transaction_threads))
    list(map(lambda t: t.join(), transaction_threads))
    print('All transactions are done.')
