import grpc  # type: ignore
from datetime import datetime, timedelta
from typing import Optional, Tuple, TYPE_CHECKING

from .constants import BroadcastMode, Network
from .dydx_indexer_client import IndexerClient
from .dydx_subaccount import Subaccount
from .dydx_validator_client import ValidatorClient
from .helpers.chain_helpers import (
    Order,
    OrderFlags,
    OrderSide,
    OrderTimeInForce,
    OrderType,

    calculate_side,
    calculate_quantums,
    calculate_subticks,
    calculate_conditional_order_trigger_subticks,
    calculate_condition_type,
    calculate_time_in_force,
    calculate_order_flags,
    calculate_client_metadata,

    QUOTE_QUANTUMS_ATOMIC_RESOLUTION,
    SHORT_BLOCK_WINDOW
)

from ..chain.aerial.tx_helpers import SubmittedTx


class CompositeClient:
    def __init__(
        self,
        network: Network,
        api_timeout=None,
        send_options=None,
        credentials=grpc.ssl_channel_credentials(),
    ):
        self.indexer_client = IndexerClient(network.indexer_config, api_timeout, send_options)
        self.validator_client = ValidatorClient(network.validator_config, credentials)

    def get_latest_block_height(self) -> int:
        return self.validator_client.get.latest_block_height()

    def calculate_good_til_block(
        self, good_til_blocks: int,
        latest_height: Optional[int] = None,
    ) -> int:
        if latest_height is None:
            latest_height = self.get_latest_block_height()

        good_til_block = latest_height + good_til_blocks
        self.validate_good_til_block(good_til_block, latest_height)
        return good_til_block

    def calculate_good_til_block_time(self, good_til_time_in_seconds: int) -> int:
        now = datetime.now()
        interval = timedelta(seconds=good_til_time_in_seconds)
        future = now + interval
        return int(future.timestamp())

    # Helper function to generate the corresponding
    # good_til_block, good_til_block_time fields to construct an order.
    # good_til_block is the exact block number the short term order will expire on.
    # good_til_time_in_seconds is the number of seconds until the stateful order expires.
    def generate_good_til_fields(
        self,
        order_flags: OrderFlags,
        good_til_blocks: int,
        good_til_seconds: int,
        latest_height: Optional[int] = None,
    ) -> Tuple[int, int]:
        if order_flags.is_stateful():
            return (0, self.calculate_good_til_block_time(good_til_seconds))

        return (self.calculate_good_til_block(good_til_blocks, latest_height), 0)

    def validate_good_til_block(
        self, good_til_block: int,
        latest_block_height: Optional[int] = None,
    ) -> None:
        if latest_block_height is None:
            latest_block_height = self.validator_client.get.latest_block_height()

        next_valid_block_height = latest_block_height + 1
        lower_bound = next_valid_block_height
        upper_bound = next_valid_block_height + SHORT_BLOCK_WINDOW
        if good_til_block < lower_bound or good_til_block > upper_bound:
            raise Exception(
                f"Invalid Short-Term order GoodTilBlock. "
                f"Should be greater-than-or-equal-to {lower_bound} "
                f"and less-than-or-equal-to {upper_bound}. "
                f"Provided good til block: {good_til_block}"
            )

    def place_order(
        self,
        subaccount: Subaccount,
        market: str,
        type: OrderType,
        side: OrderSide,
        price: float,
        size: float,
        client_id: int,
        time_in_force: OrderTimeInForce,
        good_til_blocks: int,
        good_til_seconds: int,
        reduce_only: bool,
        trigger_price: float = 0,
        market_info: Optional[dict] = None,
        latest_height: Optional[int] = None,
        broadcast_mode: Optional[BroadcastMode] = None,
    ) -> SubmittedTx:
        '''
        Place order

        :param subaccount: required
        :type subaccount: Subaccount

        :param market: required
        :type market: str

        :param side: required
        :type side: Order.Side

        :param price: required
        :type price: float

        :param size: required
        :type size: float

        :param client_id: required
        :type client_id: int

        :param time_in_force: required
        :type time_in_force: OrderTimeInForce

        :param good_til_block: required
        :type good_til_block: int

        :param good_til_time_in_seconds: required
        :type good_til_time_in_seconds: int

        :param execution: required
        :type execution: OrderExecution

        :param post_only: required
        :type post_only: bool

        :param reduce_only: required
        :type reduce_only: bool

        :returns: Tx information
        :rtype: SubmittedTx
        '''
        if market_info is None:
            markets_response = self.indexer_client.markets.get_perpetual_markets(market)
            market_info = markets_response.data['markets'][market]

        clob_pair_id = market_info['clobPairId']
        atomic_resolution = market_info['atomicResolution']
        step_base_quantums = market_info['stepBaseQuantums']
        quantum_conversion_exponent = market_info['quantumConversionExponent']
        subticks_per_tick = market_info['subticksPerTick']
        order_side = calculate_side(side)
        quantums = calculate_quantums(size, atomic_resolution, step_base_quantums)
        subticks = calculate_subticks(price, atomic_resolution, quantum_conversion_exponent, subticks_per_tick)
        order_flags = calculate_order_flags(type, time_in_force)
        # order_time_in_force = calculate_time_in_force(type, time_in_force, execution, post_only)
        order_time_in_force = calculate_time_in_force(type, time_in_force)
        good_til_block, good_til_block_time = self.generate_good_til_fields(
            order_flags,
            good_til_blocks,
            good_til_seconds,
            latest_height,
        )
        client_metadata = calculate_client_metadata(type)
        condition_type = calculate_condition_type(type)
        conditional_order_trigger_subticks = calculate_conditional_order_trigger_subticks(
            type,
            atomic_resolution,
            quantum_conversion_exponent,
            subticks_per_tick,
            trigger_price
        )
        return self.validator_client.post.place_order(
            subaccount,
            client_id,
            clob_pair_id,
            order_side,
            quantums,
            subticks,
            order_time_in_force,
            order_flags,
            reduce_only,
            good_til_block,
            good_til_block_time,
            client_metadata,
            condition_type,
            conditional_order_trigger_subticks,
            broadcast_mode,
        )

    def place_short_term_order(
        self,
        subaccount: Subaccount,
        market: str,
        type: OrderType,
        side: OrderSide,
        price: float,
        size: float,
        client_id: int,
        good_til_blocks: int,
        time_in_force: Order.TimeInForce,
        reduce_only: bool,
        market_info: Optional[dict] = None,
        latest_height: Optional[int] = None,
        broadcast_mode: Optional[BroadcastMode] = None,
    ) -> SubmittedTx:
        '''
        Place Short-Term order

        :param subaccount: required
        :type subaccount: Subaccount

        :param market: required
        :type market: str

        :param side: required
        :type side: Order.Side

        :param price: required
        :type price: float

        :param size: required
        :type size: float

        :param client_id: required
        :type client_id: int

        :param good_til_block: required
        :type good_til_block: int

        :param time_in_force: required
        :type time_in_force: OrderExecution

        :param reduce_only: required
        :type reduce_only: bool

        :returns: Tx information
        :rtype: SubmittedTx
        '''
        if market_info is None:
            markets_response = self.indexer_client.markets.get_perpetual_markets(market)
            market_info = markets_response.data['markets'][market]

        clob_pair_id = market_info['clobPairId']
        atomic_resolution = market_info['atomicResolution']
        step_base_quantums = market_info['stepBaseQuantums']
        quantum_conversion_exponent = market_info['quantumConversionExponent']
        subticks_per_tick = market_info['subticksPerTick']
        order_side = calculate_side(side)
        quantums = calculate_quantums(size, atomic_resolution, step_base_quantums)
        subticks = calculate_subticks(price, atomic_resolution, quantum_conversion_exponent, subticks_per_tick)
        order_flags = OrderFlags.SHORT_TERM
        client_metadata = calculate_client_metadata(type)
        good_til_block, good_til_block_time = self.generate_good_til_fields(
            order_flags,
            good_til_blocks,
            0,  # good_til_seconds
            latest_height,
        )
        condition_type = Order.CONDITION_TYPE_UNSPECIFIED
        conditional_order_trigger_subticks = 0
        return self.validator_client.post.place_order(
            subaccount,
            client_id,
            clob_pair_id,
            order_side,
            quantums,
            subticks,
            time_in_force,
            order_flags,
            reduce_only,
            good_til_block,
            good_til_block_time,
            client_metadata,
            condition_type,
            conditional_order_trigger_subticks,
            broadcast_mode,
        )

    def cancel_order(
        self,
        subaccount: Subaccount,
        client_id: int,
        market: str,
        order_flags: OrderFlags,
        good_til_block_time: int = 0,
        good_til_block: int = 0,
        market_info: Optional[dict] = None,
        broadcast_mode: Optional[BroadcastMode] = None,
    ) -> SubmittedTx:
        '''
        Cancel order

        :param subaccount: required
        :type subaccount: Subaccount

        :param client_id: required
        :type client_id: int

        :param market: required
        :type market: str

        :param order_flags: required
        :type order_flags: int

        :param good_til_block: required
        :type good_til_block: int

        :param good_til_block_time: required
        :type good_til_block_time: int

        :returns: Tx information
        :rtype: SubmittedTx
        '''
        if market_info is None:
            markets_response = self.indexer_client.markets.get_perpetual_markets(market)
            market_info = markets_response.data['markets'][market]

        clob_pair_id = market_info['clobPairId']

        return self.validator_client.post.cancel_order(
            subaccount,
            client_id,
            clob_pair_id,
            order_flags,
            good_til_block,
            good_til_block_time,
            broadcast_mode,
        )

    def cancel_short_term_order(
        self,
        subaccount: Subaccount,
        client_id: int,
        market: str,
        good_til_block: int,
        market_info: Optional[dict] = None,
        broadcast_mode: Optional[BroadcastMode] = None,
    ) -> SubmittedTx:
        '''
        Cancel short term order

        :param subaccount: required
        :type subaccount: Subaccount

        :param client_id: required
        :type client_id: int

        :param clob_pair_id: required
        :type clob_pair_id: int

        :param good_til_block: required
        :type good_til_block: int

        :returns: Tx information
        :rtype: SubmittedTx
        '''
        if market_info is None:
            markets_response = self.indexer_client.markets.get_perpetual_markets(market)
            market_info = markets_response.data['markets'][market]

        clob_pair_id = market_info['clobPairId']

        order_flags = OrderFlags.SHORT_TERM
        good_til_block_time = 0

        return self.validator_client.post.cancel_order(
            subaccount,
            client_id,
            clob_pair_id,
            order_flags,
            good_til_block,
            good_til_block_time,
            broadcast_mode,
        )

    def transfer_to_subaccount(
        self,
        subaccount: Subaccount,
        recipient_address: str,
        recipient_subaccount_number: int,
        amount: float,
    ) -> SubmittedTx:
        '''
        Transfer to subaccount

        :param subaccount: required
        :type subaccount: Subaccount

        :param recipient_address: required
        :type recipient_address: str

        :param recipient_subaccount_number: required
        :type recipient_subaccount_number: int

        :param amount: required
        :type amount: float

        :returns: Tx information
        :rtype: SubmittedTx
        '''
        return self.validator_client.post.transfer(
            subaccount=subaccount,
            recipient_address=recipient_address,
            recipient_subaccount_number=recipient_subaccount_number,
            asset_id=0,
            amount=amount * 10 ** (-QUOTE_QUANTUMS_ATOMIC_RESOLUTION),
        )

    def deposit_to_subaccount(
        self,
        subaccount: Subaccount,
        amount: float,
    ) -> SubmittedTx:
        '''
        Deposit to subaccount

        :param subaccount: required
        :type subaccount: Subaccount

        :param amount: required
        :type amount: float

        :returns: Tx information
        :rtype: SubmittedTx
        '''
        return self.validator_client.post.deposit(
            subaccount=subaccount,
            asset_id=0,
            quantums=amount * 10 ** (-QUOTE_QUANTUMS_ATOMIC_RESOLUTION),
        )

    def withdraw_from_subaccount(
        self,
        subaccount: Subaccount,
        amount: float,
    ) -> SubmittedTx:
        '''
        Withdraw from subaccount

        :param subaccount: required
        :type subaccount: Subaccount

        :param amount: required
        :type amount: float

        :returns: Tx information
        :rtype: SubmittedTx
        '''
        return self.validator_client.post.withdraw(
            subaccount=subaccount,
            asset_id=0,
            quantums=amount * 10 ** (-QUOTE_QUANTUMS_ATOMIC_RESOLUTION),
        )
