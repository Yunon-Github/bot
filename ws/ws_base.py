import time
import logging

import websocket


class WebSocketBase(object):

    ws_url = ''

    ws = None
    callback = None
    to_retry = True

    retry_count = 0
    retry_sec = 3.0

    def __init__(self, callback=None):
        self.init_logging()
        self.init_ws()
        if callback:
            self.callback = callback

    @staticmethod
    def init_logging():
        logging.basicConfig(
            level=logging.INFO,
            filename='ws_exec.log',
            format='%(asctime)s: %(message)s',
        )

    @staticmethod
    def log_with_print(message):
        logging.info(message)
        print(message)

    @property
    def class_name(self):
        return self.__class__.__name__

    # initialize
    def init_ws(self):
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )

    def run(self):
        self.ws.run_forever()

    def close(self):
        self.to_retry = False
        self.ws.close()

    # callback methods
    def on_open(self):
        #self.log_with_print('--- %s Connected ---' % self.class_name)

        self.retry_count = 0
        self.subscribe()

    def on_error(self, error):
        if isinstance(error, KeyboardInterrupt):
            self.to_retry = False
        else:
            self.log_with_print('--- %s on_error ---' % self.class_name)

    def on_close(self):
        self.log_with_print('--- %s on_close ---' % self.class_name)

        if self.to_retry:
            self.retry_connection()

    def on_message(self, message):
        try:
            data, success = self.decode_message(message)
            if success and self.callback:
                self.callback(data)
        except Exception as e:
            raise e

    # re-connect
    def retry_connection(self):
        self.retry_count += 1
        sleep_time = self.retry_count * self.retry_sec

        self.log_with_print('--- wait %0.2f seconds for re-connect ---' % sleep_time)
        time.sleep(sleep_time)

        self.init_ws()
        self.run()

    # override me.
    def subscribe(self):
        pass

    # override me.
    def decode_message(self, message):
        return None, False
