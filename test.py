from threading import Thread
from sys import argv

def usage():
    print('usage:', argv[0], '<nodes (5 or 10 only)>')
    exit(1)

def create_all_node_transactions(n, tests_dir):
    with open(tests_dir + 'transactions' + n + '.txt', 'r') as transactions:

        transaction = transactions.readline().strip().split()

        while transaction:
            # get transaction data from line of file
            recipient_node = transaction[0].lstrip('id')
            amount = transaction[1]

            # make the transaction (REPLACE PRINT BELOW TO ACTUALLY DO IT)
            print('[{}] sending {} NBCs to node {}'.format(n, amount, recipient_node))

            # to the next one!
            transaction = transactions.readline().strip().split()

if len(argv) < 2:
    usage()

nodes = int(argv[1])

if nodes != 5 and nodes != 10:
    usage()

tests_dir = '../transactions/' + str(nodes) + 'nodes/'

transaction_threads = []

for n in range(nodes):
    transaction_threads.append(
        Thread(
            target=create_all_node_transactions,
            args=(str(n), tests_dir)
        )
    )

list(map(lambda t: t.start(), transaction_threads))
list(map(lambda t: t.join(), transaction_threads))
print('All transactions are done.')
