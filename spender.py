from sys import argv
import requests

addr = 'http://' + argv[1]
ring = requests.get(addr + '/ring')
ring = ring.json()

print('spender> ', end='')

while True:
    n, amount = input().strip().split()
    print('spender> ', end='')
    data = {
        'recipient_address' : ring[n][0],
        'amount' : int(amount)
    }
    r = requests.post(ring[n][1], json=data)
