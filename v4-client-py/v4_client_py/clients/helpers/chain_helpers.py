from enum import Flag, auto
from v4_proto.dydxprotocol.clob.order_pb2 import Order


class OrderSide(Flag):
    BUY = auto()
    SELL = auto()


class OrderType(Flag):
    MARKET = auto()
    LIMIT = auto()
    STOP_MARKET = auto()
    TAKE_PROFIT_MARKET = auto()
    STOP_LIMIT = auto()
    TAKE_PROFIT_LIMIT = auto()


# FE enums. Do not pass these directly into the order proto TimeInForce field.
class OrderTimeInForce(Flag):
    GTT = auto()    # Good Til Time
    IOC = auto()    # Immediate or Cancel
    FOK = auto()    # Fill or Kill


# TODO: unnecessary class remove
class OrderExecution(Flag):
    DEFAULT = 0         # Default. Note proto enums start at 0, which is why this start at 0.
    IOC = auto()        # Immediate or Cancel
    POST_ONLY = auto()  # Post-only
    FOK = auto()        # Fill or Kill


ORDER_FLAGS_SHORT_TERM = 0
ORDER_FLAGS_LONG_TERM = 64
ORDER_FLAGS_CONDITIONAL = 32

QUOTE_QUANTUMS_ATOMIC_RESOLUTION = -6

SHORT_BLOCK_FORWARD = 3
SHORT_BLOCK_WINDOW = 20


def is_order_flag_stateful_order(
    order_flag: int
) -> bool:
    if order_flag == ORDER_FLAGS_SHORT_TERM:
        return False
    elif order_flag == ORDER_FLAGS_LONG_TERM:
        return True
    elif order_flag == ORDER_FLAGS_CONDITIONAL:
        return True
    else:
        raise ValueError('Invalid order flag')


def validate_good_til_fields(
    is_stateful_order: bool,
    good_til_block_time: int,
    good_til_block: int,
):
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


def calculate_side(
    side: OrderSide,
) -> Order.Side:
    return Order.SIDE_BUY if side == OrderSide.BUY else Order.SIDE_SELL


def calculate_time_in_force(
    order_type: OrderType,
    time_in_force: OrderTimeInForce,
    # execution: OrderExecution,
    post_only: bool
) -> Order.TimeInForce:
    if order_type == OrderType.MARKET or order_type == OrderType.STOP_MARKET or order_type == OrderType.TAKE_PROFIT_MARKET:
        if time_in_force == OrderTimeInForce.FOK:
            return Order.TimeInForce.TIME_IN_FORCE_FILL_OR_KILL
        elif time_in_force == OrderTimeInForce.IOC:
            return Order.TimeInForce.TIME_IN_FORCE_IOC
        else:
            raise ValueError(f'{time_in_force} is invalid for {order_type}')

    elif order_type == OrderType.LIMIT or order_type == OrderType.STOP_LIMIT or order_type == OrderType.TAKE_PROFIT_LIMIT:
        if time_in_force == OrderTimeInForce.GTT:
            if post_only:
                return Order.TimeInForce.TIME_IN_FORCE_POST_ONLY
            else:
                return Order.TimeInForce.TIME_IN_FORCE_UNSPECIFIED
        elif time_in_force == OrderTimeInForce.FOK:
            return Order.TimeInForce.TIME_IN_FORCE_FILL_OR_KILL
        elif time_in_force == OrderTimeInForce.IOC:
            return Order.TimeInForce.TIME_IN_FORCE_IOC
        else:
            raise ValueError(f'{time_in_force} is invalid for {order_type}')
#    elif type == OrderType.STOP_LIMIT or type == OrderType.TAKE_PROFIT_LIMIT:
#        if execution == OrderExecution.DEFAULT:
#            return Order.TimeInForce.TIME_IN_FORCE_UNSPECIFIED
#        elif execution == OrderExecution.POST_ONLY:
#            return Order.TimeInForce.TIME_IN_FORCE_POST_ONLY
#        if execution == OrderExecution.FOK:
#            return Order.TimeInForce.TIME_IN_FORCE_FILL_OR_KILL
#        elif execution == OrderExecution.IOC:
#            return Order.TimeInForce.TIME_IN_FORCE_IOC
#        else:
#            raise Exception("Unexpected code path: time_in_force")
#    elif type == OrderType.STOP_MARKET or type == OrderType.TAKE_PROFIT_MARKET:
#        if execution == OrderExecution.DEFAULT:
#            raise Exception("Execution value DEFAULT not supported for STOP_MARKET or TAKE_PROFIT_MARKET")
#        elif execution == OrderExecution.POST_ONLY:
#            raise Exception("Execution value POST_ONLY not supported for STOP_MARKET or TAKE_PROFIT_MARKET")
#        if execution == OrderExecution.FOK:
#            return Order.TimeInForce.TIME_IN_FORCE_FILL_OR_KILL
#        elif execution == OrderExecution.IOC:
#            return Order.TimeInForce.TIME_IN_FORCE_IOC
#        else:
#            raise Exception("Unexpected code path: time_in_force")
    else:
        raise ValueError('order_type is invalid')


def calculate_execution_condition(reduce_only: bool) -> int:
    if reduce_only:
        return Order.EXECUTION_CONDITION_REDUCE_ONLY
    else:
        return Order.EXECUTION_CONDITION_UNSPECIFIED


def calculate_order_flags(order_type: OrderType, time_in_force: OrderTimeInForce) -> int:
    if order_type == OrderType.MARKET:
        return ORDER_FLAGS_SHORT_TERM
    elif order_type == OrderType.LIMIT:
        if time_in_force == OrderTimeInForce.GTT:
            return ORDER_FLAGS_LONG_TERM
        else:
            return ORDER_FLAGS_SHORT_TERM
    else:
        return ORDER_FLAGS_CONDITIONAL


def calculate_client_metadata(order_type: OrderType) -> int:
    return 1 if (order_type == OrderType.MARKET or order_type == OrderType.STOP_MARKET or order_type == OrderType.TAKE_PROFIT_MARKET) else 0


def calculate_condition_type(order_type: OrderType) -> Order.ConditionType:
    if order_type == OrderType.LIMIT:
        return Order.CONDITION_TYPE_UNSPECIFIED
    elif order_type == OrderType.MARKET:
        return Order.CONDITION_TYPE_UNSPECIFIED
    elif order_type == OrderType.STOP_LIMIT or order_type == OrderType.STOP_MARKET:
        return Order.CONDITION_TYPE_STOP_LOSS
    elif order_type == OrderType.TAKE_PROFIT_LIMIT or order_type == OrderType.TAKE_PROFIT_MARKET:
        return Order.CONDITION_TYPE_TAKE_PROFIT
    else:
        raise ValueError('order_type is invalid')


def calculate_conditional_order_trigger_subticks(
    order_type: OrderType,
    atomic_resolution: int,
    quantum_conversion_exponent: int,
    subticks_per_tick: int,
    trigger_price: float,
) -> int:
    if order_type == OrderType.LIMIT or order_type == OrderType.MARKET:
        return 0
    elif order_type == OrderType.STOP_LIMIT or order_type == OrderType.STOP_MARKET or order_type == OrderType.TAKE_PROFIT_LIMIT or order_type == OrderType.TAKE_PROFIT_MARKET:
        if trigger_price is None:
            raise ValueError('trigger_price is required for conditional orders')
        return calculate_subticks(trigger_price, atomic_resolution, quantum_conversion_exponent, subticks_per_tick)
    else:
        raise ValueError('order_type is invalid')
