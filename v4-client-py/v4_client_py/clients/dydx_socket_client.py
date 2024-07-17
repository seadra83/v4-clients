import json
import threading
import time
from enum import Enum
from typing import Callable, Optional

from websocket import (
    WebSocket,
    WebSocketApp,
)

from .constants import IndexerConfig


class CandleResolution(Enum):
    ONE_MINUTE = '1MIN'
    FIVE_MINUTES = '5MINS'
    FIFTEEN_MINUTES = '15MINS'
    THIRTY_MINUTES = '30MINS'
    ONE_HOUR = '1HOUR'
    FOUR_HOURS = '4HOURS'
    ONE_DAY = '1DAY'


class SocketClient:
    def __init__(
        self,
        config: IndexerConfig,
        on_message: Optional[Callable] = None,
        on_open: Optional[Callable] = None,
        on_close: Optional[Callable] = None
    ) -> None:
        self.url = config.websocket_endpoint
        self.ws: WebSocketApp
        self.on_message = on_message
        self.on_open = on_open
        self.on_close = on_close
        self.last_activity_time = None
        self.ping_thread = None
        self.ping_sent_time = None

    def connect(self) -> None:
        self.ws = WebSocketApp(
            self.url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_close=self._on_close,
        )
        self.ws.run_forever()

    def _on_open(self, ws):
        if self.on_open:
            self.on_open(ws)
        else:
            print('WebSocket connection opened')
        self.last_activity_time = time.time()
        self.ping_thread = threading.Thread(target=self._ping_thread_func)
        self.ping_thread.start()

    def _on_message(self, ws, message):
        if message == 'ping':
            self.send('pong')
        elif message == 'pong' and self.ping_sent_time is not None:
            elapsed_time = time.time() - self.ping_sent_time
            print(f'Received PONG after {elapsed_time:.2f} seconds')
            self.ping_sent_time = None
        elif self.on_message:
            self.on_message(ws, message)
        else:
            print(f'Received message: {message}')
        self.last_activity_time = time.time()

    def _on_close(self, ws: WebSocket, code: Optional[int], msg: Optional[str]) -> None:
        if self.on_close:
            self.on_close(ws)
        else:
            print('WebSocket connection closed')
        self.last_activity_time = None
        self.ping_thread = None

    def send(self, message):
        if self.ws:
            self.ws.send(message)
            self.last_activity_time = time.time()
        else:
            print('Error: WebSocket is not connected')

    def send_ping(self):
        self.send('ping')
        self.ping_sent_time = time.time()

    def _ping_thread_func(self):
        while self.ws:
            if self.last_activity_time and time.time() - self.last_activity_time > 30:
                self.send_ping()
                self.last_activity_time = time.time()
            elif self.ping_sent_time and time.time() - self.ping_sent_time > 5:
                print('Did not receive PONG in time, closing WebSocket...')
                self.close()
                break
            time.sleep(1)

    def send_ping_if_inactive_for(self, duration):
        self.last_activity_time = time.time() - duration

    def close(self):
        if self.ws:
            self.ws.close()
        else:
            print('Error: WebSocket is not connected')

    def subscribe(self, channel: str, params: Optional[dict] = None) -> None:
        if params is None:
            params = {}
        message = json.dumps(
            {
                'type': 'subscribe',
                'channel': channel,
                **params,
            },
        )
        self.send(message)

    def unsubscribe(self, channel: str, params: Optional[dict] = None) -> None:
        if params is None:
            params = {}
        message = json.dumps(
            {
                'type': 'unsubscribe',
                'channel': channel,
                **params,
            },
        )
        self.send(message)

    def subscribe_to_markets(self, batched: bool = True) -> None:
        self.subscribe('v4_markets', {'batched': batched})

    def unsubscribe_from_markets(self) -> None:
        self.unsubscribe('v4_markets')

    def subscribe_to_trades(self, market: str, batched: bool = True) -> None:
        self.subscribe('v4_trades', {'id': market, 'batched': batched})

    def unsubscribe_from_trades(self, market: str) -> None:
        self.unsubscribe('v4_trades', {'id': market})

    def subscribe_to_orderbook(self, market: str, batched: bool = True) -> None:
        self.subscribe('v4_orderbook', {'id': market, 'batched': batched})

    def unsubscribe_from_orderbook(self, market: str) -> None:
        self.unsubscribe('v4_orderbook', {'id': market})

    def subscribe_to_candles(
        self,
        market: str,
        resolution: CandleResolution,
        batched: bool = True,
    ) -> None:
        candles_id = f'{market}/{resolution.value}'
        self.subscribe('v4_candles', {'id': candles_id, 'batched': batched})

    def unsubscribe_from_candles(
        self,
        market: str,
        resolution: CandleResolution,
    ) -> None:
        candles_id = f'{market}/{resolution.value}'
        self.unsubscribe('v4_candles', {'id': candles_id})

    def subscribe_to_subaccount(
        self,
        address: str,
        subaccount_number: int,
    ) -> None:
        subaccount_id = f'{address}/{subaccount_number}'
        self.subscribe('v4_subaccounts', {'id': subaccount_id})

    def unsubscribe_from_subaccount(
        self,
        address: str,
        subaccount_number: int,
    ) -> None:
        subaccount_id = f'{address}/{subaccount_number}'
        self.unsubscribe('v4_subaccounts', {'id': subaccount_id})

    def subscribe_to_block_height(self) -> None:
        self.subscribe('v4_block_height')

    def unsubscribe_from_block_height(self) -> None:
        self.unsubscribe('v4_block_height')
