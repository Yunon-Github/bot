import json
import time

from .ws_const import ExchangeType
from .ws_base import WebSocketBase


class BinanceWS(WebSocketBase):

    ws_url = 'wss://stream.binance.com:9443/ws/btcusdt@trade'

    def subscribe(self):
        # ws.send() to Binance, is not required
        pass

    def decode_message(self, message):
        try:
            rcv_time = int(time.time() * 1000)

            m = json.loads(message)
            e, ut, price = m['e'], m['E'], float(m['p'])
            size = -float(m['q']) if m['m'] else float(m['q'])

            return [{
                'ex_key': ExchangeType.binance,
                'price': price,
                'size': size, 
                'time': ut, 
                'rcv_time': rcv_time,
            }], True
        except Exception as e:
            # raise or log if you need.
            return [], False
