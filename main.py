from binance.client import Client
from binance.enums import *
from binance import ThreadedWebsocketManager
import config as Config
import numpy
import talib


class Trade:
    RSI_PERIOD = 14
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70

    def __init__(self, twm, client) -> None:
        self.twm = twm
        self.client = client
        self.closes = []
        self.close  = 0
        self.buy_price = 0
        self.last_rsi = 0
        self.previous_rsi = 0
        self.BOUGHT = False
        self.SOLD = False

    def get_first_set_of_closes(self):
        for kline in self.client.get_historical_klines(Config.TRADESYMBOL, Client.KLINE_INTERVAL_1MINUTE, "1 hour ago UTC"):
            self.closes.append(float(kline[4]))

    def start(self):
        self.get_first_set_of_closes()
        self.twm.start()
        self.twm.start_kline_socket(callback=self.handle_socket_message,
                                    symbol=Config.TRADESYMBOL, interval=Client.KLINE_INTERVAL_1MINUTE)

    def get_balance(self, asset):
            balance = self.client.get_asset_balance(asset=asset)
            return balance

    def order(self, side):
        try:
            print("placing order for {}".format(side))
            if side == SIDE_BUY:
                self.client.order_market_buy(
                        symbol=Config.TRADESYMBOL,
                        quoteOrderQty=self.get_balance(Config.QUOTE_ASSET))
                self.BOUGHT = True
                self.SOLD = False
            else:
                self.client.order_market_sell(
                        symbol=Config.TRADESYMBOL,
                        quoteOrderQty=self.get_balance(Config.BASE_ASSET))
                self.SOLD = True
                self.BOUGHT = False
            self.previous_rsi = 0
        except Exception as e:
            print("error placing order for {}".format(side))
            return False
        return True

    def should_buy(self):
        if(self.last_rsi < Trade.RSI_OVERSOLD and not self.BOUGHT):
            if self.previous_rsi == 0:
                self.previous_rsi = self.last_rsi
                return False
            if self.previous_rsi > self.last_rsi:
                return True
            else:
                self.previous_rsi = self.last_rsi
                return False
        else:
            return False

    def should_sell(self):
        if(self.last_rsi >= Trade.RSI_OVERBOUGHT and not self.SOLD):
            if self.previous_rsi == 0:
                self.previous_rsi = self.last_rsi
                return False
            if self.previous_rsi < self.last_rsi:
                return True
            else:
                self.previous_rsi = self.last_rsi
                return False
        else:
            return False
    
    def buy_or_sell(self):
        if self.should_buy():
            print("Close price @ buy: {}".format(self.close))
            self.order(SIDE_BUY)
        if self.should_sell():
            print("Close price @ sale: {}".format(self.close))
            self.order(SIDE_SELL)
        print(self.last_rsi)

    def handle_socket_message(self, msg):
        candle = msg['k']
        self.close = candle['c']
        is_candle_closed = candle['x']
        if is_candle_closed:
            self.closes.append(float(self.close))
            if len(self.closes) > 30:
                self.closes.pop(0)
                np_closes = numpy.array(self.closes)
                rsi = talib.RSI(np_closes, Trade.RSI_PERIOD)
                self.last_rsi = rsi[-1]
                self.buy_or_sell()




# Start The Trade
twm = ThreadedWebsocketManager(
    api_key=Config.API_KEY, api_secret=Config.API_SECRET)

client = Client(Config.API_KEY, Config.API_SECRET)

trade = Trade(twm, client)

trade.start()
