import json
import time

from .ws_const import ExchangeType
from .ws_base import WebSocketBase

# Connect to Pusher via websocket-client
PUBLISH_KEY = 'de504dc5763aeef9ff52'


class BitstampWS(WebSocketBase):

    ws_url = 'wss://ws.pusherapp.com/app/%s?protocol=6' % PUBLISH_KEY
    # ?client=PythonPusherClient&version=0.2.0&protocol=6

    def subscribe(self):
        message = json.dumps({
            'event': 'pusher:subscribe', 
            'data': {
                'channel': 'live_trades'
            }, 
        })
        self.ws.send(message)

    def decode_message(self, message):
        try:
            rcv_time = int(time.time() * 1000)

            m = json.loads(message)
            if m['event'] != 'trade':
                return [], False

            t = json.loads(m['data'])
            price, timestamp = t['price'], t['timestamp']
            size = -float(t['amount']) if t['type'] == 1 else float(t['amount'])
            
            return [{
                'ex_key': ExchangeType.bitstamp,
                'price': price,
                'size': size, 
                'time': timestamp, 
                'rcv_time': rcv_time
            }], True
        except Exception as e:
            # raise or log if you need.
            return [], False
