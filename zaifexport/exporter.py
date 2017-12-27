import csv
import sys
import time
from collections import OrderedDict
from datetime import datetime
from typing import Generator, Callable, Iterator, Union

import ccxt
import pytz
from ccxt import ExchangeError

JST = pytz.timezone('Asia/Tokyo')


class Exporter:
    ORDER_MAP = dict(bid='買', ask='売', both='自己')
    FUTURE_MAP = {
        1: 'AirFX',
        2: '四半期6月(07-01) ',
        3: '四半期9月(10-01)',
        4: '四半期12月(01-01)',
        5: '四半期3月(04-01)',
    }

    def __init__(self, api_key: str, api_secret: str, wait_interval: float):
        self._delegate = ccxt.zaif(config=dict(apiKey=api_key, secret=api_secret))
        self._delegate.nonce = self.nonce
        self._wait_interval = wait_interval

    @classmethod
    def nonce(cls):
        time.sleep(0.001)
        return time.time()

    def __getattr__(self, item):
        attr = getattr(self._delegate, item)
        if not callable(attr):
            return attr

        def wrapper(*args, **kwargs):
            while True:
                try:
                    return attr(*args, **kwargs)
                except ExchangeError as e:
                    s = str(e)
                    if 'time wait restriction, please try later.' in s:
                        print('rate limit exceeded. wait and retry...', file=sys.stderr)
                        time.sleep(self._wait_interval)
                        pass
                    else:
                        raise

        return wrapper

    @classmethod
    def get_history(cls, fn: Callable[[dict], dict], parse_fn: Callable[[dict], Iterator[dict]],
                    **kwargs) -> Generator[dict, None, None]:
        from_i = 0
        last_id = int(1e10)
        params = kwargs.copy()
        while True:
            params['from'] = from_i
            res = fn(params)['return']
            if not len(res):
                break
            for k, v in sorted(res.items(), key=lambda _x: int(_x[0]), reverse=True):
                k = int(k)
                v['id'] = k
                if k < last_id:
                    for x in parse_fn(v):
                        yield x
                    last_id = k
            from_i += len(res)

    @classmethod
    def convert_timestamp(cls, timestamp: Union[int, float], tz: pytz.timezone = JST) -> str:
        timestamp = float(timestamp)
        return pytz.UTC.localize(datetime.utcfromtimestamp(timestamp)).astimezone(tz).isoformat()

    @classmethod
    def write_csv(cls, gen: Generator[dict, None, None], file):
        writer = None
        for data in gen:
            if not writer:
                writer = csv.DictWriter(file, fieldnames=tuple(data.keys()))
                writer.writeheader()
            writer.writerow(data)

    def export_spot(self) -> Generator[dict, None, None]:
        markets = self.load_markets()
        for market in sorted(markets.values(), key=lambda x: x['id']):
            def parse(trade: dict) -> Iterator[dict]:
                """
                "182": {
                    "currency_pair": "btc_jpy",
                    "action": "bid",
                    "amount": 0.03,
                    "price": 56000,
                    "fee": 0,
                    "your_action": "ask",
                    "bonus": 1.6,
                    "timestamp": 1402018713,
                    "comment" : "demo"
                }
                """
                x = OrderedDict()
                is_taker = trade['action'] == trade['your_action']
                x['分類'] = '現物'
                x['ID'] = trade['id']
                x['日時'] = self.convert_timestamp(trade['timestamp'])
                x['通貨ペア'] = '/'.join(trade['currency_pair'].upper().split('_'))
                x['注文種別'] = self.ORDER_MAP[trade['your_action']]
                x['TAKER/MAKER'] = 'TAKER' if is_taker else 'MAKER'
                x['価格'] = trade['price']
                x['数量'] = trade['amount']
                x['手数料'] = trade['fee_amount']
                x['ボーナス'] = trade['bonus']
                x['コメント'] = trade['comment']

                results = []
                if trade['your_action'] == 'both':
                    if trade['action'] == 'bid':
                        # 買い
                        x['注文種別'] = '自己買'
                        x['TAKER/MAKER'] = 'TAKER'
                        results.append(x.copy())
                        x['注文種別'] = '自己売'
                        x['TAKER/MAKER'] = 'MAKER'
                        results.append(x.copy())
                    elif trade['action'] == 'ask':
                        # 売り
                        x['注文種別'] = '自己売'
                        x['TAKER/MAKER'] = 'TAKER'
                        results.append(x.copy())
                        x['注文種別'] = '自己買'
                        x['TAKER/MAKER'] = 'MAKER'
                        results.append(x.copy())
                    else:
                        assert False, 'unknown action: {}'.format(trade)
                else:
                    results.append(x)
                return results

            currency_pair = market['id']
            yield from self.get_history(self.privatePostTradeHistory, parse, currency_pair=currency_pair)

    def _export_margin_or_future(self, **kwargs) -> Generator[dict, None, None]:
        def parse(trade: dict) -> Iterator[dict]:
            """
            "182": {
                "group_id": 1,
                "currency_pair": "btc_jpy",
                "action": "bid",
                "leverage": 2.5,
                "price": 110005,
                "limit": 130000,
                "stop": 90000,
                "amount": 0.03,
                "fee_spent": 0,
                "timestamp": 1402018713,
                "term_end": 1404610713,
                "timestamp_closed": 1402019000,
                "deposit": 35.76 ,
                "deposit_jpy": 35.76,
                "refunded": 35.76 ,
                "refunded_jpy": 35.76,
                "swap": 0,
            }
            group_id	グループID	int
            currency_pair	通貨ペア	str
            action	bid(買い) or ask(売り)	str
            amount	数量	float
            price	価格	float
            limit	リミット価格	float
            stop	ストップ価格	float
            timestamp	発注日時	UNIX_TIMESTAMP
            term_end	注文の有効期限	UNIX_TIMESTAMP
            leverage	レバレッジ	float
            fee_spent	支払い手数料	float
            timestamp_closed	クローズ日時	UNIX_TIMESTAMP
            price_avg	建玉平均価格	float
            amount_done	建玉数	float
            close_avg	決済平均価格	float
            close_done	決済数	float
            deposit_xxx	実際にデポジットした額(xxxは通貨コード）	float
            deposit_price_xxx	デポジット時計算レート(xxxは通貨コード）	float
            refunded_xxx	実際に返却した額(xxxは通貨コード）	float
            refunded_price_xxx	実際に返却した額(xxxは通貨コード）	float
            swap	受け取ったスワップの額(AirFXのみ）	float
            guard_fee	追証ガード手数料(信用取引のみ)	float
            """
            x = OrderedDict()
            is_executed = 'amount_done' in trade
            if 'group_id' in trade:
                x['分類'] = '先物'
                x['先物グループ'] = self.FUTURE_MAP[trade['group_id']]
            else:
                x['分類'] = '信用'
            x['ID'] = trade['id']
            x['発注日時'] = self.convert_timestamp(trade['timestamp'])
            x['決済日時'] = self.convert_timestamp(trade['timestamp_closed'])
            x['通貨ペア'] = '/'.join(trade['currency_pair'].upper().split('_'))
            if is_executed:
                x['ステータス'] = '成立'
            else:
                x['ステータス'] = '取消済み（建玉不成立）'
            x['注文種別'] = self.ORDER_MAP[trade['action']]
            x['数量'] = trade['amount']
            x['価格'] = trade['price']
            x['リミット価格'] = trade.get('limit')
            x['ストップ価格'] = trade.get('stop')
            x['支払い手数料'] = trade['fee_spent']
            x['建玉平均価格'] = trade.get('price_avg')
            x['建玉数'] = trade.get('amount_done')
            x['決済平均価格'] = trade.get('close_avg')
            x['決済数'] = trade.get('close_done')
            x['スワップ'] = trade.get('swap')
            swap = trade.get('swap', 0)
            x['追証ガード手数料(信用取引のみ)'] = trade.get('guard_fee')
            guard_fee = trade.get('guard_fee', 0)
            if is_executed:
                pnl = trade['close_avg'] * trade['close_done'] - trade['price_avg'] * trade['amount_done']
                pnl = pnl if trade['action'] == 'bid' else -pnl
                pnl_with_fee_swap = pnl + swap - guard_fee - trade['fee_spent']
            else:
                pnl = None
                pnl_with_fee_swap = None
            x['ポジション損益'] = pnl
            x['ポジション損益(手数料・スワップ込み)'] = pnl_with_fee_swap
            return [x]

        yield from self.get_history(self.tlapiPostGetPositions, parse, **kwargs)

    def export_margin(self) -> Generator[dict, None, None]:
        yield from self._export_margin_or_future(type='margin')

    def export_future(self) -> Generator[dict, None, None]:
        for group_id in sorted(map(lambda x: x['id'], self.fapiGetGroupsGroupId(dict(group_id='all')))):
            yield from self._export_margin_or_future(type='futures', group_id=group_id)
