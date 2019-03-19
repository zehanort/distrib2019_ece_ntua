from sys import argv
import requests
import cfg

addr = 'http://' + argv[1]
ring = requests.get(addr + '/ring')
ring = ring.json()

print('Ring:')
for r in ring:
    print(r)

while True:
    n, amount = list(map(int, input('spender> ').strip().split()))
    data = {
        'recipient_address' : ring[n][1],
        'amount' : int(amount)
    }
    r = requests.post(addr + cfg.CREATE_TRANSACTION, json=data)
