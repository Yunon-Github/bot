import json
import time

from .ws_const import ExchangeType
from .ws_base import WebSocketBase


class GDaxWS(WebSocketBase):

    ws_url = 'wss://ws-feed.gdax.com'

    def subscribe(self):
        message = json.dumps({
            'type': 'subscribe',
            'channels': [
                {
                    'name': 'full',
                    'product_ids': ['BTC-USD']
                },
            ]
        })
        self.ws.send(message)

    def decode_message(self, message):
        try:
            rcv_time = int(time.time() * 1000)

            m = json.loads(message)

            if m['type'] != 'match':
                return [], False

            return [{
                'ex_key': ExchangeType.gdax,
                'price': float(m['price']),
                'size': float(m['size']) if m['side'] == 'sell' else -float(m['size']),
                'time': m['time'],
                'rcv_time': rcv_time
            }], True
        except Exception as e:
            # raise or log if you need.
            return [], False
