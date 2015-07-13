from cryptsy.private import AuthenticatedSession
import cryptsy.public
import json
import urllib2
from decimal import *

api = AuthenticatedSession('keyfile.txt')

marketData = urllib2.urlopen(urllib2.Request('http://pubapi.cryptsy.com/api.php?method=marketdatav2'))

all_market_data = json.loads(marketData.read())

all_market_data = all_market_data['return']['markets']

total_btc_in_account = Decimal(0)
total_ltc_in_account = Decimal(0)

for market in all_market_data.iterkeys():
	print all_market_data[market]['marketid']
	orders = api.myorders(all_market_data[market]['marketid'])
	for order in orders:
		if order.type == 'Sell':
			if all_market_data[market]['secondarycode'] == 'LTC':
				total_ltc_in_account += Decimal(order.total)
			else:
				total_btc_in_account += Decimal(order.total)
				
print total_ltc_in_account
print total_btc_in_account