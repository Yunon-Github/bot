import json
import time

from .ws_const import ExchangeType
from .ws_base import WebSocketBase


class BitmexWS(WebSocketBase):

    ws_url = 'wss://www.bitmex.com/realtime'

    def subscribe(self):
        message = json.dumps({
            'op': 'subscribe', 
            'args': [ 
                'trade:XBTUSD', 
            ], 
        })
        self.ws.send(message)

    def decode_message(self, message):
        try:
            rcv_time = int(time.time() * 1000)

            m = json.loads(message)
            trades = m['data']
            
            if 'table' not in m:
                return [], False

            return list(map(lambda x: {
                'ex_key': ExchangeType.bitmex,
                'price': x['price'],
                'size': (x['size']/x['price']) if x['side'] == 'Buy' else -(x['size']/x['price']),
                'time': x['timestamp'],
                'rcv_time': rcv_time
            }, trades)), True
        except Exception as e:
            # raise or log if you need.
            return [], False
