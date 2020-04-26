import time
import logging

from sty import fg

from ws import (
    ExchangeType,

    BitfinexWS,
    BitflyerWS,
    BitflyerFxWS,
    BitmexWS,
    GDaxWS,
    BitstampWS,
    CoincheckWS,
    BinanceWS,
    HitBTCWS,
    OkexWS,

    WebSocketProcessor,
)

logger = logging.getLogger('LoggingTest')
logger.setLevel(20)
# ログのコンソール出力の設定（3）
sh = logging.StreamHandler()
logger.addHandler(sh)
# ログのファイル出力先を設定（4）
fh = logging.FileHandler('test.log')
logger.addHandler(fh)


def print_trades(trades):
    try:
        for trade in trades:
            trade_str = '%s %s %s %s' % (
                exchange_print(trade['ex_key'], padding=12),
                size_print(trade['size'], padding=10),
                price_print(trade['price'], padding=12),
                price_time(trade['rcv_time'], padding=16),
            )
            for_logger = trade['ex_key'], trade['size'], trade['price'], trade['rcv_time']
            logger.info(for_logger)
            print(trade_str)

    except Exception as e:
        print(e)


def color_string(string, color=255, padding=0):
    if padding:
        string = string.ljust(padding)
    return fg(color) + string + fg.rs


def exchange_print(ex_key, padding=10):
    exchange_strings = {
        ExchangeType.bitfinex: ('Bitfinex', 201),
        ExchangeType.bitflyer: ('Bitflyer', 51),
        ExchangeType.bitflyer_fx: ('BitflyerFX', 27),
        ExchangeType.bitmex: ('BitMEX', 35),
        ExchangeType.gdax: ('GDAX', 123),
        ExchangeType.bitstamp: ('BitStamp', 93),
        ExchangeType.coincheck: ('Coincheck', 173),
        ExchangeType.binance: ('Binance', 30),
        ExchangeType.hitbtc: ('HitBTC', 110),
        ExchangeType.okex: ('OKEx', 70),
    }
    exchange_string = exchange_strings[ex_key]
    return color_string(exchange_string[0], padding=padding)


def size_print(size, padding=10):
    size_string = '%.4f' % size
    if size > 0.0:
        return color_string(size_string, padding=padding)
    return color_string(size_string, padding=padding)


def price_print(price, padding=10):
    price_string = '%.1f' % price
    return color_string(price_string, padding=padding)


def price_time(unix_time, padding=10):
    time_string = '%d' % unix_time
    return color_string(time_string, padding=padding)


def main():
    ws_processor = WebSocketProcessor().add_ws(
        #BitfinexWS,
        #BitflyerWS,
        BitflyerFxWS,
        #BitmexWS,
        #GDaxWS,
        #BitstampWS,
        #CoincheckWS,
        BinanceWS,
        #HitBTCWS,
        #OkexWS,
    ).run()

    try:
        while True:
            trades = ws_processor.get()
            if trades == None:
                continue
            #print(trades)
            print_trades(trades)

    except KeyboardInterrupt:
        print('Closing sockets...')
        ws_processor.close()
        time.sleep(2.0)


if __name__ == '__main__':
    main()
