#need to optimize tjhat 
if (checking to make sure total spent on that coin is not more than defined amount)
	if above is true than adjust the amount allowed to be bought
		if (the amount to be bought equates to less than 10 satoshis make the order)
			make the order
			adjust total coins bought 
			adjust total spent by calcuting fees as well

			try and make sell order
			if it doesnt work add order to cleanup dictionary

		else dont make the order and continue to next coin
else (make the trade like normal)
	
if total_spent + order_total > max_coin_to_trade_order:
	order_amount = Decimal((max_coin_to_trade))