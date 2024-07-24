from enum import Enum, Flag, IntEnum, auto

from v4_proto.dydxprotocol.clob.order_pb2 import Order  # type: ignore


class OrderType(Enum):
    MARKET = auto()
    LIMIT = auto()
    STOP_MARKET = auto()
    TAKE_PROFIT_MARKET = auto()
    STOP_LIMIT = auto()
    TAKE_PROFIT_LIMIT = auto()

    @classmethod
    def market(self) -> tuple['OrderType', ...]:
        return (
            self.MARKET,
            self.STOP_MARKET,
            self.TAKE_PROFIT_MARKET,
        )

    def is_market(self) -> bool:
        return self in self.market()

    @classmethod
    def limit(self) -> tuple['OrderType', ...]:
        return (
            self.LIMIT,
            self.STOP_LIMIT,
            self.TAKE_PROFIT_LIMIT,
        )

    def is_limit(self) -> bool:
        return self in self.limit()

    @classmethod
    def conditional(self) -> tuple['OrderType', ...]:
        return (
            self.STOP_MARKET,
            self.TAKE_PROFIT_MARKET,
            self.STOP_LIMIT,
            self.TAKE_PROFIT_LIMIT,
        )

    def is_conditional(self) -> bool:
        return self in self.conditional()

    @classmethod
    def stop(self) -> tuple['OrderType', ...]:
        return (
            self.STOP_MARKET,
            self.STOP_LIMIT,
        )

    def is_stop(self) -> bool:
        return self in self.stop()

    @classmethod
    def take_profit(self) -> tuple['OrderType', ...]:
        return (
            self.TAKE_PROFIT_MARKET,
            self.TAKE_PROFIT_LIMIT,
        )

    def is_take_profit(self) -> bool:
        return self in self.take_profit()


class OrderSide(Flag):
    BUY = auto()
    SELL = auto()


# FE enums. Do not pass these directly into the order proto TimeInForce field.
class OrderTimeInForce(Flag):
    GTT = auto()    # Good Til Time
    GTX = auto()    # Good Til Time & Post Only
    IOC = auto()    # Immediate or Cancel
    FOK = auto()    # Fill or Kill

    @classmethod
    def immediate_execution(self) -> tuple['OrderTimeInForce', ...]:
        return (
            self.IOC,
            self.FOK,
        )

    def requires_immediate_execution(self) -> bool:
        return self in self.immediate_execution()


class OrderFlags(IntEnum):
    SHORT_TERM = 0
    CONDITIONAL = 32
    LONG_TERM = 64

    def is_stateful(self) -> bool:
        return self != self.SHORT_TERM


MarketTifMap = {
    OrderTimeInForce.IOC: Order.TIME_IN_FORCE_IOC,
    OrderTimeInForce.FOK: Order.TIME_IN_FORCE_FILL_OR_KILL,
}

LimitTifMap = {
    OrderTimeInForce.GTT: Order.TIME_IN_FORCE_UNSPECIFIED,
    OrderTimeInForce.GTX: Order.TIME_IN_FORCE_POST_ONLY,
    **MarketTifMap,
}

SHORT_BLOCK_WINDOW = 20

QUOTE_QUANTUMS_ATOMIC_RESOLUTION = -6


def validate_good_til_fields(
    is_stateful_order: bool,
    good_til_block: int,
    good_til_block_time: int,
) -> None:
    if is_stateful_order:
        if good_til_block_time == 0:
            raise ValueError(
                "stateful orders must have a valid GTBT. GTBT: ${0}".format(
                    good_til_block_time,
                )
            )
        if good_til_block != 0:
            raise ValueError(
                "stateful order uses GTBT. GTB must be zero. GTB: ${0}".format(
                    good_til_block,
                )
            )
    else:
        if good_til_block == 0:
            raise ValueError(
                "short term orders must have a valid GTB. GTB: ${0}".format(
                    good_til_block,
                )
            )
        if good_til_block_time != 0:
            raise ValueError(
                "stateful order uses GTB. GTBT must be zero. GTBT: ${0}".format(
                    good_til_block_time,
                )
            )


def round(
    number: float,
    base: int
) -> int:
    return int(number / base) * base


def calculate_quantums(
    size: float,
    atomic_resolution: int,
    step_base_quantums: int,
):
    raw_quantums = size * 10**(-1 * atomic_resolution)
    quantums = round(raw_quantums, step_base_quantums)
    # step_base_quantums functions as the minimum order size
    return max(quantums, step_base_quantums)


def calculate_subticks(
    price: float,
    atomic_resolution: int,
    quantum_conversion_exponent: int,
    subticks_per_tick: int
):
    exponent = atomic_resolution - quantum_conversion_exponent - QUOTE_QUANTUMS_ATOMIC_RESOLUTION
    raw_subticks = price * 10**(exponent)
    subticks = round(raw_subticks, subticks_per_tick)
    return max(subticks, subticks_per_tick)


def calculate_conditional_order_trigger_subticks(
        order_type: OrderType,
        atomic_resolution: int,
        quantum_conversion_exponent: int,
        subticks_per_tick: int,
        trigger_price: float,
) -> int:
    if order_type.is_conditional():
        if trigger_price is None:
            raise ValueError(
                'trigger_price is required for conditional orders',
            )
        return calculate_subticks(
            trigger_price,
            atomic_resolution,
            quantum_conversion_exponent,
            subticks_per_tick,
        )

    return 0


def calculate_side(
    side: OrderSide,
) -> Order.Side:
    return Order.SIDE_BUY if side == OrderSide.BUY else Order.SIDE_SELL


def calculate_time_in_force(
    order_type: OrderType,
    time_in_force: OrderTimeInForce,
) -> Order.TimeInForce:
    if order_type.is_market():
        if (tif := MarketTifMap.get(time_in_force)) is None:
            raise ValueError(f'Invalid time_in_force: {time_in_force} for order_type: {order_type}')
        return tif
    elif order_type.is_limit():
        if (tif := LimitTifMap.get(time_in_force)) is None:
            raise ValueError(f'Invalid time_in_force: {time_in_force} for order_type: {order_type}')
        return tif

    raise Exception(f'Invalid order_type: {order_type}')


def calculate_execution_condition(reduce_only: bool) -> int:
    if reduce_only:
        return Order.EXECUTION_CONDITION_REDUCE_ONLY

    return Order.EXECUTION_CONDITION_UNSPECIFIED


def calculate_order_flags(order_type: OrderType, time_in_force: OrderTimeInForce) -> OrderFlags:
    if order_type.is_conditional():
        return OrderFlags.CONDITIONAL
    if time_in_force.requires_immediate_execution():
        return OrderFlags.SHORT_TERM

    return OrderFlags.LONG_TERM


def calculate_client_metadata(order_type: OrderType) -> int:
    return int(order_type.is_market())


def calculate_condition_type(order_type: OrderType) -> Order.ConditionType:
    if order_type.is_stop():
        return Order.CONDITION_TYPE_STOP_LOSS
    elif order_type.is_take_profit():
        return Order.CONDITION_TYPE_TAKE_PROFIT

    return Order.CONDITION_TYPE_UNSPECIFIED
