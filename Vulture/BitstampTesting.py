import bitstamp.client
from coinbase import CoinbaseAccount
import oauth2client
import time

public_client = bitstamp.client.Public()

while True:
	bitstamp_file = open('bitstamp.txt', 'a')
	print 'Grabbing Info'
	ticker = public_client.ticker()
	print 'Printing Info To File'
	bitstamp_file.write(ticker['last'] + ',' + ticker['ask'] + ',' + ticker['timestamp'] + '\n')
	print 'Pausing for 1 minute'
	print '---'
	bitstamp_file.close()
	time.sleep(60)