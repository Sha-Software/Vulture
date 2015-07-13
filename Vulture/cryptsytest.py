from cryptsy.private import AuthenticatedSession
from cryptsy.common import CryptsyError
import urllib2
import json
from decimal import *

api = AuthenticatedSession("keyfile.txt")

balances = api.getinfo()
balances = balances['balances_available']

api.cancelallorders()

"""
marketData = urllib2.urlopen(urllib2.Request('http://pubapi.cryptsy.com/api.php?method=marketdatav2'))

all_market_data = json.loads(marketData.read())

all_market_data = all_market_data['return']['markets']

total = Decimal(0)

print 'before loop'
for markets in all_market_data.iterkeys():
	for coin in balances.iterkeys():
		if coin == all_market_data[markets]['primarycode']:
			try:
				api.createorder(all_market_data[markets]['marketid'], 'Sell', balances[coin], round(Decimal(all_market_data[markets]['lasttradeprice']), 9))
				print 'Selling', balances[coin], all_market_data[markets]['primarycode']
			except (CryptsyError, Exception) as e:
				print 'less than 0.00000010'
print total
"""

api.createorder(3, 'Buy', 0.00000001, 0.015)