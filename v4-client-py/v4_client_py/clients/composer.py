from v4_proto.dydxprotocol.clob.order_pb2 import Order, OrderId  # type: ignore
from v4_proto.dydxprotocol.clob.tx_pb2 import (  # type: ignore
    MsgBatchCancel,
    MsgCancelOrder,
    MsgPlaceOrder,
    OrderBatch,
)
from v4_proto.dydxprotocol.sending.transfer_pb2 import (  # type: ignore
    Transfer,
    MsgWithdrawFromSubaccount,
    MsgDepositToSubaccount,
)
from v4_proto.dydxprotocol.sending.tx_pb2 import MsgCreateTransfer  # type: ignore
from v4_proto.dydxprotocol.subaccounts.subaccount_pb2 import SubaccountId  # type: ignore

from v4_client_py.clients.helpers.chain_helpers import is_order_flag_stateful_order, validate_good_til_fields


class Composer:
    def compose_msg_place_order(
        self,
        address: str,
        subaccount_number: int,
        client_id: int,
        clob_pair_id: int,
        order_flags: int,
        good_til_block: int,
        good_til_block_time: int,
        side: Order.Side,
        quantums: int,
        subticks: int,
        time_in_force: Order.TimeInForce,
        reduce_only: bool,
        client_metadata: int,
        condition_type: Order.ConditionType,
        conditional_order_trigger_subticks: int,
    ) -> MsgPlaceOrder:
        '''
        Compose a place order message

        :param address: required
        :type address: str

        :param subaccount_number: required
        :type subaccount_number: int

        :param client_id: required
        :type client_id: int

        :param clob_pair_id: required
        :type clob_pair_id: int

        :param order_flags: required
        :type order_flags: int

        :param good_til_block: required
        :type good_til_block: int

        :param good_til_block_time: required
        :type good_til_block_time: int

        :param side: required
        :type side: Order.Side

        :param quantums: required
        :type quantums: int

        :param subticks: required
        :type subticks: int

        :param time_in_force: required
        :type time_in_force: int

        :param reduce_only: required
        :type reduce_only: bool

        :param client_metadata: required
        :type client_metadata: int

        :param condition_type: required
        :type condition_type: int

        :param conditional_order_trigger_subticks: required
        :type conditional_order_trigger_subticks: int

        :returns: Place order message, to be sent to chain
        :rtype: MsgPlaceOrder
        '''
        subaccount_id = SubaccountId(owner=address, number=subaccount_number)

        is_stateful_order = is_order_flag_stateful_order(order_flags)
        validate_good_til_fields(is_stateful_order, good_til_block_time, good_til_block)

        order_id = OrderId(
            subaccount_id=subaccount_id,
            client_id=client_id,
            order_flags=order_flags,
            clob_pair_id=int(clob_pair_id),
        )

        order = Order(
            order_id=order_id,
            side=side,
            quantums=quantums,
            subticks=subticks,
            good_til_block=good_til_block,
            good_til_block_time=good_til_block_time,
            time_in_force=time_in_force.value,
            reduce_only=reduce_only,
            client_metadata=client_metadata,
            condition_type=condition_type,
            conditional_order_trigger_subticks=conditional_order_trigger_subticks,
        )
        return MsgPlaceOrder(order=order)

    def compose_msg_cancel_order(
        self,
        address: str,
        subaccount_number: int,
        client_id: int,
        clob_pair_id: int,
        order_flags: int,
        good_til_block: int,
        good_til_block_time: int,
    ) -> MsgCancelOrder:
        '''
        Compose a cancel order messasge

        :param address: required
        :type address: str

        :param subaccount_number: required
        :type subaccount_number: int

        :param client_id: required
        :type client_id: int

        :param clob_pair_id: required
        :type clob_pair_id: int

        :param order_flags: required
        :type order_flags: int

        :param good_til_block: required
        :type good_til_block: int

        :param good_til_block_time: required
        :type good_til_block_time: int

        :returns: Cancel order message, to be sent to chain
        :rtype: MsgCancelOrder
        '''
        subaccount_id = SubaccountId(
            owner=address,
            number=subaccount_number,
        )
        is_stateful_order = is_order_flag_stateful_order(order_flags)
        validate_good_til_fields(is_stateful_order, good_til_block_time, good_til_block)

        order_id = OrderId(
            subaccount_id=subaccount_id,
            client_id=client_id,
            order_flags=order_flags,
            clob_pair_id=int(clob_pair_id),
        )

        if is_stateful_order:
            return MsgCancelOrder(
                order_id=order_id,
                good_til_block_time=good_til_block_time
            )
        return MsgCancelOrder(
            order_id=order_id,
            good_til_block=good_til_block
        )

    def compose_msg_batch_cancel(
        self,
        address: str,
        subaccount_number: int,
        cancel_orders: dict[int, list[int]],
        good_til_block: int,
    ) -> MsgBatchCancel:
        '''
        Compose a batch cancel messasge

        :param address: required
        :type address: str

        :param subaccount_number: required
        :type subaccount_number: int

        :param cancel_orders: required dict {"clob_pair_id": [client_id, ...], ...}
        :type cancel_orders: dict[int, list[int]]

        :param good_til_block: required
        :type good_til_block: int

        :returns: Batch cancel message, to be sent to chain
        :rtype MsgBatchCancel
        '''
        subaccount_id = SubaccountId(
            owner=address, number=subaccount_number,
        )
        short_term_cancels: list[OrderBatch] = []
        for k, v in cancel_orders.items():
            short_term_cancels.append(
                OrderBatch(clob_pair_id=k, client_ids=v)
            )
        return MsgBatchCancel(
            subaccount_id=subaccount_id,
            short_term_cancels=short_term_cancels,
            good_til_block=good_til_block,
        )

    def compose_msg_transfer(
        self,
        address: str,
        subaccount_number: int,
        recipient_address: str,
        recipient_subaccount_number: int,
        asset_id: int,
        amount: int
    ) -> MsgCreateTransfer:
        sender = SubaccountId(owner=address, number=subaccount_number)
        recipient = SubaccountId(owner=recipient_address, number=recipient_subaccount_number)

        transfer = Transfer(sender=sender, recipient=recipient, asset_id=asset_id, amount=amount)

        return MsgCreateTransfer(transfer=transfer)

    def compose_msg_deposit_to_subaccount(
        self,
        address: str,
        subaccount_number: int,
        asset_id: int,
        quantums: int
    ) -> MsgDepositToSubaccount:
        recipient = SubaccountId(owner=address, number=subaccount_number)

        return MsgDepositToSubaccount(sender=address, recipient=recipient, asset_id=asset_id, quantums=quantums)

    def compose_msg_withdraw_from_subaccount(
        self,
        address: str,
        subaccount_number: int,
        asset_id: int,
        quantums: int
    ) -> MsgWithdrawFromSubaccount:
        sender = SubaccountId(owner=address, number=subaccount_number)

        return MsgWithdrawFromSubaccount(sender=sender, recipient=address, asset_id=asset_id, quantums=quantums)
