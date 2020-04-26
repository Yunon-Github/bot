from multiprocessing import Process, Queue

from .ws_base import WebSocketBase
import time

# defined as global method, to take care windows
def run_ws(ws_instance):
    return WebSocketProcessor.run_ws(ws_instance)


class WebSocketProcessor(object):

    queue = None
    sockets = []
    processes = []

    def __init__(self):
        self.queue = Queue()
        self.sockets = []
        self.processes = []

    @staticmethod
    def run_ws(ws_instance):
        if isinstance(ws_instance, WebSocketBase):
            ws_instance.run()

    def ws_callback(self, ws_data):
        self.queue.put(ws_data)

    def add_ws(self, *ws_classes):
        for ws_class in ws_classes:
            ws_instance = ws_class(callback=self.ws_callback)
            self.sockets.append(ws_instance)
        return self

    def run(self):
        for ws_instance in self.sockets:
            process = Process(target=run_ws, args=(ws_instance,))
            process.start()
            self.processes.append(process)
        return self

    def get(self):
        if not self.queue.empty():
            return self.queue.get()
        time.sleep(0.0001)
        return None

    def close(self):
        for ws_instance in self.sockets:
            ws_instance.close()
        for process in self.processes:
            process.join()
        self.queue.close()

