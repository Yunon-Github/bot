# import pybitflyer
from bffx_client import BFFXClient, OrderState
import time
from threading import Thread
import influxdb
import pandas as pd
import pybitflyer

# BFFXClient のインスタンスを生成
client = BFFXClient(
    api_key="XwtMm31szNgQPAfgTH1ZjY",  # bitFlyerのAPI Key
    api_secret="jxQ09ydZWxfAe6CB3U3fvVMJSNjPaEaSJiinLn5Qu9k="  # bitFlyerのAPI Secret
)

# bitFlyerAPIキーの設定
api = pybitflyer.API(
api_key="XwtMm31szNgQPAfgTH1ZjY",
api_secret = "jxQ09ydZWxfAe6CB3U3fvVMJSNjPaEaSJiinLn5Qu9k="
)


def error_checker(r):
    if 'child_order_acceptance_id' in r:
        return '注文成功'
    elif 'error_message' in r:
        return '注文失敗', r['error_message']
    else:
        return '例外です'


def error_test():
    # 成行買注文
    # btc_Long_taker = {'child_order_acceptance_id': 'JRF20200425-134056-381546'}
    btc_Long_taker = {'status': -200, 'error_message': 'This is the error', 'data': None}

    result = error_checker(btc_Long_taker)
    print(result[0])


def bffxclient_test():
    x = client.has_positions()
    print(x)

yakujou_data = pd.read_csv('test.csv', sep=',')

def tejimai():
    #成行注文の手仕舞いLot確認
    try:
        tejimai_lot = 0
        lot_parts = 0

        while True:

            tejimai_lot_check = api.getpositions(product_code='FX_BTC_JPY')

            if tejimai_lot_check != []:

                for tejimai_lot_check_List in tejimai_lot_check:
                    lot_parts = tejimai_lot_check_List['size']
                    tejimai_lot += lot_parts
            else:
                tine.sleep(2)
                continue

            print(tejimai_lot)

    except Exception as e:
        print(e)

def list_check():
    test = []
    print(test[0])

def pandas_check():

    print(yakujou_data['key'][19])

def kakunin():
    a =time.perf_counter()
    print(a)

def re():
    a = 4
    return 0, a

def time_sokutei():
    # 時間計測開始
    time_sta = time.perf_counter()
    # 処理を書く（ここでは5秒停止する）
    time.sleep(5)
    # 時間計測終了
    time_end = time.perf_counter()
    # 経過時間（秒）
    tim = time_end- time_sta

    print(tim)
    #[結果] 4.99997752884417

def trade_complete_check():

    position_price = 710000
    #トレード完了チェック
    try:
        while True:
            ticker = api.ticker(product_code="FX_BTC_JPY")
            print("[FX_BTC_JPY] の最終価格 : " + "{}".format(ticker["ltp"]) + " 円")
            print('ポジション価格は ', position_price, '円')
            kairi = ticker['ltp'] - position_price
            print('ポジション価格と最終価格の乖離 = ', kairi)


            #500秒の時間稼ぎ
            for i in range (500):
                print('注文を確認中です...')
                time.sleep(1.0)

    except Exception as e:
        print(e)

def bf_order_nariyuki():
	buy_btc_Long_nariyuki = api.sendchildorder(
        product_code='FX_BTC_JPY',
        child_order_type='MARKET',
        side='BUY',
        size=0.01,
        minute_to_expire=1000,
        time_in_force='GTC')

def listtest():
    position_count = 0
    position = [{'product_code': 'FX_BTC_JPY', 'side': 'SELL', 'price': 792805.0, 'size': 0.01, 'commission': 0.0, 'swap_point_accumulate': 0.0, 'require_collateral': 7928.05, 'open_date': '2020-04-07T04:56:58.307', 'leverage': 1.0, 'pnl': -1.95, 'sfd': 0.0},{'product_code': 'FX_BTC_JPY', 'side': 'SELL', 'price': 792805.0, 'size': 0.01, 'commission': 0.0, 'swap_point_accumulate': 0.0, 'require_collateral': 7928.05, 'open_date': '2020-04-07T04:56:58.307', 'leverage': 1.0, 'pnl': -1.95, 'sfd': 0.0}]

    for positionList in position:

        position_price = positionList['price']
        print(position_price)
        position_size = positionList['size']
        print(position_size)


def sashine():
    btc_Long_maker = api.sendchildorder(
        product_code='FX_BTC_JPY',
        child_order_type='LIMIT',
        side='BUY',
        size=0.01,
        price=600000,
        minute_to_expire=1000,
        time_in_force='GTC')

    print(btc_Long_maker)
    time.sleep(10.0)
    cancel_sashine()

def cancel_sashine():
    orders = api.getchildorders(product_code='FX_BTC_JPY' ,child_order_state='ACTIVE')
    print(orders)

    #cancel_order = api.cancelchildorder(product_code='FX_BTC_JPY' , child_order_id =orders[0]["child_order_id"])
    #print(cancel_order)

def bF_get_position():
    print('ポジションを確認します')
    position = api.getpositions(product_code='FX_BTC_JPY')
    print(position)

def influxDB_test(measurement, value):
    client = influxdb.InfluxDBClient(port='8086', username='Yunon', password='drew520mice231')
    show_database = client.get_list_database()
    client.switch_database('bot')

    data = [{'measurement':measurement,
            'tags':{'botname':'Bi-bF-soukan'},
            'fields':{'count':float(value)}
            }]
    res = client.write_points(data)

    query = client.query('select * from api_count')

    print(query)

bffxclient_test()
#list_check()
#influxDB_test('api_count', 777)
#kakunin()
#cancel_sashine()
#trade_complete_check()
#bF_get_position()
