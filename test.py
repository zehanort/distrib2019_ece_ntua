from block import *
from wallet import *
from transaction import *

genesis_transaction = Transaction(
			inputs=[],
			sender_address=0,
			recipient_address='vuliagmeni',
			amount=500
		)

wallet = Wallet()
