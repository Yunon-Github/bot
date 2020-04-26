#!/usr/bin/python3
# -*- coding: utf-8 -*-
from pybitflyer import API
from pybitflyer.exception import AuthException
from enum import Enum, auto
from typing import Optional
from datetime import datetime
from functools import wraps

class Cond(Enum):
    LIMIT = auto()
    MARKET = auto()
    STOP = auto()
    STOP_LIMIT = auto()
    TRAIL = auto()

class Side(Enum):
    BUY = auto()
    SELL = auto()

class OrderState(Enum):
    ACTIVE = auto()
    COMPLETED = auto()
    CANCELED = auto()
    EXPIRED = auto()
    REJECTED = auto()

class TimeInForce(Enum):
    GTC = auto()  # Good 'Til Canceled
    IOC = auto()  # Immediate or Cancel
    FOK = auto()  # Fill or Kill

class Order:
    def __init__(self,
                 cond: Cond,
                 side: Side,
                 size: float,
                 price: Optional[int] = None,
                 trigger_price: Optional[int] = None,
                 offset: Optional[int] = None):
        self.cond = cond
        self.side = side
        self.size = custom_round(size, 8)
        self.size = size
        self.price = price
        self.trigger_price = trigger_price
        self.offset = offset

    def __str__(self):
        if self.cond == Cond.STOP or self.cond == Cond.STOP_LIMIT:
            return "{0} {1} {2} at {3}".format(self.cond.name, self.side.name, self.size, self.trigger_price)
        elif self.cond == Cond.TRAIL:
            return "{0} {1} {2} offset: {3}".format(self.cond.name, self.side.name, self.size, self.offset)
        else:
            return "{0} {1} {2} at {3}".format(self.cond.name, self.side.name, self.size, self.price)

    @classmethod
    def limit(cls, side: Side, size: float, price: int):
        return cls(cond=Cond.LIMIT, side=side, size=size, price=price)

    @classmethod
    def limit_buy(cls, size: float, price: int):
        return cls.limit(side=Side.BUY, size=size, price=price)

    @classmethod
    def limit_sell(cls, size: float, price: int):
        return cls.limit(side=Side.SELL, size=size, price=price)

    @classmethod
    def market(cls, side: Side, size: float):
        return cls(cond=Cond.LIMIT, side=side, size=size)

    @classmethod
    def market_buy(cls, size: float):
        return cls.market(side=Side.BUY, size=size)

    @classmethod
    def market_sell(cls, size: float):
        return cls.market(side=Side.SELL, size=size)

    @classmethod
    def stop(cls, side: Side, size: float, trigger_price: int):
        return cls(cond=Cond.STOP, side=side, size=size, trigger_price=trigger_price)

    @classmethod
    def stop_buy(cls, size: float, trigger_price: int):
        return cls.stop(side=Side.BUY, size=size, trigger_price=trigger_price)

    @classmethod
    def stop_sell(cls, size: float, trigger_price: int):
        return cls.stop(side=Side.SELL, size=size, trigger_price=trigger_price)

    @classmethod
    def stop_limit(cls, side: Side, size: float, price: int, trigger_price: int):
        return cls(cond=Cond.STOP_LIMIT, side=side, size=size, price=price, trigger_price=trigger_price)

    @classmethod
    def stop_limit_buy(cls, size: float, price: int, trigger_price: int):
        return cls.stop_limit(side=Side.BUY, size=size, price=price, trigger_price=trigger_price)

    @classmethod
    def stop_limit_sell(cls, size: float, price: int, trigger_price: int):
        return cls.stop_limit(side=Side.SELL, size=size, price=price, trigger_price=trigger_price)

    @classmethod
    def trail(cls, side: Side, size: float, offset: int):
        return cls(cond=Cond.TRAIL, side=side, size=size, offset=offset)

    @classmethod
    def trail_buy(cls, size: float, offset: int):
        return cls.trail(side=Side.BUY, size=size, offset=offset)

    @classmethod
    def trail_sell(cls, size: float, offset: int):
        return cls.trail(side=Side.SELL, size=size, offset=offset)

    def params(self, product_code: str):
        params = {
            "product_code": product_code,
            "condition_type": self.cond.name,
            "side": self.side.name,
            "size": self.size
        }

        if self.price is not None:
            params["price"] = self.price

        if self.trigger_price is not None:
            params["trigger_price"] = self.trigger_price

        if self.offset is not None:
            params["offset"] = self.offset

        return params

def request(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        args[0].requested()
        return result
    return wrapper

class BFFXClient:
    def __init__(self,
                 api_key: str,
                 api_secret: str,
                 timeout: Optional[float] = None,
                 product_code: str = "FX_BTC_JPY",
                 logger=None,
                 request_callback=None):
        """
        Initializer

        :param api_key: bitFlyerのAPI Key
        :param api_secret: bitFlyerのAPI Secret
        :param timeout: requestsのtimeout [s]
        :param product_code: bitFlyerのproduct_code. 現物/先物の指定も可能.
        :param logger: ログを出力させる場合はloggingのloggerを設定. Noneで出力なし.
        :param request_callback: API request直後に特定の処理を呼び出したい場合はcallbackとして登録.
        """
        self.__client = API(api_key=api_key, api_secret=api_secret, timeout=timeout)
        self.__product_code = product_code
        self.__logger = logger
        self.request_callback = request_callback

    # == HTTP Public API ==============================================

    @request
    def markets(self):
        """
        マーケットの一覧
        """
        endpoint = "/v1/getmarkets"
        return self.__client.request(endpoint=endpoint, method="GET")

    @request
    def board(self):
        """
        板情報
        """
        return self.__client.board(product_code=self.__product_code)

    @request
    def ticker(self):
        """
        Ticker
        """
        return self.__client.ticker(product_code=self.__product_code)

    @request
    def executions(self, count: Optional[int] = None, before: Optional[int] = None, after: Optional[int] = None):
        """
        約定履歴（market全体）
        """
        params = BFFXClient.__format_params(product_code=self.__product_code, count=count, before=before, after=after)
        return self.__client.executions(**params)

    @request
    def board_state(self):
        """
        板の状態
        """
        return self.__client.getboardstate(product_code=self.__product_code)

    @request
    def health(self):
        """
        取引所の状態
        """
        return self.__client.gethealth(product_code=self.__product_code)

    @request
    def chats(self, from_date: Optional[datetime] = None):
        """
        チャット
        NOTE: from_dateにNoneを指定すると、データが大きいため取得に時間がかかります

        :param from_date: UTC時間でdatetimeを指定. Noneを渡すと5日前からのログを返却.
        :return: chat logs
        """
        date_text = from_date.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
        return self.__client.getchats(from_date=date_text)

    # == Utility methods for HTTP Public API ==========================

    @request
    def mid_price(self) -> float:
        """
        mid_price（中間価格）
        """
        return self.__client.board(product_code=self.__product_code)["mid_price"]

    @request
    def ltp(self) -> int:
        """
        ltp（最終取引価格）
        """
        return int(self.__client.ticker(product_code=self.__product_code)["ltp"])

    @request
    def best_ask(self) -> int:
        """
        best_ask（最高買い価格）
        """
        return int(self.__client.ticker(product_code=self.__product_code)["best_ask"])

    @request
    def best_bid(self) -> int:
        """
        best_bid（最低売り価格）
        """
        return int(self.__client.ticker(product_code=self.__product_code)["best_bid"])

    # == HTTP Private API - [API] =====================================

    @request
    def permissions(self) -> [str]:
        """
        API キーの権限を取得
        """
        self.__check_auth()
        endpoint = "/v1/me/getpermissions"
        return self.__client.request(endpoint)

    # == HTTP Private API - [Assets] ==================================

    @request
    def balance(self):
        """
        資産残高を取得
        """
        return self.__client.getbalance()

    @request
    def collateral(self):
        """
        証拠金の状態を取得
        """
        return self.__client.getcollateral()

    @request
    def collateral_accounts(self):
        """
        通貨別の証拠金の数量を取得
        """
        self.__check_auth()
        endpoint = "/v1/me/getcollateralaccounts"
        return self.__client.request(endpoint)

    # == HTTP Private API - [Deposits and Withdrawals] ================

    @request
    def addresses(self):
        """
        預入用アドレス取得
        """
        return self.__client.getaddresses()

    @request
    def coinins(self, count: Optional[int] = None, before: Optional[int] = None, after: Optional[int] = None):
        """
        仮想通貨預入履歴
        """
        params = BFFXClient.__format_params(count=count, before=before, after=after)
        return self.__client.getcoinins(**params)

    @request
    def coinouts(self, count: Optional[int] = None, before: Optional[int] = None, after: Optional[int] = None):
        """
        仮想通貨送付履歴
        """
        params = BFFXClient.__format_params(count=count, before=before, after=after)
        return self.__client.getcoinouts(**params)

    @request
    def bank_accounts(self):
        """
        銀行口座一覧取得
        """
        return self.__client.getbankaccounts()

    @request
    def deposits(self, count: Optional[int] = None, before: Optional[int] = None, after: Optional[int] = None):
        """
        入金履歴
        """
        params = BFFXClient.__format_params(count=count, before=before, after=after)
        return self.__client.getdeposits(**params)

    @request
    def withdraw(self, bank_account_id: str, amount: int, code: Optional[str]):
        """
        出金
        :param bank_account_id: 出金先の口座の id
        :param amount: 出金する数量
        :param code: 二段階認証の確認コード. 出金時の二段階認証を設定している場合のみ必要.
        """
        params = BFFXClient.__format_params(
            currency_code="JPY",
            bank_account_id=bank_account_id,
            amount=amount,
            code=code
        )
        return self.__client.withdraw(**params)

    @request
    def withdrawals(self,
                    count: Optional[int] = None,
                    before: Optional[int] = None,
                    after: Optional[int] = None,
                    message_id: Optional[str] = None):
        """
        出金履歴
        """
        params = BFFXClient.__format_params(
            count=count,
            before=before,
            after=after,
            message_id=message_id
        )
        return self.__client.getwithdrawals(**params)

    # == HTTP Private API - [Trading] =================================

    def limit_buy(self,
                  size: float,
                  price: int,
                  minute_to_expire: Optional[int] = None,
                  time_in_force: Optional[TimeInForce] = None):
        return self.__send_limit_child_order(
            side=Side.BUY,
            size=size,
            price=price,
            minute_to_expire=minute_to_expire,
            time_in_force=time_in_force
        )

    def limit_sell(self,
                   size: float,
                   price: int,
                   minute_to_expire: Optional[int] = None,
                   time_in_force: Optional[TimeInForce] = None):
        return self.__send_limit_child_order(
            side=Side.SELL,
            size=size,
            price=price,
            minute_to_expire=minute_to_expire,
            time_in_force=time_in_force
        )

    def market_buy(self, size: float):
        return self.__send_market_child_order(side=Side.BUY, size=size)

    def market_sell(self, size: float):
        return self.__send_market_child_order(side=Side.SELL, size=size)

    @request
    def cancel_child_order(self,
                           child_order_id: Optional[str] = None,
                           child_order_acceptance_id: Optional[str] = None):
        """
        子注文をキャンセルする

        NOTE: order_id を指定する場合は child_order_id もしくは child_order_acceptance_id のどちらか片方を指定
        """
        self.__info("Cancel child order")
        params = BFFXClient.__format_params(
            product_code=self.__product_code,
            child_order_id=child_order_id,
            child_order_acceptance_id=child_order_acceptance_id
        )
        self.__client.cancelchildorder(**params)

    def stop_buy(self,
                 size: float,
                 trigger_price: int,
                 minute_to_expire: Optional[int] = None,
                 time_in_force: Optional[TimeInForce] = None):
        order = Order.stop_buy(size=size, trigger_price=trigger_price)
        return self.__send_special_order(order=order, minute_to_expire=minute_to_expire, time_in_force=time_in_force)

    def stop_sell(self,
                  size: float,
                  trigger_price: int,
                  minute_to_expire: Optional[int] = None,
                  time_in_force: Optional[TimeInForce] = None):
        order = Order.stop_sell(size=size, trigger_price=trigger_price)
        return self.__send_special_order(order=order, minute_to_expire=minute_to_expire, time_in_force=time_in_force)

    def stop_limit_buy(self,
                       size: float,
                       price: int,
                       trigger_price: int,
                       minute_to_expire: Optional[int] = None,
                       time_in_force: Optional[TimeInForce] = None):
        order = Order.stop_limit_buy(size=size, price=price, trigger_price=trigger_price)
        return self.__send_special_order(order=order, minute_to_expire=minute_to_expire, time_in_force=time_in_force)

    def stop_limit_sell(self,
                        size: float,
                        price: int,
                        trigger_price: int,
                        minute_to_expire: Optional[int] = None,
                        time_in_force: Optional[TimeInForce] = None):
        order = Order.stop_limit_sell(size=size, price=price, trigger_price=trigger_price)
        return self.__send_special_order(order=order, minute_to_expire=minute_to_expire, time_in_force=time_in_force)

    def trail_buy(self,
                  size: float,
                  offset: int,
                  minute_to_expire: Optional[int] = None,
                  time_in_force: Optional[TimeInForce] = None):
        order = Order.trail_buy(size=size, offset=offset)
        return self.__send_special_order(order=order, minute_to_expire=minute_to_expire, time_in_force=time_in_force)

    def trail_sell(self,
                   size: float,
                   offset: int,
                   minute_to_expire: Optional[int] = None,
                   time_in_force: Optional[TimeInForce] = None):
        order = Order.trail_sell(size=size, offset=offset)
        return self.__send_special_order(order=order, minute_to_expire=minute_to_expire, time_in_force=time_in_force)

    def ifd(self,
            first: Order,
            second: Order,
            minute_to_expire: Optional[int] = None,
            time_in_force: Optional[TimeInForce] = None):
        """
        IFD 注文.
        一度に2つの注文を出し、最初の注文が約定したら2つ目の注文が自動的に発注される注文方法.

        :param first: 1つ目の注文
        :param second: 2つ目の注文
        :param minute_to_expire: 期限切れまでの時間を分で指定. default: 43200分 (30 日間).
        :param time_in_force: 執行数量条件. GTC, IOC, FOKのいずれかをTimeInForce型で指定. default: GTC
        """
        return self.__send_special_order_pair(
            order_method="IFD",
            first=first,
            second=second,
            minute_to_expire=minute_to_expire,
            time_in_force=time_in_force
        )

    def oco(self,
            first: Order,
            second: Order,
            minute_to_expire: Optional[int] = None,
            time_in_force: Optional[TimeInForce] = None):
        """
        OCO 注文.
        2つの注文を同時に出し、一方の注文が成立した際にもう一方の注文が自動的にキャンセルされる注文方法.

        :param first: 1つ目の注文
        :param second: 2つ目の注文
        :param minute_to_expire: 期限切れまでの時間を分で指定. default: 43200分 (30 日間).
        :param time_in_force: 執行数量条件. GTC, IOC, FOKのいずれかをTimeInForce型で指定. default: GTC
        """
        return self.__send_special_order_pair(
            order_method="OCO",
            first=first,
            second=second,
            minute_to_expire=minute_to_expire,
            time_in_force=time_in_force
        )

    def ifdoco(self,
               ifd: Order,
               oco1: Order,
               oco2: Order,
               minute_to_expire: Optional[int] = None,
               time_in_force: Optional[TimeInForce] = None):
        """
        IFDOCO 注文.
        最初の注文が約定した後に自動的にOCO注文が発注される注文方法

        :param ifd: IFD注文の1つ目の注文
        :param oco1: OCO注文の1つ目の注文 （IFD注文の2つ目としてのOCO）
        :param oco2: OCO注文の2つ目の注文 （IFD注文の2つ目としてのOCO）
        :param minute_to_expire: 期限切れまでの時間を分で指定. default: 43200分 (30 日間).
        :param time_in_force: 執行数量条件. GTC, IOC, FOKのいずれかをTimeInForce型で指定. default: GTC
        """
        order_method = "IFDOCO"
        self.__info("Send {}".format(order_method))
        self.__info("IFD: {}".format(ifd))
        self.__info("OCO1: {}".format(oco1))
        self.__info("OCO2: {}".format(oco2))
        parameters = [
            ifd.params(product_code=self.__product_code),
            oco1.params(product_code=self.__product_code),
            oco2.params(product_code=self.__product_code)
        ]
        params = BFFXClient.__format_params(
            order_method=order_method,
            parameters=parameters,
            minute_to_expire=minute_to_expire,
            time_in_force=time_in_force and time_in_force.name
        )
        return self.__client.sendparentorder(**params)

    @request
    def cancel_parent_order(self,
                            parent_order_id: Optional[str] = None,
                            parent_order_acceptance_id: Optional[str] = None):
        """
        親注文をキャンセルする

        NOTE: order_id を指定する場合は child_order_id もしくは child_order_acceptance_id のどちらか片方を指定
        """
        self.__info("Cancel parent order")
        params = BFFXClient.__format_params(
            product_code=self.__product_code,
            parent_order_id=parent_order_id,
            parent_order_acceptance_id=parent_order_acceptance_id
        )
        return self.__client.cancelparentorder(**params)

    @request
    def cancel_all_child_orders(self):
        """
        すべての注文をキャンセル
        """
        self.__info("Cancel all child orders")
        return self.__client.cancelallchildorders(product_code=self.__product_code)

    @request
    def child_orders(self,
                     count: Optional[int] = None,
                     before: Optional[int] = None,
                     after: Optional[int] = None,
                     child_order_state: Optional[OrderState] = None,
                     child_order_id: Optional[str] = None,
                     child_order_acceptance_id: Optional[str] = None,
                     parent_order_id: Optional[str] = None):
        """
        注文の一覧を取得
        """
        self.__info("Get child orders")
        child_order_state = None if child_order_state is None else child_order_state.name
        params = BFFXClient.__format_params(
            product_code=self.__product_code,
            count=count,
            before=before,
            after=after,
            child_order_state=child_order_state,
            child_order_id=child_order_id,
            child_order_acceptance_id=child_order_acceptance_id,
            parent_order_id=parent_order_id
        )
        return self.__client.getchildorders(**params)

    @request
    def parent_orders(self,
                      count: Optional[int] = None,
                      before: Optional[int] = None,
                      after: Optional[int] = None,
                      parent_order_state: Optional[OrderState] = None):
        """
        親注文の一覧を取得
        """
        self.__info("Get parent orders")
        parent_order_state = None if parent_order_state is None else parent_order_state.name
        params = BFFXClient.__format_params(
            product_code=self.__product_code,
            count=count,
            before=before,
            after=after,
            parent_order_state=parent_order_state
        )
        return self.__client.getparentorders(**params)

    @request
    def parent_order(self, parent_order_id: Optional[str] = None, parent_order_acceptance_id: Optional[str] = None):
        """
        親注文の詳細を取得

        NOTE: order_id を指定する場合は child_order_id もしくは child_order_acceptance_id のどちらか片方を指定
        """
        self.__info("Get parent order")
        params = BFFXClient.__format_params(
            product_code=self.__product_code,
            parent_order_id=parent_order_id,
            parent_order_acceptance_id=parent_order_acceptance_id
        )
        return self.__client.getparentorder(**params)

    @request
    def my_executions(self,
                      count: Optional[int] = None,
                      before: Optional[int] = None,
                      after: Optional[int] = None,
                      child_order_id: Optional[str] = None,
                      child_order_acceptance_id: Optional[str] = None):
        """
        自分の約定一覧を取得

        NOTE: order_id を指定する場合は child_order_id もしくは child_order_acceptance_id のどちらか片方を指定
        """
        self.__info("Get my executions")
        params = BFFXClient.__format_params(
            product_code=self.__product_code,
            count=count,
            before=before,
            after=after,
            child_order_id=child_order_id,
            child_order_acceptance_id=child_order_acceptance_id
        )
        return self.__client.getexecutions(**params)

    @request
    def positions(self):
        """
        建玉の一覧を取得
        """
        return self.__client.getpositions(product_code=self.__product_code)

    @request
    def collateral_history(self, count: int, before: Optional[int] = None, after: Optional[int] = None):
        """
        証拠金の変動履歴を取得
        """
        params = BFFXClient.__format_params(count=count, before=before, after=after)
        return self.__client.getcollateralhistory(**params)

    @request
    def trading_commission(self):
        """
        取引手数料を取得
        """
        return self.__client.gettradingcommission(product_code=self.__product_code)

    # == Utility methods for HTTP Private API =========================

    def has_positions(self) -> bool:
        """
        ポジションを保持しているかどうかをboolで取得
        """
        positions = self.positions()
        return positions != []

    def position_size(self) -> float:
        """
        Position sizeを取得

        売りポジション -> 負の値をreturn
        買いポジション -> 正の値をreturn
        :return: 小数点以下第8位までで丸め込んだposition size
        """
        positions = self.positions()

        size = 0
        for position in positions:
            if position["side"] == "BUY":
                size += position["size"]
            else:
                size -= position["size"]

        return custom_round(size, 8)

    def active_child_orders(self,
                            count: Optional[int] = None,
                            before: Optional[int] = None,
                            after: Optional[int] = None):
        """
        ACTIVEな子注文を取得
        """
        return self.child_orders(count=count, before=before, after=after, child_order_state=OrderState.ACTIVE)

    def active_parent_orders(self,
                             count: Optional[int] = None,
                             before: Optional[int] = None,
                             after: Optional[int] = None):
        """
        ACTIVEな親注文を取得
        """
        return self.parent_orders(count=count, before=before, after=after, parent_order_state=OrderState.ACTIVE)

    def cancel_all_unexecuted_parent_orders(self):
        """
        未約定な親注文を全てキャンセル（100件を超える場合は残ります）
        """
        self.__info("Cancel all unexecuted parent orders")
        orders = self.active_parent_orders()
        responses = []
        for order in orders:
            if order["executed_size"] == 0:
                order_id = order["parent_order_id"]
                response = self.cancel_parent_order(parent_order_id=order_id)
                responses.append(response)
        return responses

    def close_all_positions(self):
        """
        保持しているポジション数を0にするよう成行注文
        """
        self.__info("Close all positions")
        size = self.position_size()

        # 成りで全ポジションをClose
        if size == 0:
            self.__warning("Position does not exist.")
        elif size > 0:
            return self.market_sell(size=size)
        else:
            return self.market_buy(size=abs(size))

    # == Private methods ==============================================

    @request
    def __send_limit_child_order(self,
                                 side: Side,
                                 size: float,
                                 price: int,
                                 minute_to_expire: Optional[int] = None,
                                 time_in_force: Optional[TimeInForce] = None):
        size = custom_round(size, 8)
        self.__info("Send LIMIT {0} {1}BTC at {2}".format(side.name, size, price))
        params = BFFXClient.__format_params(
            product_code=self.__product_code,
            child_order_type="LIMIT",
            side=side.name,
            size=size,
            price=price,
            minute_to_expire=minute_to_expire,
            time_in_force=time_in_force and time_in_force.name
        )
        return self.__client.sendchildorder(**params)

    @request
    def __send_market_child_order(self, side: Side, size: float):
        size = custom_round(size, 8)
        self.__info("Send MARKET {0} {1}BTC".format(side.name, size))
        params = {
            "product_code": self.__product_code,
            "child_order_type": "MARKET",
            "side": side.name,
            "size": size
        }
        return self.__client.sendchildorder(**params)

    @request
    def __send_special_order(self,
                             order: Order,
                             minute_to_expire: Optional[int] = None,
                             time_in_force: Optional[TimeInForce] = None):
        self.__info("Send {}".format(order))
        parameters = [
            order.params(product_code=self.__product_code)
        ]
        params = BFFXClient.__format_params(
            order_method="SIMPLE",
            parameters=parameters,
            minute_to_expire=minute_to_expire,
            time_in_force=time_in_force and time_in_force.name
        )
        return self.__client.sendparentorder(**params)

    @request
    def __send_special_order_pair(self,
                                  order_method: str,
                                  first: Order,
                                  second: Order,
                                  minute_to_expire: Optional[int] = None,
                                  time_in_force: Optional[TimeInForce] = None):
        self.__info("Send {}".format(order_method))
        self.__info("First: {}".format(first))
        self.__info("Second: {}".format(second))
        parameters = [
            first.params(product_code=self.__product_code),
            second.params(product_code=self.__product_code)
        ]
        params = BFFXClient.__format_params(
            order_method=order_method,
            parameters=parameters,
            minute_to_expire=minute_to_expire,
            time_in_force=time_in_force and time_in_force.name
        )
        return self.__client.sendparentorder(**params)

    # == Log ==========================================================

    def __error(self, obj):
        if self.__logger is not None:
            self.__logger.error(obj)

    def __warning(self, obj):
        if self.__logger is not None:
            self.__logger.warning(obj)

    def __info(self, obj):
        if self.__logger is not None:
            self.__logger.info(obj)

    # == Other ========================================================

    def __check_auth(self):
        if not all([self.__client.api_key, self.__client.api_secret]):
            raise AuthException()

    def requested(self):
        self.request_callback and self.request_callback()

    @staticmethod
    def __format_params(**params):
        formatted_params = {}
        for key, value in params.items():
            if value is None:
                continue
            formatted_params[key] = value
        return formatted_params

def custom_round(val, digit=0):
    p = 10 ** digit
    return (val * p * 2 + 1) // 2 / p