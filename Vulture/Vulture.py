import urllib2
import json
from datetime import datetime, timedelta
from operator import itemgetter
from cryptsy.private import AuthenticatedSession
from cryptsy.common import CryptsyError
import collections
from decimal import *
import time

class InsufficientOrder(Exception):
	def __init__(self, message):
		self.message = message

"""
Function #1
-----------
"""
def gather_market_data_private(api, all_market_data):
	get_market_data = api.getmarkets()
	for market in get_market_data:
		all_market_data[market['label']]['marketid'] = market['marketid']
		all_market_data[market['label']]['label'] = market['label']
		all_market_data[market['label']]['lasttradeprice'] = market['last_trade']
		all_market_data[market['label']]['volume'] = market['current_volume']
		all_market_data[market['label']]['primarycode'] = market['primary_currency_code']
		all_market_data[market['label']]['primaryname'] = market['primary_currency_name']
		all_market_data[market['label']]['secondarycode'] = market['secondary_currency_code']
		all_market_data[market['label']]['secondaryname'] = market['secondary_currency_name']		
		all_market_data[market['label']]['daily_high'] = market['high_trade']
		all_market_data[market['label']]['daily_low'] = market['low_trade']

		order_data = api.markertorders(market['marketid'])

		for order_type in order_data.iterkeys():
			all_market_data[market['label']][order_data[order_type]] = list()
			for order in order_type.iterkeys():
				all_market_data[market['label']][order_data[order_type]].append({'price':order.price, 'quantity':order.quantity, 'total':order.total})

		order_data = api.markettrades(market['marketid'])

		for order in order_data:
			all_market_data[market['label']]['recenttrades'] = list()
			all_market_data[market['label']]['recenttrades'].append({'time':order.time_created, 'type':order.type, 'price':order.price, 'quantity':order.quantity, 'total':order.total})

	return all_market_data

"""
Function #2
-----------
"""
def gather_extra_market_data(api, all_market_data):
	print 'switching'
	all_market_data = collections.OrderedDict(all_market_data['return']['markets'])
	
	extra_market_data = api.getmarkets()

	"""
	Adding Highest Trade in 24 Hours, Lowest Trade in 24 Hours to the data for each coin
	"""
	for coin_market in extra_market_data:
		all_market_data[coin_market['label']]['daily_high'] = coin_market['high_trade']
		all_market_data[coin_market['label']]['daily_low'] = coin_market['low_trade']

	return all_market_data

"""
Function #3
-----------
"""
def trend_determination(coin_trade_data, price_two, last_n_trades):
	coin_loop_count = 0
	prival_dict = dict({'last_n_volume':Decimal(0), 'average_price':Decimal(0), 'trend_count':Decimal(0)})
	"""
	Trend determination:
	compares each price to the price before it if higher then n-1 +1 if lower than n-1 -1
	"""
	for single_trade in coin_trade_data:
		if coin_loop_count < last_n_trades:
			price_one = price_two
			price_two = Decimal(single_trade['price'])
			prival_dict['last_n_volume'] += Decimal(single_trade['quantity'])
			prival_dict['average_price'] += Decimal(price_two)
			if price_one > price_two:
				prival_dict['trend_count'] += 1
			elif price_one < price_two:
				prival_dict['trend_count'] -= 1
			coin_loop_count += 1
		else:
			break
	#print 'Number is: ', prival_dict['trend_count']

	"""
	Calculating average_price
	"""
	prival_dict['average_price'] /= coin_loop_count
	prival_dict['average_price']  = round(prival_dict['average_price'], 9)

	return prival_dict
"""
Function #4
-----------
"""
def cleanup_orders(api, stored_orders, runtimelog):

	balances = api.getinfo()

	balances = balances['balances_available']

	runtimelog.write('\nCleanup Orders:\n----------\n')

	for orders in stored_orders:
		try:
			runtimelog.write('Selling' + str(orders['amount']) + orders['primary'] + 'for a price of' + str(orders['price']) + 'on the' + orders['secondary'] + 'market\n')
			print 'Selling', orders['amount'], orders['primary'], 'for a price of', orders['price'], 'on the', orders['secondary'], 'market'
			api.createorder(orders['id'], 'Sell', orders['amount'], orders['price'])
			stored_orders.remove(orders)
		except CryptsyError, e:
			runtimelog.write('The sell order did not execute as there was only ' + str(balances[orders['primary']]) + orders['primary'] + ' in the account\n')
			print 'The sell order did not execute as there was only', balances[orders['primary']], orders['primary'], 'in the account'
			"""
			orders['loop_count'] += 1
			if orders['loop_count'] == 5:
				stored_orders.remove(orders)
			"""
	return stored_orders
"""
Function #5
-----------
"""
def cleanup_dust(api, runtimelog):
	
	def cleanup_trade(api, runtimelog, balances, market):
		try:
			if Decimal(balances[market['primary_currency_code']]) * Decimal(market['last_trade']) >= Decimal(0.00000010) and market['primary_currency_code'] != 'LTC':
				api.createorder(market['marketid'], 'Sell', balances[market['primary_currency_code']], market['last_trade'])
				runtimelog.write('Selling (dust) ' + str(balances[market['primary_currency_code']]) + ' ' + market['primary_currency_code'] + ' at current trade price\n')
				balances['primary_currency_code'] = 0
		except CryptsyError as e:
			print e
			runtimelog.write('Something went wrong cleaning up dust\nINFO:\n' + 'Selling: ' + str(balances[market['primary_currency_code']]) + ' ' + market['primary_currency_code'] + '\nPrice: ' + str(market['last_trade']) + '\nTotal of: ' + str(round(Decimal(market['last_trade']) * Decimal(balances[market['primary_currency_code']]), 9)))
		except KeyError as e:
			print e
		return balances

	markets = api.getmarkets()
	balances = api.getinfo()['balances_available']

	for market in markets:
		if market['secondary_currency_code'] == 'BTC':
			balances = cleanup_trade(api, runtimelog, balances, market)
	for market in markets:
		balances = cleanup_trade(api, runtimelog, balances, market)
"""
Function #6
-----------
"""
def maketrades(api, tracking, order_amount, order_price, plus_percentage, market_id, runtimelog):
	if (order_amount * (order_price * plus_percentage)) >= Decimal(0.0000001):
		print 'Buying', order_amount, 'for the price of', order_price
		runtimelog.write('Buying ' + str(order_amount) + ' for the price of ' + str(order_price) + '\n')
		tracking['orderid'] = api.createorder(market_id, 'Buy', round(order_amount, 9), round(order_price, 9))
		tracking['total_bought'] += order_amount
		tracking['total_spent'] += api.calculatefees('Sell', order_amount, order_price)['net']		
		api.createorder(market_id, 'Sell', round(order_amount, 9), round(order_price * plus_percentage, 9))
		print 'Selling ', order_amount, ' for the price of ', round(order_price * plus_percentage, 9)
		runtimelog.write('Selling ' + str(order_amount) + ' or the price of ' + str(round(order_price * plus_percentage, 9)) + '\n')
	else:
		raise InsufficientOrder('Order cannot be less than 0.00000010')
	return tracking

"""
last_n_trades = the number of last trades to calculate the trend from
plus_percentage = by how much percent to increase the buy orders when selling
percent_daily_volume_order = the percent of the DTV used to determine if there is a sell wall and list below that
percent_daily_volume_total = the percent of the DTV to limit total orders of coins
max_btc_to_trade_order = maximum amount of btc to spend on each coin
percent_of_variation = the percentage of the variation between current and highest used to determine max sell price
outlier_percentage = the percentage difference to ignore an outlieing data point
"""

cleanup = list()
algo_count = 0

while True:

	runtimelog = open('logs/' + time.strftime("%Y-%m-%d") + '.txt', 'a')

	try:
		conf_open  = open('config.conf', 'r')
		conf_file = json.loads(conf_open.read())
		conf_open.close()

		last_n_trades = int(conf_file['last_n_trades'])
		plus_percentage = Decimal(conf_file['plus_percentage'])
		percent_daily_volume_order = Decimal(conf_file['percent_daily_volume_order'])
		percent_daily_volume_total = Decimal(conf_file['percent_daily_volume_total'])
		max_btc_to_trade_order = Decimal(conf_file['max_btc_to_trade_order'])
		max_ltc_to_trade_order = Decimal(conf_file['max_ltc_to_trade_order'])
		percent_of_variation = Decimal(conf_file['percent_of_variation'])
		outlier_percentage = Decimal(conf_file['outlier_percent'])
		loops_to_clean_dust = int(conf_file['loops_to_clean_dust'])

		max_ltc_to_trade_total = Decimal(0)
		max_btc_to_trade_total = Decimal(0)
		final_total_btc = Decimal(0)
		final_total_ltc = Decimal(0)
		total_funds_spent = Decimal(0)
		max_funds_to_spend = Decimal(0)

		api = AuthenticatedSession('keyfile.txt')

		marketData = urllib2.urlopen(urllib2.Request('http://pubapi.cryptsy.com/api.php?method=marketdatav2'))

		all_market_data = json.loads(marketData.read())

		daily_volume_market = {'BTC':Decimal(0), 'LTC':Decimal(0), 'USD':Decimal(0)}

		all_market_data = gather_extra_market_data(api, all_market_data)

		"""
		Looping through all the market data

		coin_market = each of the trading pairs ie. LTC/BTC

		all_market_data = results from cryptsy API, only data

		First Loop through gathers data to allocate funds to each coin for investing
		"""
		for coin_market in all_market_data:

			if all_market_data[coin_market]['secondarycode'] != 'USD':
				all_market_data[coin_market]['prival_dict'] = dict()
				"""
				Extracting just recent trade data to new coin_trade_data
				"""
				coin_trade_data = all_market_data[coin_market]['recenttrades']
				
				if type(coin_trade_data) == list:
					"""
					Initializing Variables:		
					price_one = the first price to be used in the trend determination
					prival_dict:
						-'last_n_volume' = volume of the last n trades
						-'average_price' = average price over last n trades
						-'trend_count' = trend determination number
					"""		
					price_two = Decimal(all_market_data[coin_market]['lasttradeprice'])
					all_market_data[coin_market]['prival_dict'] = trend_determination(coin_trade_data, price_two, last_n_trades)
					if all_market_data[coin_market]['prival_dict']['trend_count'] > 0:
						daily_volume_market[all_market_data[coin_market]['secondarycode']] += Decimal(all_market_data[coin_market]['volume']) * Decimal(all_market_data[coin_market]['prival_dict']['average_price'])

		balances = api.getinfo()
		balances = balances['balances_available']
		currency_available = {'BTC':Decimal(balances['BTC']), 'LTC':Decimal(balances['LTC']), 'USD':Decimal(balances['USD'])}
		print 'BTC available', currency_available['BTC']
		print 'LTC available', currency_available['LTC']

		runtimelog.write('BTC available:' + str(currency_available['BTC']) + '\nLTC available:' + str(currency_available['LTC']))
		"""
		if algo_count == loops_to_clean_dust:
			cleanup_dust(api, runtimelog)
			algo_count = 0
		algo_count += 1
		"""
		for coin_market in all_market_data:

			if all_market_data[coin_market]['secondarycode'] == 'LTC':
				total_funds_spent = final_total_ltc
				max_funds_to_spend = currency_available['LTC']
			elif all_market_data[coin_market]['secondarycode'] == 'BTC':
				total_funds_spent = final_total_btc
				max_funds_to_spend = currency_available['BTC']

			if all_market_data[coin_market]['secondarycode'] != 'USD':
				"""
				Initializing Variables:
				currency_symbol = the primary coins symbol (ie. LTC, FST, GLD etc)
				market_symbol  = the secondary coins symbol (market symbol, ie. BTC, LTC, USD)
				"""
				currency_symbol = all_market_data[coin_market]['primarycode']
				market_symbol = all_market_data[coin_market]['secondarycode']
				last_trade_price = Decimal(all_market_data[coin_market]['lasttradeprice'])

				"""
				Cases if coin is trending up, down or not at all
				"""
				if all_market_data[coin_market]['prival_dict']['trend_count'] > 0:

					"""
					Initializing:
					currency_name = Name of the coin being traded 
					market_name = Name of the market the coin is being traded on
					daily_volume = Daily volume in respective coin 
					market_id = ID of the market
					sell_order_data = list of open sell orders
					daily_high = local variable of the 24 hour daily high value
					"""
					currency_name = all_market_data[coin_market]['primaryname']		
					market_name = all_market_data[coin_market]['secondaryname']
					daily_volume = Decimal(all_market_data[coin_market]['volume'])
					market_id = all_market_data[coin_market]['marketid']
					daily_high = Decimal(all_market_data[coin_market]['daily_high'])
					sell_order_data = all_market_data[coin_market]['sellorders']
					tracking = {'total_spent':Decimal(0), 'total_bought':Decimal(0)}
					
					total_quantity_open = Decimal(0)
					maximum_sell_price = (daily_high - last_trade_price) * percent_of_variation + last_trade_price
					maximum_sell_volume_order = round(Decimal(daily_volume) * percent_daily_volume_order, 9)

					print '--------------'
					print currency_symbol
					print '--------------'
					runtimelog.write('\n--------------\n' + str(currency_symbol) + '\n--------------\n')

					"""
					Grabbing Balances in account
					"""
					open_orders = api.myorders(market_id)		
					
					"""
					Calculating if the quantity of open orders is less than n\% of the DTV
					"""
					#print 'GRABBING CURRENT ORDER INFO'
					for orders in open_orders:
						if orders.type == 'Sell':
							#print 'TOTAL QUANTITY OPEN', total_quantity_open
							#print 'ORDER QUANTITY', orders.quantity
							total_quantity_open += Decimal(orders.quantity)
							#print 'ORDER PRICE', orders.price
							#print 'MAXIMUM SELL PRICE', maximum_sell_price
							if Decimal(orders.price) < maximum_sell_price:
								#print 'Switching maximum price of ', maximum_sell_price, 'to', Decimal(orders.price)
								maximum_sell_price = Decimal(orders.price)
						elif orders.type == 'Buy':
							#cancel open orders should only be buying orders that are open
							pass

					#print '-CURRENT OPEN QUANTITY', total_quantity_open
					#print '-DAILY VOLUME', daily_volume
					maximum_sell_volume_total = daily_volume * percent_daily_volume_total - total_quantity_open
					#print 'maximum after editing', maximum_sell_volume_total

					if market_symbol == 'BTC':
						max_coin_to_trade_order = max_btc_to_trade_order
					elif market_symbol == 'LTC':
						max_coin_to_trade_order = max_ltc_to_trade_order
					"""
					#max_coin_to_trade_order =  (all_market_data[coin_market]['volume'] / daily_volume_market[market_symbol]) * currency_available[market_symbol]
					print 'The total volume of the coin in ', market_symbol, 'is', all_market_data[coin_market]['volume']
					print 'The total daily volume of',  market_symbol, 'is', daily_volume_market[market_symbol]
					print 'The amount of', market_symbol, 'left is', currency_available[market_symbol]
					"""
					"""
					New highest price to resell at
					maximum_sell_price = Calculates the variance between current trade price and highest trade price, take a percetage of that
					"""			

					for sellorder in sell_order_data:
						order_price = Decimal(sellorder['price'])
						order_quantity = Decimal(sellorder['quantity'])
						order_total = Decimal(sellorder['total'])
						#print 'order_price = ', order_price, ', order_quantity = ', order_quantity, ', order_total', order_total
						"""
						Limits:
						1. the price to resell the order at +x% is not higher than the determine maximum sell price
						2. the quantity of the order does not surpass the determined maximum sell order (in terms of amount, ie. sell wall)
						3. the total quantity of coins bought does not exceed the outstanding difference between determined total sell volume and current open sell orders quantity
						4. total amount of BTC spent does not exceed set maxmimum BTC to spend on each coin
						"""
						if order_price * plus_percentage <= maximum_sell_price and order_quantity <= maximum_sell_volume_order and tracking['total_bought'] < maximum_sell_volume_total and tracking['total_spent'] < max_coin_to_trade_order and total_funds_spent < max_funds_to_spend:
							"""
							if the next order up would exceed the maximum sell volume total than only buy and resell a portion of it
							"""
							try:	
								if tracking['total_spent'] + order_total > max_coin_to_trade_order:
									order_quantity = Decimal((max_coin_to_trade_order - tracking['total_spent']) * order_price)
									tracking = maketrades(api, tracking, order_quantity, order_price, plus_percentage, market_id, runtimelog)
								else:
									tracking = maketrades(api, tracking, order_quantity, order_price, plus_percentage, market_id, runtimelog)
							except CryptsyError as e:
								runtimelog.write(currency_symbol + '/' + market_symbol + '\nTrade did not execute adding trade to cleanup dictionary with values:\n\tMarket ID: ' + str(market_id) + '\n\tPrice: ' + str(round(order_price * plus_percentage, 9)) + '\n\tAmount: ' + str(round(order_quantity, 9)))
								cleanup.append({'id':market_id, 'price':round(order_price * plus_percentage, 9), 'amount':order_quantity, 'primary':currency_symbol, 'secondary':market_symbol, 'loop_count':0})	
							except InsufficientOrder as e:
								runtimelog.write(e.message + '\nTotal amount of funds exceeded max allowed')
								print e.message
								print '\tTotal amount of funds exceeded max allowed'
								break
							
						elif order_price * plus_percentage > maximum_sell_price:
							runtimelog.write('\tThe order price of ' + str(order_price) + ' plus the percentage increase (' + str(round(order_price * plus_percentage, 9)) + ' was > the maximum sell price of ' + str(round(maximum_sell_price, 9)))
							print '\tThe order price of ', order_price, 'plus the percentage increase (', round(order_price * plus_percentage, 9), 'was > the maximum sell price of', round(maximum_sell_price, 9)
							break
						elif order_quantity > maximum_sell_volume_order:
							runtimelog.write('\tThere was a sell wall of ' + str(order_quantity) + ' at a price of ' + str(order_price))
							print '\tThere was a sell wall of ', order_quantity, ' at a price of ', order_price
							break
						elif tracking['total_bought'] >= maximum_sell_volume_total:
							runtimelog.write('\tThe total bought is greater than or equal to the set maximum to buy\n\t\tTotal Bought: ' + str(tracking['total_bought']) + '\n\t\tMax To Buy: ' + str(maximum_sell_volume_total))
							print '\tThe total bought is greater than or equal to the set maximum to buy'
							print '\t\tTotal Bought:', tracking['total_bought']
							print '\t\tMax To Buy:', maximum_sell_volume_total
							break
						elif tracking['total_spent'] >= max_coin_to_trade_order:
							runtimelog.write('\tThe total BTC spent is greater than or equal to the set maximum to spend on each coin')
							print '\tThe total BTC spent is greater than or equal to the set maximum to spend on each coin'
							break
						elif total_funds_spent >= max_funds_to_spend:
							runtimelog.write('\tYou have used up all your funds in the account! Not including orders that have been sold since then')
							print '\tYou have used up all your funds in the account! Not including orders that have been sold since then'
							break

					if market_symbol =='BTC':
						final_total_btc += tracking['total_spent']
					elif market_symbol == 'LTC':
						final_total_ltc += tracking['total_spent']
						runtimelog.write('\nBought a total of ' + str(tracking['total_spent']) + ' ' + market_symbol + ' worth of ' + currency_symbol)
					print 'Bought a total of ', tracking['total_spent'], market_symbol, 'worth of', currency_symbol

				elif all_market_data[coin_market]['prival_dict']['trend_count'] < 0:
					"""
					print currency_symbol, ' is on an downward trend'
					print 'On the: ', market_symbol
					print 'Average Price Over Past', last_n_trades, 'Trades: ', all_market_data[coin_market]['prival_dict']['average_price'] 
					print 'Last Trade Price: ', last_trade_price
					print '---\n'
					"""
				else:
					"""
					print currency_symbol, ' is not on a trend'
					print 'On the: ', market_symbol
					print 'Average Price Over Past 50 Trades: ', all_market_data[coin_market]['prival_dict']['average_price']
					print 'Last Trade Price: ', last_trade_price
					print '---\n'
					"""	
		cleanup = cleanup_orders(api, cleanup, runtimelog)

		runtimelog.write('----\n----\nTotal amount of BTC spent on all orders: ' + str(round(final_total_btc, 9)) + '\nTotal amount of BTC made from a 2% increase: ' + str(round(final_total_btc * plus_percentage, 9)) + '\nTotal amount of LTC spent on all orders: ' + str(round(final_total_ltc, 9)) + '\nTotal amount of LTC made from a 2% increase: ' + str(round(final_total_ltc * plus_percentage, 9)) + '\n----\n----')
		print '----'
		print '----'
		print 'Total amount of BTC spent on all orders: ', round(final_total_btc, 9)
		print 'Total amount of BTC made from a 2% increase:', round(final_total_btc * plus_percentage, 9)
		print 'Total amount of LTC spent on all orders: ', round(final_total_ltc, 9)
		print 'Total amount of LTC made from a 2% increase: ', round(final_total_ltc * plus_percentage, 9)
		print '----'
		print '----'

		runtimelog.close()
	except Exception as e:
		print 'Something went wrong'
		print e
		print e.args
		runtimelog.write('\nSomething went wrong\n')
		continue