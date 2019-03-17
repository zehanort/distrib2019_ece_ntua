from sys import argv
import requests
import cfg

addr = 'http://' + argv[1]
ring = requests.get(addr + '/ring')
ring = ring.json()

print(ring)
print('spender> ', end='')

while True:
    n, amount = list(map(int, input().strip().split()))
    print('spender> ', end='')
    data = {
        'recipient_address' : ring[n][1],
        'amount' : int(amount)
    }
    r = requests.post(addr + cfg.CREATE_TRANSACTION, json=data)
