import json
import time

from .ws_const import ExchangeType
from .ws_base import WebSocketBase


class CoincheckWS(WebSocketBase):

    ws_url = 'wss://ws-api.coincheck.com/'

    def subscribe(self):
        message = json.dumps({
            'type': 'subscribe', 
            'channel': 'btc_jpy-trades', 
        })
        self.ws.send(message)

    def decode_message(self, message):
        try:
            rcv_time = int(time.time() * 1000)

            m = json.loads(message)
            price = int(float(m[2]))
            size = -float(m[3]) if m[4] == 'sell' else float(m[3])
            
            return [{
                'ex_key': ExchangeType.coincheck,
                'price': price,
                'size': size, 
                'time': rcv_time,  # has not time property on ws..
                'rcv_time': rcv_time
            }], True
        except Exception as e:
            print(e)
            # raise or log if you need.
            return [], False
