import json
import time

from .ws_const import ExchangeType
from .ws_base import WebSocketBase


class BitfinexWS(WebSocketBase):

    ws_url = 'wss://api.bitfinex.com/ws'

    def subscribe(self):
        message = json.dumps({
            'event': 'subscribe', 
            'channel': 'trades', 
            'symbol': 'BTCUSD'
        })
        self.ws.send(message)

    def decode_message(self, message):
        try:
            rcv_time = int(time.time() * 1000)

            m = json.loads(message)
            
            if type(m) is list and m[1] == 'te':
                return [{
                    'ex_key': ExchangeType.bitfinex,
                    'price': m[-2],
                    'size': m[-1],
                    'time': m[-3],
                    'rcv_time': rcv_time
                }], True
            return [], False
        except Exception as e:
            # raise or log if you need.
            return [], False
