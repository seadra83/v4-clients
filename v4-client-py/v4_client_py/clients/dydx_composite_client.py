from datetime import datetime, timedelta
from typing import Optional, Tuple

import grpc  # type: ignore
from v4_client_py.clients.helpers.chain_helpers import (
    OrderSide,
    OrderTimeInForce,
    OrderType,
    calculate_quantums,
    calculate_subticks,
    calculate_side,
    calculate_time_in_force,
    calculate_order_flags,
    calculate_client_metadata,
    calculate_condition_type,
    calculate_conditional_order_trigger_subticks,
    is_order_flag_stateful_order,
    QUOTE_QUANTUMS_ATOMIC_RESOLUTION,
    SHORT_BLOCK_FORWARD,
    SHORT_BLOCK_WINDOW,
)
from v4_client_py.clients.constants import Network
from v4_client_py.clients.dydx_indexer_client import IndexerClient
from v4_client_py.clients.dydx_validator_client import ValidatorClient
from v4_client_py.clients.dydx_subaccount import Subaccount
from v4_client_py.chain.aerial.tx_helpers import SubmittedTx


class CompositeClient:
    def __init__(
        self,
        network: Network,
        api_timeout=None,
        send_options=None,
        credentials=grpc.ssl_channel_credentials(),
    ):
        self.indexer_client = IndexerClient(
            network.indexer_config, api_timeout, send_options)
        self.validator_client = ValidatorClient(
            network.validator_config, credentials)

    def validate_good_til_block(self, good_til_block: int) -> None:
        height = self.validator_client.get.latest_block_height()
        next_valid_block_height = height + 1
        lower_bound = next_valid_block_height
        upper_bound = next_valid_block_height + SHORT_BLOCK_WINDOW
        if good_til_block < lower_bound or good_til_block > upper_bound:
            raise Exception(
                f"Invalid Short-Term order GoodTilBlock."
                f"Should be greater-than-or-equal-to {lower_bound}"
                f"and less-than-or-equal-to {upper_bound}."
                f"Provided GoodTilBlock: {good_til_block}"
            )

    def calculate_good_til_block(self, current_height: Optional[int]) -> int:
        if current_height is None:
            current_height = self.validator_client.get.latest_block_height()

        return current_height + SHORT_BLOCK_FORWARD

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
        order_flags: int,
        current_height: Optional[int],
        good_til_time_in_seconds: int,
    ) -> Tuple[int, int]:
        is_stateful_order = is_order_flag_stateful_order(order_flags)
        if is_stateful_order:
            return 0, self.calculate_good_til_block_time(good_til_time_in_seconds)
        else:
            return self.calculate_good_til_block(current_height), 0

    # Use human readable form of input, including price and size
    # The quantum and subticks are calculated and submitted

    def place_order(
        self,
        subaccount: Subaccount,
        market: str,
        order_type: OrderType,
        side: OrderSide,
        price: float,
        size: float,
        client_id: int,
        time_in_force: OrderTimeInForce,
        good_til_time_in_seconds: int,
        post_only: bool,
        reduce_only: bool,
        trigger_price: float = .0,
        market_info: Optional[dict] = None,
        current_height: Optional[int] = None,
    ) -> SubmittedTx:
        '''
        Place order

        :param subaccount: required
        :type subaccount: Subaccount

        :param market: required
        :type market: str

        :param order_type: required
        :type order_type: OrderType

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

        :param good_til_time_in_seconds: required
        :type good_til_time_in_seconds: int

        :param post_only: required
        :type post_only: bool

        :param reduce_only: required
        :type reduce_only: bool

        :param trigger_price: optional
        :type trigger_price: float

        :param market_info: optional
        :type market_info: dict

        :param current_height: optional
        :type current_height: int

        :returns: Tx information
        '''
        if market_info is None:
            markets_response = self.indexer_client.markets.get_perpetual_markets(market)
            market_info = markets_response.data['markets'][market]

        clob_pair_id = int(market_info['clobPairId'])
        atomic_resolution = market_info['atomicResolution']
        step_base_quantums = market_info['stepBaseQuantums']
        quantum_conversion_exponent = market_info['quantumConversionExponent']
        subticks_per_tick = market_info['subticksPerTick']

        order_side = calculate_side(side)
        quantums = calculate_quantums(size, atomic_resolution, step_base_quantums)
        subticks = calculate_subticks(price, atomic_resolution, quantum_conversion_exponent, subticks_per_tick)
        order_flags = calculate_order_flags(order_type, time_in_force)
        time_in_force = calculate_time_in_force(order_type, time_in_force, post_only)
        good_til_block, good_til_block_time = self.generate_good_til_fields(
            order_flags,
            current_height,
            good_til_time_in_seconds,
        )
        client_metadata = calculate_client_metadata(order_type)
        condition_type = calculate_condition_type(order_type)
        conditional_order_trigger_subticks = calculate_conditional_order_trigger_subticks(
            order_type,
            atomic_resolution,
            quantum_conversion_exponent,
            subticks_per_tick,
            trigger_price,
        )

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
        )

    def cancel_order(
        self,
        subaccount: Subaccount,
        client_id: int,
        clob_pair_id: int,
        order_flags: int,
        good_til_block: int,
        good_til_block_time: int,
    ) -> SubmittedTx:
        '''
        Cancel order

        :param subaccount: required
        :type subaccount: Subaccount

        :param client_id: required
        :type client_id: int

        :param clob_pair_id: required
        :type clob_pair_id: int

        :param order_flags: required
        :type order_flags: int

        :param good_til_block: required
        :type good_til_block: int

        :param good_til_time_in_seconds: required
        :type good_til_time_in_seconds: int

        :returns: Tx information
        '''
        return self.validator_client.post.cancel_order(
            subaccount,
            client_id,
            clob_pair_id,
            order_flags,
            good_til_block,
            good_til_block_time,
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
        '''
        return self.validator_client.post.withdraw(
            subaccount=subaccount,
            asset_id=0,
            quantums=amount * 10 ** (-QUOTE_QUANTUMS_ATOMIC_RESOLUTION),
        )
