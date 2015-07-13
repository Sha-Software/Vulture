from cryptsy.private import AuthenticatedSession
from decimal import *

api = AuthenticatedSession("keyfile.txt")

balances = api.getinfo()

orders = api.allmyorders()

print type(orders)

total_btc = Decimal(0)
total_ltc = Decimal(0)

for order in orders:
	print order


print 'BTC in account:', balances['BTC']
