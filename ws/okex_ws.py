import json
import time
import zlib

from .ws_const import ExchangeType
from .ws_base import WebSocketBase


class OkexWS(WebSocketBase):

    ws_url = 'wss://real.okex.com:10442/ws/v3'

    @staticmethod
    def inflate(data):
        decompress = zlib.decompressobj(-zlib.MAX_WBITS)
        inflated = decompress.decompress(data)
        inflated += decompress.flush()
        return inflated

    def subscribe(self):
        message = json.dumps({
            'op': 'subscribe',
            'args': [
                'spot/trade:BTC-USDT',
            ],
        })
        self.ws.send(message)

    def decode_message(self, message):
        try:
            rcv_time = int(time.time() * 1000)

            message = self.inflate(message)
            m = json.loads(message)

            if 'table' not in m or m['table'] != 'spot/trade':
                return [], False

            trades = m['data']
            return list(map(lambda x: {
                'ex_key': ExchangeType.okex,
                'price': float(x['price']),
                'size': -float(x['size']) if x['side'] == 'sell' else float(x['size']),
                'time': x['timestamp'],
                'rcv_time': rcv_time
            }, trades)), True
        except Exception as e:
            # raise or log if you need.
            return [], False
