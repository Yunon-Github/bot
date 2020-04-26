import json
import time

from .ws_const import ExchangeType
from .ws_base import WebSocketBase


class HitBTCWS(WebSocketBase):

    ws_url = 'wss://api.hitbtc.com/api/2/ws'

    def subscribe(self):
        message = json.dumps({
            'method': 'subscribeTrades', 
            'params': {
                'symbol': 'BTCUSD'
            }, 
            'id': int(time.time() * 1000)
        })
        self.ws.send(message)

    def decode_message(self, message):
        try:
            rcv_time = int(time.time() * 1000)

            m = json.loads(message)

            if 'method' not in m or m['method'] != 'updateTrades':
                return [], False

            trades = m['params']['data']

            return list(map(lambda x: {
                'ex_key': ExchangeType.hitbtc,
                'price': float(x['price']),
                'size': -float(x['quantity']) if x['side'] == 'sell' else float(x['quantity']),
                'time': x['timestamp'],
                'rcv_time': rcv_time
            }, trades)), True
        except Exception as e:
            # raise or log if you need.
            return [], False
