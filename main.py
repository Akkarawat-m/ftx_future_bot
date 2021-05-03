### JUST FOR LEARNING PURPOSE USE AT YOUR OWN RISK !!!!! ####

# import neccessary package

import ccxt
import json
import pandas as pd
import time
import decimal
from datetime import datetime
import pytz
import csv
import simplejson as json

def read_config():
    with open('config.json') as json_file:
        return json.load(json_file)

config = read_config()

# Api and secret
api_key = config["apiKey"]
api_secret = config["secret"]
subaccount = config["sub_account"]
account_name = config["account_name"]  # Set your account name (ตั้งชื่อ Account ที่ต้องการให้แสดงผล)
pair = config["pair"]



# Exchange Details
exchange = ccxt.ftx({
    'apiKey': api_key,
    'secret': api_secret,
    'enableRateLimit': True}
)
exchange.headers = {'FTX-SUBACCOUNT': subaccount,}
post_only = True  # Maker or Taker (วางโพซิชั่นเป็น MAKER เท่านั้นหรือไม่ True = ใช่)

# Global Varibale Setting
min_trade_size = 0.25  # Minimum Trading Size ($)

# Fix Value Setting
capital = 50
leverage = 2
cap_lev = capital * leverage
step = 0.001
upzone = 0.50
lowzone = 0.25

# Equation calculation
zone_range = round(upzone - (lowzone), 10)
trade_slot = int(zone_range / step)  # all trade slot (จำนวนไม้)
base_size = ((cap_lev / upzone) / trade_slot)
x_point = [upzone, lowzone]
y_point = [base_size, (trade_slot * base_size)]

a = (y_point[1] - y_point[0]) / (x_point[1] - x_point[0])
b = y_point[1] - (a * (x_point[1]))


# file system
tradelog_file = "tradinglog_{}.csv".format(subaccount)
trading_call_back = 5

# Rebalance Condition
time_sequence = [1]  # Trading Time Sequence (เวลาที่จะใช้ในการ Rebalance ใส่เป็นเวลาเดี่ยว หรือชุดตัวเลขก็ได้)

### Function Part ###

def get_time():  # เวลาปัจจุบัน
    named_tuple = time.localtime() # get struct_time
    Time = time.strftime("%m/%d/%Y, %H:%M:%S", named_tuple)
    return Time

def get_price():
    price = exchange.fetch_ticker(pair)['last']
    return float(price)

def get_ask_price():
    ask_price = exchange.fetch_ticker(pair)['ask']
    return float(ask_price)

def get_bid_price():
    bid_price = exchange.fetch_ticker(pair)['bid']
    return float(bid_price)

def get_pending_buy():
    pending_buy = []
    for i in exchange.fetch_open_orders(pair):
        if i['side'] == 'buy':
            pending_buy.append(i['info'])
    return pending_buy

def get_pending_sell():
    pending_sell = []
    for i in exchange.fetch_open_orders(pair):
        if i['side'] == 'sell':
            pending_sell.append(i['info'])
    return pending_sell

def create_buy_order():
    # Order Parameter
    types = 'limit'
    side = 'buy'
    size = buy_size
    price = buy_price
    exchange.create_order(pair, types, side, size, price, {'postOnly': post_only})
    print("{} Buy Order Created".format(pair))
    
def create_sell_order():
    # Order Parameter
    types = 'limit'
    side = 'sell'
    size = sell_size
    price = sell_price
    exchange.create_order(pair, types, side, size, price, {'postOnly': post_only})
    print("{} Sell Order Created".format(pair))
    
def cancel_order(order_id):
    order_id = order_id
    exchange.cancel_order(order_id)
    print("Order ID : {} Successfully Canceled".format(order_id))

def get_minimum_size():
    minimum_size = float(exchange.fetch_ticker(pair)['info']['minProvideSize'])
    return minimum_size

def get_step_size():
    step_size = float(exchange.fetch_ticker(pair)['info']['sizeIncrement'])
    return step_size

def get_step_price():
    step_price = float(exchange.fetch_ticker(pair)['info']['priceIncrement'])
    return step_price

def get_min_trade_value():
    min_trade_value = float(exchange.fetch_ticker(pair)['info']['sizeIncrement']) * price
    return min_trade_value

def get_wallet_details():
    wallet = exchange.privateGetWalletBalances()['result']
    return wallet

def get_cash():
    wallet = exchange.privateGetWalletBalances()['result']
    for t in wallet:
        if t['coin'] == 'USD':
            cash = float(t['availableWithoutBorrow'] )
    return cash

def get_position_size():
    position_pair = exchange.privateGetPositions()["result"][0]['future']
    if position_pair == pair:
        position_size = exchange.privateGetPositions()["result"][0]['size']
        
    return float(position_size)

def get_position_value():
    position_pair = exchange.privateGetPositions()["result"][0]['future']
    if position_pair == pair:
        position_value = exchange.privateGetPositions()["result"][0]['cost']
    
    return float(position_value)

def get_free_col():
    free_col = float(exchange.privateGetAccount()['result']['freeCollateral'])
    
    return free_col

def get_last_trade_price(pair):
    pair = pair
    trade_history = pd.DataFrame(exchange.fetchMyTrades(pair, limit = 1),
                            columns=['id', 'timestamp', 'datetime', 'symbol', 'side', 'price', 'amount', 'cost', 'fee'])
    last_trade_price = trade_history['price']
    
    return float(last_trade_price)

def buy_execute():
    pending_buy = get_pending_buy()
    if pending_buy == []:
        print('Buying {} Size = {}'.format(pair, buy_size))
        create_buy_order()
        time.sleep(5)
        pending_buy = get_pending_buy()

        if pending_buy != []:
            print('Waiting For Order To be filled')
            pending_buy_id = get_pending_buy()[0]['id']
            print('Buy Order Created Success, Order ID: {}'.format(pending_buy_id))
            print('Waiting For Buy Order To be Filled')
            time.sleep(10)
            pending_buy = get_pending_buy()

        if pending_buy == []:
            print("Buy order Matched")
            print("Updating Trade Log")
            update_trade_log(pair)
        else:
            print('Buy Order is not match, Resending...')
            pending_buy_id = get_pending_buy()[0]['id']
            order_id = pending_buy_id
            cancel_order(order_id)  
    else:
        pending_buy_id = get_pending_buy()[0]['id']
        print("Pending BUY Order Found")
        print("Canceling pending Order")
        order_id = pending_buy_id
        cancel_order(order_id)
        pending_buy = get_pending_buy()

        if pending_buy == []:
            print('Buy Order Matched or Cancelled')
        else:
            print('Buy Order is not Matched or Cancelled, Retrying')
    print("------------------------------")

def sell_execute():
    pending_sell = get_pending_sell()

    if pending_sell == []:
        print('Selling {} Size = {}'.format(pair, sell_size))
        create_sell_order()
        time.sleep(5)
        pending_sell = get_pending_sell()
        if pending_sell != []:
            pending_sell_id = get_pending_sell()[0]['id']
            print('Sell Order Created Success, Order ID: {}'.format(pending_sell_id))
            print('Waiting For Sell Order To be filled')
            time.sleep(10)
            pending_sell = get_pending_sell()

        if pending_sell == []:
            print("Sell order Matched")
            print("Updating Trade Log")
            update_trade_log(pair)
        else:
            print('Sell Order is not match, Resending...')
            pending_sell_id = get_pending_sell()[0]['id']
            order_id = pending_sell_id
            cancel_order(order_id)

    else:
        pending_sell_id = get_pending_sell()[0]['id']
        print("Pending Order Found")
        print("Canceling pending Order")
        order_id = pending_sell_id
        cancel_order(order_id)
        time.sleep(1)
        pending_sell = get_pending_sell()

        if pending_sell == []:
            print('Sell Order Matched or Cancelled')
        else:
            print('Sell Order is not Matched or Cancelled, Retrying')
    print("------------------------------")

# Database Function Part
def checkDB():
    try:
        tradinglog = pd.read_csv(tradelog_file)
        print('DataBase Exist Loading DataBase....')
    except:
        tradinglog = pd.DataFrame(columns=['id', 'timestamp', 'time', 'pair', 'side', 'price', 'qty', 'fee', 'timeseries', 'bot_name', 'subaccount', 'cost'])
        tradinglog.to_csv(tradelog_file,index=False)
        print("Database Created")
        
    return tradinglog

def create_funding_csv():
    try:      
        dffunding  = pd.read_csv("dffunding.csv")
    except:
        dffunding = pd.DataFrame(columns=['id','future','payment','time','rate'])
        dffunding.to_csv("dffunding.csv",index=False) 

# Database Setup
print('Checking Database file.....')
tradinglog = checkDB()
create_funding_csv()

def get_trade_history(pair):
    pair = pair
    trade_history = pd.DataFrame(exchange.fetchMyTrades(pair, limit = trading_call_back),
                              columns=['id', 'timestamp', 'datetime', 'symbol', 'side', 'price', 'amount', 'fee'])
    
    cost=[]
    for i in range(len(trade_history)):
        fee = trade_history['fee'].iloc[i]['cost'] if trade_history['fee'].iloc[i]['currency'] == 'USD' else trade_history['fee'].iloc[i]['cost'] * trade_history['price'].iloc[i]
        cost.append(fee)  # ใน fee เอาแค่ cost
    
    trade_history['fee'] = cost
    
    return trade_history

def get_last_id(pair):
    pair = pair
    trade_history = get_trade_history(pair)
    last_trade_id = (trade_history.iloc[:trading_call_back]['id'])
    
    return last_trade_id

def getfunding():
    dffunding = pd.DataFrame(exchange.private_get_funding_payments()['result'],
                    columns=['id','future','payment','time','rate'])
    return dffunding

def updatefunding():
    funding_in_csv = pd.read_csv('dffunding.csv')
    checkIDincsv = funding_in_csv['id'].values.tolist()
    #print(type(checkIDincsv[0]))
    fundingftx   = getfunding()
    for i in range(len(fundingftx)):
        #print(type(fundingftx['id'][i]) == type(checkIDincsv[0]))
        if int(fundingftx['id'][i]) not in checkIDincsv :
            with open("dffunding.csv", "a+", newline='') as fp:
                wr = csv.writer(fp, dialect='excel')
                wr.writerow(fundingftx.iloc[i])

def update_trade_log(pair):
    pair = pair
    tradinglog = pd.read_csv(tradelog_file)
    last_trade_id = get_last_id(pair)
    trade_history = get_trade_history(pair)
    
    for i in last_trade_id:
        tradinglog = pd.read_csv(tradelog_file)
        trade_history = get_trade_history(pair)
    
        if int(i) not in tradinglog.values:
            print(i not in tradinglog.values)
            last_trade = trade_history.loc[trade_history['id'] == i]
            list_last_trade = last_trade.values.tolist()[0]

            # แปลงวันที่ใน record
            d = datetime.strptime(list_last_trade[2], "%Y-%m-%dT%H:%M:%S.%fZ")
            d = pytz.timezone('Etc/GMT+7').localize(d)
            d = d.astimezone(pytz.utc)
            Date = d.strftime("%Y-%m-%d")
            Time = d.strftime("%H:%M:%S")
            time_serie = (d.weekday()*1440)+(d.hour*60)+d.minute

            # find Cost
            cost = float(list_last_trade[5] * list_last_trade[6])


            print(list_last_trade)
            # edit & append ข้อมูลก่อน add เข้า database
            list_last_trade[1] = Date
            list_last_trade[2] = Time
            list_last_trade.append(time_serie)
            list_last_trade.append(account_name)
            list_last_trade.append(subaccount)
            list_last_trade.append(cost)

            ## list_last_trade.append(cost)

            with open(tradelog_file, "a+", newline='') as fp:
                wr = csv.writer(fp, dialect='excel')
                wr.writerow(list_last_trade)
            print('Recording Trade ID : {}'.format(i))
        else:
            print('Trade Already record')

# Main Loop


while True:
    try:
        # Checking Initial Balance Loop
        while exchange.privateGetPositions()["result"] == [] or get_position_size() < 1:
            print('Entering Initial Loop')
            print("------------------------------")

            position_size = 0
            print("You don't have any position yet")
            print("Creating Initial Position")
        
            pair = pair
            price = get_price()
            ask_price = get_ask_price()
            bid_price = get_bid_price()
        
            # Trade history Checking
            
            print('Validating Trading History')
            update_trade_log(pair)
                
            # Innitial asset BUY params
            pair = pair
            bid_price = get_bid_price()
            min_size = get_minimum_size()
            step_price = get_step_price()
            min_trade_value = get_min_trade_value()
            cash = get_cash()
            pending_buy = get_pending_buy()
            fix_asset_control = (a * price) + b
            buy_size = fix_asset_control
            buy_price = bid_price - step_price
                        
            if price < upzone and price > lowzone:
                if cash > min_trade_value and buy_size > min_size:
                    buy_execute()
                else:
                    print("Not Enough Balance to buy {}".format(pair))
                    print('Your Cash is {} // Minimum Trade Value is {}'.format(cash, min_trade_value))
            elif price > upzone:
                print("Out of trading zone")
                print("Price more than {}".format(str(upzone)))
            else :
                print("Out of trading zone")
                print("Price lower than {}".format(str(lowzone)))
        else:
            print('Your already have {} position'.format(pair))
            print("------------------------------")
            time.sleep(1)

        # Trading Loop
        for t in time_sequence:
            free_col = get_free_col()
            Time = get_time()
            

            print('Time : {}'.format(Time))
            print('Checking Your Position')
            position_size = get_position_size()
            position_value = get_position_value()
            
            print('Your position size is : {}'.format(position_size))

            if free_col > 1 and exchange.privateGetPositions()["result"] != []:
                print('Entering Trading Loop')
                print("------------------------------")
                wallet = get_wallet_details()

                pair = pair
                price = get_price()
                position_size = get_position_size()
                position_value = get_position_value()
                min_size = get_minimum_size()
                fix_asset_control = (a * price) + b
                last_trade_price = get_last_trade_price(pair)

                while price > upzone:
                    if position_size > min_size:
                        sell_size = position_size
                        sell_execute()
                        price = get_price()
                        time.sleep(5)
                    else:
                        print("Out of trading zone")
                        print("Price more than {}".format(str(upzone)))
                        price = get_price()
                        time.sleep(5)
                            
                while price < lowzone:
                        print("Out of trading zone")
                        print("Price lower than {}".format(str(lowzone)))
                        price = get_price()
                        time.sleep(5)

                if pair == exchange.privateGetPositions()["result"][0]['future']:
                    # check coin price and value
                    print('{} Price is {}'.format(pair, price))
                    print('{} Value is {}'.format(pair, position_value))
                    print('{} Amount is {}'.format(pair, position_size))
                    print('Fix Asset Control is {}'.format(fix_asset_control))
                    print('Base Trading Size is {}'.format(base_size))
                        
                # Check trading BUY trigger
                if position_size <= fix_asset_control - base_size and price < last_trade_price - step:
                    print("Current {} size less than fix size : Trading -- Buy".format(pair))
                            
                    # Create trading params
                    price = get_price()
                    bid_price = get_bid_price()
                    min_size = get_minimum_size()
                    step_price = get_step_price()
                    min_trade_value = get_min_trade_value()
                    cash = get_cash()
                    pending_buy = get_pending_buy()

                    # Trading Diff Control
                    fix_asset_control = (a * price) + b
                    diff = abs(fix_asset_control - position_size)
                    
                    # Create BUY params
                    buy_size = diff
                    buy_price = bid_price - step_price

                            # BUY order execution
                    if free_col > min_trade_value and buy_size > min_size:
                        buy_execute()
                    else:
                        print("Not Enough Balance to buy {}".format(pair))
                        print('Your Collateral is {} // Minimum Trade Value is {}'.format(free_col, min_trade_value))
                        
                # Check trading SELL trigger        
                elif position_size >= fix_asset_control + base_size and price > last_trade_price + step:
                    print("Current {} Amount more than fix amount : Trading -- Sell".format(pair))
                            
                    # Create sell trading params
                    price = get_price()
                    bid_price = get_bid_price()
                    min_size = get_minimum_size()
                    step_price = get_step_price()
                    min_trade_value = get_min_trade_value()
                    pending_sell = get_pending_sell()

                    # Trading Diff Control
                    fix_asset_control = (a * price) + b
                    diff = abs(fix_asset_control - position_size)
                            
                    # Create SELL params
                    sell_size = diff
                    sell_price = bid_price + (3 * step_price)
                    
                    # SELL order execution
                    if diff > base_size and sell_size > min_size:
                        sell_execute()
                    else:
                        print("Not Enough Balance to sell {}".format(pair))
                        print('You are selling {} {} BUT Minimum Trade amount is {}'.format(sell_size, pair, min_size))
                            
                else:
                    if abs(price - last_trade_price) < step:
                        diff_price = price - last_trade_price
                        print("Diff from last trade is {}".format((diff_price)))
                        print("Current price diff is not reach {} yet : Waiting".format(step))
                    else:
                        print("Current {} size is not reach fix Size Trigger yet : Waiting".format(pair))

                    print("------------------------------")
                    time.sleep(5)

            # Rebalancing Time Sequence
            print('Current Time Sequence is : {}'.format(t))
            updatefunding()
            fundingincsv = pd.read_csv("dffunding.csv")
            fund = fundingincsv['payment'].sum()
            print('Total Funding fee is {}'.format(fund))
            time.sleep(t)

    except Exception as e:
        print('Error : {}'.format(str(e)))
        time.sleep(10)  