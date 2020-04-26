import time
import decimal
import pybitflyer
from multiprocessing import Process, Manager
from sty import fg
import configparser
from linebot import LineBotApi
from linebot.models import TextSendMessage
from linebot.exceptions import LineBotApiError
import influxdb
from bffx_client import BFFXClient, OrderState

from ws import (
    ExchangeType,
    BinanceWS,
    WebSocketProcessor,
)


# PRINT_VOLUME_INTERVAL_SEC = 20.0
# TRADES_RELEASE_SEC = 30.0

# プロセス間共有変数
api_count_manager = Manager()
time_count_manager = Manager()
api_count = api_count_manager.list([0, 0, 0, 0, 0])
time_count = time_count_manager.list([0, 0, 0])


# BFFXClient のインスタンスを生成
client = BFFXClient(
    api_key="XwtMm31szNgQPAfgTH1ZjY",  # bitFlyerのAPI Key
    api_secret="jxQ09ydZWxfAe6CB3U3fvVMJSNjPaEaSJiinLn5Qu9k="  # bitFlyerのAPI Secret
)

# bitFlyerAPIキーの設定
api = pybitflyer.API(
    api_key="XwtMm31szNgQPAfgTH1ZjY",
    api_secret="jxQ09ydZWxfAe6CB3U3fvVMJSNjPaEaSJiinLn5Qu9k="
)

# Line Notify
LINE_ACCESS_TOKEN = "ueJ1bnMTfoqMYaruN5zrQ3dsEZ6YvybUqVIYlkFPqtZG74FzYz5tb3Ao8M3itweppzHzThNXsrTLy/mCCVRaYYKw2VGU79H+tGH6COrNRqqO2WtfQ7210Rq2UGO9Kl0tETgqIxhu4TmdbWdgFdRZaAdB04t89/1O/w1cDnyilFU=" # ラインアクセストークン
LINE_USER_ID = "Ue75543d77fa00129801af8cc590405df"
line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)

# influxDB
client_influxdb = influxdb.InfluxDBClient(port='8086', username='Yunon', password='drew520mice231')
client_influxdb.switch_database('bot')


# パラメータ読み込み
inifile = configparser.SafeConfigParser()
inifile.read('param.ini')
BOT_STATUS = inifile.get('SYSTEM', 'BOT_STATUS')
LONG_THRESHOLD = decimal.Decimal(inifile.get('BINANCE', 'LONG_THRESHOLD'))
SHORT_THRESHOLD = decimal.Decimal(inifile.get('BINANCE', 'SHORT_THRESHOLD'))
LOGIC_TYPE_LONG_LOT = float(inifile.get('TRADE', 'LOGIC_TYPE_LONG_LOT'))
LOGIC_TYPE_SHORT_LOT = float(inifile.get('TRADE', 'LOGIC_TYPE_SHORT_LOT'))
MAKE_ADDSUB = int(inifile.get('TRADE', 'MAKE_ADDSUB'))
LOGIC_TYPE_LONG_KAIRI = int(inifile.get('TRADE', 'LOGIC_TYPE_LONG_KAIRI'))
LOGIC_TYPE_SHORT_KAIRI = int(inifile.get('TRADE', 'LOGIC_TYPE_SHORT_KAIRI'))
INTERBAL = int(inifile.get('BINANCE','INTERBAL'))


def insert_influxdb(measurement, value):
    data = [{'measurement': measurement,
            'tags': {'botname': 'Bi-bF-soukan'},
            'fields': {'count': float(value)}
            }]
    client_influxdb.write_points(data)


def line_notify_exec(error, number):

    # メッセージ生成
    text = number + 'にて' + str(error) + 'が発生しました'

    try:
        # ラインユーザIDは配列で指定する。
        line_bot_api.multicast(
        [LINE_USER_ID], TextSendMessage(text=text)
    )
    except LineBotApiError as e:
        # エラーが起こり送信できなかった場合
        print(e)


def error_checker(r):
    if 'child_order_acceptance_id' in r:
        return 'ok'
    elif 'error_message' in r:
        return 'ng'
    else:
        return '例外です'


def time_counter():

    standard = time.perf_counter()

    # 0番地を1分毎に0→4まで順繰りで更新
    # time_count[0] = 0

    try:
        while True:

            # print(time_count)

            # 1分経過するまでcontinue
            if time.perf_counter() - standard < 60:
                continue

            # 1分経過したらtime_countの値をすすめ、standardを再設定する
            else:
                standard = time.perf_counter()

                # time_countが0〜4なら素直に+1
                if time_count[0] < 5:
                    time_count[0] += 1
                    # time_countが5に到達したらフラグを立てる。そのあとこの関数を終了。
                    if time_count[0] == 5:
                        time_count[0] = 4
                        time_count[1] = 1

            if time_count[1] == 1:
                # print('time_counterを終了します')
                break

    except Exception as e:
        print(e)


def api_counter():
    while True:

        if time_count[1] == 0:
            # 最初の5分間は淡々とapi_count[0〜4]に蓄積
            print('api_count = ', api_count[0], ' ', api_count[1], ' ', api_count[2], ' ', api_count[3], ' ', api_count[4])
            time.sleep(5)
            print(sum(api_count))
            insert_influxdb('api_count', sum(api_count))

        # 5分経ったら
        elif time_count[1] == 1 and time_count[2] == 0:
            del api_count[0]
            api_count.append(1)
            standard = time.perf_counter()
            time_count[2] = 1

        elif time_count[1] == 1 and time_count[2] == 1:
            if time.perf_counter() - standard < 60:

                print('api_count = ', api_count[0], ' ', api_count[1], ' ', api_count[2], ' ', api_count[3], ' ', api_count[4])
                time.sleep(5)
                print(sum(api_count))
                insert_influxdb('api_count', sum(api_count))
                continue
            else:
                del api_count[0]
                api_count.append(0)
                standard = time.perf_counter()


# メインで実行される関数
def receive_trades():

    # Binanceの閾値チェックロジックを定義
    def logic_in_binance(trade):

        # Binanceの閾値チェック
        first = decimal.Decimal(str(fixed_price))
        last = decimal.Decimal(str(trade['price']))
        hendouritsu = decimal.Decimal(str((last / first) - 1))
        # print('last = ', last, 'first = ', first)
        # print('変動率 = ', hendouritsu)

        # bitflyer側ロジックへの入り口
        if hendouritsu > LONG_THRESHOLD:
            # line_Notify_exec()
            print('Longで注文します')
            order_in_bitflyer('Long')
            return 0

        elif hendouritsu < SHORT_THRESHOLD:
            # line_notify_exec()
            print('Shortで注文します')
            order_in_bitflyer('Short')
            return 0

        else:
            return 1

    # bitflyerでの注文
    def order_in_bitflyer(order_type):

        if order_type == 'Long':

            nariyuki_tyumon_sta = time.perf_counter()

            # 成行買注文
            order_market_long = client.market_buy(size=float(LOGIC_TYPE_LONG_LOT))
            api_count[time_count[0]] += 1

            # 成行売注文後のエラーチェック
            r = error_checker(order_market_long)
            if r == 'ok':
                print('注文成功')
            elif r == 'ng':
                print('ロジックを抜けます')
                return
            else:
                print('エラーチェック例外')
                return

            print('Shortで成行注文が完了しました')

            print('Longで成行注文が完了しました')

            # ポジションチェック
            try:
                while True:
                    print('ポジションを確認します')

                    position_count = 0
                    position_check_count = 0

                    position = api.getpositions(product_code='FX_BTC_JPY')
                    api_count[time_count[0]] += 1

                    if position == []:
                        position_check_count += 1
                        if position_check_count > 150:
                            error = '150回以内にポジション確認できませんでした。注文せずに次の閾値チェックに進みます。'
                            print(error)
                            line_notify_exec(error, 'No.16')
                            break
                        continue

                    else:
                        # 成行注文を出してポジションを持つまでにかかった時間
                        nariyuki_tyumon_end = time.perf_counter() - nariyuki_tyumon_sta
                        res = insert_influxdb('positon_confirm_time', nariyuki_tyumon_end)
                        print('res = ', res)

                        print('ポジションは', len(position), '個あります')
                        position_price_result = 0

                        # ポジションの数を数えつつ、priceを変数に格納
                        for positionList in position:
                            position_price = positionList['price']
                            position_size = positionList['size']
                            print(position_count+1, '個目のポジション価格は ', position_price, '円です')

                            position_price_result = position_price_result + position_price * (position_size / float(LOGIC_TYPE_LONG_LOT))
                            print('ポジション価格の合計 = ', position_price_result)
                            position_count += 1

                        # ポジジョン価格を平均値から出した結果

                        print('算出されたポジション価格 = ', position_price_result)

                        # 得たポジションを元に指値売注文

                        order_maker_price = round(position_price_result + MAKE_ADDSUB)
                        print(order_maker_price, '円でShort指値注文します')

                        btc_short_maker = client.limit_sell(size=float(LOGIC_TYPE_LONG_LOT), price=order_maker_price)
                        api_count[time_count[0]] += 1

                        try:

                            while True:
                                # 本当に指値注文が完了したかの確認
                                orders_really_check = client.child_orders(count=10, child_order_state=OrderState.ACTIVE)  # Activeなものを10件取得
                                api_count[time_count[0]] += 1

                                # 成行注文が残っているか確認
                                position_really_check = client.has_positions()
                                api_count[time_count[0]] += 1

                                # 成行注文が残っている、かつ指値注文が空の時→continue
                                if position_really_check and orders_really_check == []:
                                    print('recheck')
                                    print('position_really_check = ', position_really_check)
                                    print('orders_really_check = ', orders_really_check)
                                    time.sleep(2)
                                    continue
                                else:
                                    print('orders_really_check = ', orders_really_check)
                                    print('Short指値注文が完了しました')
                                    break
                        except Exception as e:
                            print(e)
                            line_notify_exec(e, 'No.4')

                        break

            except Exception as e:
                print(e)
                line_notify_exec(e, 'No.5')

        # shortから入る場合
        elif order_type == 'Short':

            nariyuki_tyumon_sta = time.perf_counter()

            # 成行売注文
            order_market_short = client.market_sell(size=float(LOGIC_TYPE_SHORT_LOT))
            api_count[time_count[0]] += 1

            # 成行売注文後のエラーチェック
            r = error_checker(order_market_short)
            if r == 'ok':
                print('注文成功')
            elif r == 'ng':
                print('ロジックを抜けます')
                return
            else:
                print('エラーチェック例外')
                return

            print('Shortで成行注文が完了しました')

            # ポジションチェック
            try:
                print('ポジションを確認します')
                while True:

                    position_count = 0
                    position_check_count = 0

                    position = api.getpositions(product_code='FX_BTC_JPY')
                    api_count[time_count[0]] += 1
                    print(position)

                    if position == []:

                        position_check_count += 1
                        if position_check_count > 150:
                            error = '150回以内にポジション確認できませんでした。注文せずに次の閾値チェックに進みます。'
                            print(error)
                            line_notify_exec(error, 'No.16')
                            break
                        continue
                    else:
                        # 成行注文を出してポジションを持つまでにかかった時間
                        nariyuki_tyumon_end = time.perf_counter() - nariyuki_tyumon_sta
                        res = insert_influxdb('positon_confirm_time', nariyuki_tyumon_end)
                        print('res = ', res)

                        print('ポジションは', len(position), '個あります')
                        position_price_result = 0

                        # ポジションの数を数えつつ、priceを変数に格納
                        for positionList in position:
                            position_price = positionList['price']
                            position_size = positionList['size']
                            print(position_count+1, '個目のポジション価格は ', position_price, '円です')
                            position_price_result = position_price_result + position_price * (position_size / float(LOGIC_TYPE_SHORT_LOT))
                            print('ポジション価格の合計 = ', position_price_result)
                            position_count += 1

                        # ポジジョン価格を平均値から出した結果
                        print('算出されたポジション価格 = ', position_price_result)

                        # 得たポジションを元に指値買注文
                        order_maker_price = round(position_price_result - MAKE_ADDSUB)
                        print(order_maker_price, '円でLong指値注文します')

                        client.limit_buy(size=LOGIC_TYPE_SHORT_LOT, price=order_maker_price)
                        api_count[time_count[0]] += 1

                        try:

                            while True:
                                # 本当に指値注文が完了したかの確認
                                orders_really_check = client.child_orders(count=10, child_order_state=OrderState.ACTIVE)  # Activeなものを10件取得
                                api_count[time_count[0]] += 1

                                # 成行注文が残っているか確認
                                position_really_check = client.has_positions()
                                api_count[time_count[0]] += 1

                                # 成行注文が残っている、かつ指値注文が空の時→continue
                                if position_really_check == True and orders_really_check == []:
                                    print('recheck')
                                    print('position_really_check = ', position_really_check)
                                    print('orders_really_check = ', orders_really_check)
                                    time.sleep(2)
                                    continue
                                else:
                                    print('orders_really_check = ', orders_really_check)
                                    print('Long指値注文が完了しました')
                                    break
                        except Exception as e:
                            print(e)
                            line_notify_exec(e, 'No.6')

                        break
            except Exception as e:
                print(e)
                line_notify_exec(e, 'No.7')

        # トレード完了チェック
        try:

            moving_losscut_flag1 = 0

            while True:
                # 建玉が無い かつ　指値注文がなければトレード完了とする
                position_recheck = client.has_positions()
                api_count[time_count[0]] += 1

                orders = client.child_orders(count=10, child_order_state=OrderState.ACTIVE)  # Activeなものを10件取得
                api_count[time_count[0]] += 1

                if position_recheck == False and orders == []:
                    print('トレードが完了しました')
                    break

                # ポジションが残っている場合
                else:

                    ltp = client.ltp()
                    api_count[time_count[0]] += 1

                    print("[FX_BTC_JPY] の最終価格 : " + "{}".format(ltp) + " 円")
                    print('ポジション価格は ', position_price_result, '円')
                    kairi = ltp - position_price_result

                    if order_type == 'Long':

                        print('ポジション価格と最終価格の乖離 = ', kairi, ' < ', LOGIC_TYPE_LONG_KAIRI, 'なら手仕舞い')

                        # 動的損切りロジック1(一度0から500逆方向を超えた後は、それ以降初めて0を跨ぐと手仕舞い)
                        if kairi < -500:
                            moving_losscut_flag1 = 1
                            print('moving_losscut_flag1を立てます')

                        if moving_losscut_flag1 == 1 and kairi > 0:
                            print('動的損切りロジックで手仕舞いします')

                        if (kairi < LOGIC_TYPE_LONG_KAIRI) or (moving_losscut_flag1 == 1 and kairi > 0):
                            print('手仕舞いします')

                            # 指値キャンセル
                            orders = client.cancel_all_child_orders()

                            try:
                                while True:
                                    # Activeなものを10件取得
                                    orders = client.child_orders(count=10, child_order_state=OrderState.ACTIVE)
                                    api_count[time_count[0]] += 1

                                    if orders == []:
                                        print('指値注文の手仕舞い完了')
                                        break
                                    else:
                                        print('指値注文の手仕舞い未完了')
                                        time.sleep(3)
                                        continue

                            except Exception as e:
                                print(e)
                                line_notify_exec(e, 'No.9')

                            # 成行注文キャンセル（手仕舞い）
                            tejimai_long = client.close_all_positions()
                            api_count[time_count[0]] += 1

                            try:
                                while True:
                                    position_recheck = client.has_positions()
                                    api_count[time_count[0]] += 1

                                    if position_recheck == False:
                                        print('成行注文の手仕舞い完了')
                                        break
                                    else:
                                        print('成り行き注文の手仕舞い未完了')
                                        time.sleep(3)
                                        continue
                            except Exception as e:
                                print(e)
                                line_notify_exec(e, 'No.8')

                        else:
                            trades = ws_processor.get()
                            time.sleep(3.0)
                            continue

                    elif order_type == 'Short':
                        print('ポジション価格と最終価格の乖離 = ', kairi, ' > ', LOGIC_TYPE_SHORT_KAIRI, 'なら手仕舞い')

                        # 動的損切りロジック1(一度0から500逆方向を超えた後は、それ以降初めて0を跨ぐと手仕舞い)
                        if kairi > 500:
                            moving_losscut_flag1 = 1
                            print('moving_losscut_flag1を立てます')

                        if moving_losscut_flag1 == 1 and kairi < 0:
                            print('動的損切りロジックで手仕舞いします')

                        if kairi > LOGIC_TYPE_SHORT_KAIRI or (moving_losscut_flag1 == 1 and kairi < 0):
                            print('手仕舞いします')

                            # 指値キャンセル
                            client.cancel_all_child_orders()

                            try:
                                while True:
                                    # Activeなものを10件取得
                                    orders = client.child_orders(count=10, child_order_state=OrderState.ACTIVE)
                                    api_count[time_count[0]] += 1

                                    if orders == []:
                                        print('指値注文の手仕舞い完了')
                                        break
                                    else:
                                        print('指値注文の手仕舞い未完了')
                                        time.sleep(3)
                                        continue
                            except Exception as e:
                                print(e)
                                line_notify_exec(e, 'No.11')

                            # 成行買注文（手仕舞い）
                            client.close_all_positions()
                            api_count[time_count[0]] += 1

                            try:
                                while True:
                                    position_recheck = client.has_positions()
                                    api_count[time_count[0]] += 1

                                    if position_recheck == False:
                                        print('成り行き注文の手仕舞い完了')
                                        break
                                    elif position_recheck == True:
                                        print('成り行き注文の手仕舞い未完了')
                                        time.sleep(3)
                                        continue
                            except Exception as e:
                                print(e)
                                line_notify_exec(e, 'No.10')

                        else:
                            trades = ws_processor.get()
                            time.sleep(3.0)
                            continue

        except Exception as e:
            print(e)
            line_notify_exec(e, 'No.12')

        print('キューをクリアします')

        try:
            while True:
                trades = ws_processor.get()
                if trades is None:
                    print('Queueが空になりました')
                    break
        except Exception as e:
            print(e)
            line_notify_exec(e, 'No.13')

        print('キューのクリアが完了しました')

    ws_processor = WebSocketProcessor().add_ws(
        BinanceWS,
    ).run()

    print('---パラメータ確認---')
    print('Long閾値 = ', LONG_THRESHOLD)
    print('Short閾値 = ', SHORT_THRESHOLD)
    print('指値幅 = ±', MAKE_ADDSUB)
    print('Longロット = ', LOGIC_TYPE_LONG_LOT)
    print('損切り解離(Long) = ', LOGIC_TYPE_LONG_KAIRI)
    print('Shortロット = ', LOGIC_TYPE_SHORT_LOT)
    print('損切り解離(Short) = ', LOGIC_TYPE_SHORT_KAIRI)
    print('インターバル = ', INTERBAL)

    time.sleep(5)

    # ここがすべての始まり
    try:
        flag = 0

        while True:
            # print('----------')
            # print('api_count = ', sum(api_count))
            if sum(api_count) > 450:
                print('api制限回避のため1分')
                time.sleep(60)

            # フラグが立っていない場合
            if flag == 0:
                # print('分岐①in')
                # 時間経過のカウントを始める
                # print('時間カウント開始')
                time_start = time.perf_counter()

                try:
                    while True:
                        trades = ws_processor.get()
                        if trades == None:
                            continue
                        else:
                            break
                except Exception as e:
                    print(e)
                    line_notify_exec(e, 'No.1')

                # try:
                    # for trade in trades:

                        # trade_str = '%s %s %s %s %s %s' % (
                            # exchange_print(trade['ex_key'], padding=12),
                            # size_print(trade['size'], padding=10),
                            # price_print(trade['price'], padding=12),
                            # price_time_Binance(trade['time'], padding=16),
                            # rcv_time(trade['rcv_time'], padding=16),
                            # time.time(),
                        # )
                        # print(trade_str)

                # except Exception as e:
                    # print(e)
                    # line_Notify_exec(e, 'No.2')

                # 比較対象固定変数を設置
                # print('比較対象固定変数を新規設置')
                fixed_price = trades[0]['price']
                # print(fixed_price)

                # フラグを立てる
                flag = 1

            # フラグが立っている場合、かつ経過時間がINTERBAL未満の場合
            elif flag == 1 and (time.perf_counter() - time_start) < INTERBAL:

                # print('分岐②in')
                # print('比較対象変数 = ', fixed_price)

                try:
                    while True:
                        trades = ws_processor.get()
                        if trades == None:
                            continue
                        else:
                            break
                except Exception as e:
                    print(e)
                    line_notify_exec(e, 'No.3')

                try:
                    for trade in trades:

                        # trade_str = '%s %s %s %s %s %s' % (
                            # exchange_print(trade['ex_key'], padding=12),
                            # size_print(trade['size'], padding=10),
                            # price_print(trade['price'], padding=12),
                            # price_time_Binance(trade['time'], padding=16),
                            # rcv_time(trade['rcv_time'], padding=16),
                            # time.time(),
                        # )
                        # print(trade_str)
                        flag = logic_in_binance(trade)

                except Exception as e:
                    print(e)
                    line_notify_exec(e, 'No.14')



            # フラグが立っている場合、かつ経過時間がINTERBALを超過した場合
            elif flag == 1 and (time.perf_counter() - time_start) >= INTERBAL:

                # print('分岐③in')
                # print('フラグを下ろします')

                # フラグを下ろす
                flag = 0

    except KeyboardInterrupt:
        print('Closing sockets...')
        ws_processor.close()
        time.sleep(2.0)


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
    return color_string(exchange_string[0], color=exchange_string[1], padding=padding)


def color_string(string, color=255, padding=0):
    if padding:
        string = string.ljust(padding)
    return fg(color) + string + fg.rs


def size_print(size, padding=10):
    size_string = '%.4f' % size
    if size > 0.0:
        return color_string(size_string, color=118, padding=padding)
    return color_string(size_string, color=161, padding=padding)


def price_print(price, padding=10):
    price_string = '%.1f' % price
    return color_string(price_string, color=229, padding=padding)


def price_time_bitFlyer(time_string, padding=10):
    return color_string(time_string, color=250, padding=padding)


def price_time_Binance(unix_time, padding=10):
    time_string = '%d' % unix_time
    return color_string(time_string, color=250, padding=padding)


def rcv_time(unix_time, padding=10):
    time_string = '%d' % unix_time
    return color_string(time_string, color=250, padding=padding)

def now_time(unix_time, padding=10):
    return color_string(unix_time, color=250, padding=padding)

# -----------------------------------------------


def main():

    process_funcs = [
        receive_trades,
        time_counter,
        api_counter,
    ]

    if BOT_STATUS == 'RUN':

        processes = []
        for func in process_funcs:
            p = Process(target=func, args=())
            processes.append(p)

        for p in processes:
            p.start()

        for p in processes:
            p.join()

    elif BOT_STATUS == 'STOP':
        print('BOT_STATUSがSTOPです')


if __name__ == '__main__':
    main()
