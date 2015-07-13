from cryptsy.private import AuthenticatedSession
from cryptsy.common import CryptsyError
import json
import urllib2
from decimal import *
import datetime
import time

print help(datetime.date)
with open(time.strftime("%Y-%m-%d") + '.txt', 'w+') as errorlog:
	errorlog.write("Now")