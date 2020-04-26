import json
import time

from .ws_const import ExchangeType
from .ws_base import WebSocketBase


class BitflyerFxWS(WebSocketBase):

    ws_url = 'wss://ws.lightstream.bitflyer.com/json-rpc'

    def subscribe(self):
        message = json.dumps({
            'method': 'subscribe',
            'params': {
                'channel': 'lightning_executions_FX_BTC_JPY'
            }
        })
        self.ws.send(message)

    def decode_message(self, message):
        try:
            rcv_time = int(time.time() * 1000)

            m = json.loads(message)
            trades = m['params']['message']

            return list(map(lambda x: {
                'ex_key': ExchangeType.bitflyer_fx,
                'price': x['price'],
                'size': x['size'] if x['side'] == 'BUY' else -x['size'],
                'time': x['exec_date'],
                'rcv_time': rcv_time
            }, trades)), True
        except Exception as e:
            # raise or log if you need.
            return [], False
