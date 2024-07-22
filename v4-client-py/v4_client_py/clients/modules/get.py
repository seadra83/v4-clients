import logging
from typing import Optional

import grpc  # type: ignore

from v4_proto.cosmos.auth.v1beta1 import (  # type: ignore
    auth_pb2 as auth_type,
    query_pb2 as auth_query,
    query_pb2_grpc as auth_query_grpc,
)

from v4_proto.cosmos.bank.v1beta1 import (  # type: ignore
    query_pb2_grpc as bank_query_grpc,
    query_pb2 as bank_query,
)
from v4_proto.cosmos.base.tendermint.v1beta1 import (  # type: ignore
    query_pb2 as tendermint_query,
    query_pb2_grpc as tendermint_query_grpc,
)
from v4_proto.cosmos.staking.v1beta1 import (  # type: ignore
    query_pb2 as staking_query,
    query_pb2_grpc as staking_query_grpc,
)
from v4_proto.cosmos.tx.v1beta1 import (  # type: ignore
    service_pb2_grpc as tx_service_grpc,
    service_pb2 as tx_service,
)

from v4_proto.dydxprotocol.clob import (  # type: ignore
    clob_pair_pb2 as clob_pair_type,
    equity_tier_limit_config_pb2 as equity_tier_limit_config_type,
    query_pb2 as clob_query,
    query_pb2_grpc as clob_query_grpc,
)
from v4_proto.dydxprotocol.feetiers import (  # type: ignore
    query_pb2 as feetiers_query,
    query_pb2_grpc as feetiers_query_grpc,
)
from v4_proto.dydxprotocol.perpetuals import (  # type: ignore
    query_pb2 as perpetuals_query,
    query_pb2_grpc as perpetuals_query_grpc,
)
from v4_proto.dydxprotocol.prices import (  # type: ignore
    query_pb2 as prices_query,
    query_pb2_grpc as prices_query_grpc,
    market_price_pb2 as market_price_type,
)
from v4_proto.dydxprotocol.ratelimit import (  # type: ignore
    query_pb2 as rate_limit_query,
    query_pb2_grpc as rate_limit_query_grpc,
)
from v4_proto.dydxprotocol.rewards import (  # type: ignore
    query_pb2 as rewards_query,
    query_pb2_grpc as rewards_query_grpc,
)
from v4_proto.dydxprotocol.bridge import (  # type: ignore
    query_pb2 as bridge_query,
    query_pb2_grpc as bridge_query_grpc,
)
from v4_proto.dydxprotocol.stats import (  # type: ignore
    query_pb2 as stats_query,
    query_pb2_grpc as stats_querry_grpc,
    stats_pb2 as stats_type,
)
from v4_proto.dydxprotocol.subaccounts import (  # type: ignore
    query_pb2 as subaccounts_query,
    query_pb2_grpc as subaccounts_query_grpc,
    subaccount_pb2 as subaccount_type,
)

from ..constants import ValidatorConfig

DEFAULT_TIMEOUTHEIGHT = 30  # blocks


class Get:
    def __init__(
        self,
        config: ValidatorConfig,
        credentials=grpc.ssl_channel_credentials(),
    ):
        # chain stubs
        self.grpc_channel = (
            grpc.secure_channel(config.grpc_endpoint, credentials) if config.ssl_enabled
            else grpc.insecure_channel(config.grpc_endpoint)
        )
        self.config = config

    # default client methods
    def latest_block(self) -> tendermint_query.GetLatestBlockResponse:
        '''
        Get lastest block

        :returns: Response, containing block information

        '''
        stub = tendermint_query_grpc.ServiceStub(self.grpc_channel)
        return stub.GetLatestBlock(
            tendermint_query.GetLatestBlockRequest()
        )

    def latest_block_height(self) -> int:
        '''
        Get latest block height

        :returns: Latest block height
        :rtype: int
        '''
        return self.latest_block().block.header.height

    def sync_timeout_height(self):
        try:
            block_height = self.latest_block_height()
            self.timeout_height = block_height + DEFAULT_TIMEOUTHEIGHT
        except Exception as e:
            logging.debug("error while fetching latest block, setting timeout height to 0:{}".format(e))
            self.timeout_height = 0

    def tx(self, tx_hash: str):
        '''
        Get tx

        :param tx_hash: required
        :type: str

        :returns: Transaction
        '''
        stub = tx_service_grpc.ServiceStub(self.grpc_channel)
        return stub.GetTx(tx_service.GetTxRequest(hash=tx_hash))

    def account(self, address: str) -> Optional[auth_type.BaseAccount]:
        '''
        Get account information

        :param address: required
        :type address: str

        :returns: Account information, including account number and sequence
        '''
        stub = auth_query_grpc.QueryStub(self.grpc_channel)
        account_any = stub.Account(
            auth_query.QueryAccountRequest(address=address)
        ).account
        account = auth_type.BaseAccount()
        if account_any.Is(account.DESCRIPTOR):
            account_any.Unpack(account)
            return account
        else:
            return None

    def bank_balance(self, address: str, denom: str) -> bank_query.QueryBalanceResponse:
        '''
        Get wallet asset balance

        :param denom: required
        :type demon: str

        :returns: Asset balance given the denom

        :raises: DydxAPIError
        '''
        stub = bank_query_grpc.QueryStub(self.grpc_channel)
        return stub.Balance(
            bank_query.QueryBalanceRequest(address=address, denom=denom)
        )

    def bank_balances(self, address: str) -> bank_query.QueryAllBalancesResponse:
        '''
        Get wallet account balances

        :returns: All assets in the wallet
        '''
        stub = bank_query_grpc.QueryStub(self.grpc_channel)
        return stub.AllBalances(
            bank_query.QueryAllBalancesRequest(address=address)
        )

    def delayed_complete_bridge_messages(
        self,
        address: str = "",
    ) -> bridge_query.QueryDelayedCompleteBridgeMessagesResponse:
        """
        Get delayed complete bridge messages

        :param address: optional
        :type address: str

        :returns: Delayed complete bridge messages
        :rtype: QueryDelayedCompleteBridgeMessagesResponse
        """
        stub = bridge_query_grpc.QueryStub(self.grpc_channel)
        return stub.DelayedCompleteBridgeMessages(
            bridge_query.QueryDelayedCompleteBridgeMessagesRequest(
                address=address,
            )
        )

    def clob_pair(self, pair_id: int) -> clob_pair_type.ClobPair:
        '''
        Get pair information

        :param pair_id: required
        :type pair_id: int

        :returns: Pair information
        '''
        stub = clob_query_grpc.QueryStub(self.grpc_channel)
        return stub.ClobPair(
            clob_query.QueryGetClobPairRequest(id=pair_id)
        ).clob_pair

    def clob_pairs(self) -> clob_query.QueryClobPairAllResponse:
        '''
        Get all pairs

        :returns: All pairs
        '''
        stub = clob_query_grpc.QueryStub(self.grpc_channel)
        return stub.ClobPairAll(
            clob_query.QueryAllClobPairRequest()
        )

    def equity_tier_limit_config(
        self,
    ) -> equity_tier_limit_config_type.EquityTierLimitConfiguration:
        '''
        Get equity tier limit configuration

        :returns: Equity tier limit configuration
        '''
        stub = clob_query_grpc.QueryStub(self.grpc_channel)
        return stub.EquityTierLimitConfiguration(
            clob_query.QueryEquityTierLimitConfigurationRequest()
        ).equity_tier_limit_config

    def feetiers(self) -> feetiers_query.QueryPerpetualFeeParamsResponse:
        stub = feetiers_query_grpc.QueryStub(self.grpc_channel)
        return stub.PerpetualFeeParams(
            feetiers_query.QueryPerpetualFeeParamsRequest()
        )

    def user_feetier(self, address: str) -> feetiers_query.QueryUserFeeTierResponse:
        stub = feetiers_query_grpc.QueryStub(self.grpc_channel)
        return stub.UserFeeTier(
            feetiers_query.QueryUserFeeTierRequest(user=address)
        )

    def perpetual(
        self,
        perpetual_id: int,
    ) -> perpetuals_query.QueryPerpetualResponse:
        stub = perpetuals_query_grpc.QueryStub(self.grpc_channel)
        return stub.Perpetual(
            perpetuals_query.QueryPerpetualRequest(id=perpetual_id)
        )

    def perpetuals(self) -> perpetuals_query.QueryAllPerpetualsResponse:
        stub = perpetuals_query_grpc.QueryStub(self.grpc_channel)
        return stub.AllPerpetuals(
            perpetuals_query.QueryAllPerpetualsRequest()
        )

    def price(self, market_id: int) -> market_price_type.MarketPrice:
        '''
        Get market price

        :param market_id: required
        :type market_id: int

        :returns: Market price
        '''
        stub = prices_query_grpc.QueryStub(self.grpc_channel)
        return stub.MarketPrice(
            prices_query.QueryMarketPriceRequest(id=market_id)
        ).market_price

    def prices(self) -> prices_query.QueryAllMarketPricesResponse:
        '''
        Get all market prices

        :returns: All market prices
        '''
        stub = prices_query_grpc.QueryStub(self.grpc_channel)
        return stub.AllMarketPrices(
            prices_query.QueryAllMarketPricesRequest()
        )

    def withdrawal_capacity_by_denom(self, denom: str) -> rate_limit_query.QueryCapacityByDenomResponse:
        '''
        Get withdrawal capacity by denom

        :param denom: required
        :type denom: str

        :returns: Withdrawal capacity by denom
        :rtype: QueryCapacityByDenomResponse
        '''
        stub = rate_limit_query_grpc.QueryStub(self.grpc_channel)
        return stub.CapacityByDenom(
            rate_limit_query.QueryCapacityByDenomRequest(denom=denom)
        )

    def rewards_params(self) -> rewards_query.QueryParamsResponse:
        """
        Get rewards params

        :returns: Rewards params
        :rtype: QueryParamsResponse
        """
        stub = rewards_query_grpc.QueryStub(self.grpc_channel)
        return stub.Params(rewards_query.QueryParamsRequest())

    def all_validators(
        self,
        status: str = "",
    ) -> staking_query.QueryValidatorsResponse:
        """
        Get all validators optionally filtered by status

        :param status: optional
        :type status: str

        :returns Validators
        :rtype: QueryValidatorsResponse
        """
        stub = staking_query_grpc.QueryStub(self.grpc_channel)
        return stub.Validators(
            staking_query.QueryValidatorsRequest(status=status)
        )

    def delegator_delegations(
        self,
        delegator_addr: str,
    ) -> staking_query.QueryDelegatorDelegationsResponse:
        """
        Get delegator delegations

        :param delegator_addr: required
        :type delegator_addr: str

        :returns: Delegations for delegator with address
        :rtype: QueryDelegatorDelegationsResponse
        """
        stub = staking_query_grpc.QueryStub(self.grpc_channel)
        return stub.DelegatorDelegations(
            staking_query.QueryDelegatorDelegationsRequest(
                delegator_addr=delegator_addr,
            )
        )

    def delegator_unbonding_delegations(
        self,
        delegator_addr: str,
    ) -> staking_query.QueryDelegatorUnbondingDelegationsResponse:
        """
        Get delegator unbonding delegations

        :param delegator_addr: required
        :type delegator_addr: str

        :returns: Unbonding delegations for delegator with address
        :rtype: QueryDelegatorUnbondingDelegationsResponses
        """
        stub = staking_query_grpc.QueryStub(self.grpc_channel)
        return stub.DelegatorUnbondingDelegations(
            staking_query.QueryDelegatorUnbondingDelegationsRequest(
                delegator_addr=delegator_addr,
            )
        )

    def user_stats(self, address: str) -> stats_type.UserStats:
        '''
        Get user stats for an address

        :param address: required
        :type address: str

        :returns: User stats for address
        :rtype: stats_type.UserStats
        '''
        stub = stats_querry_grpc.QueryStub(self.grpc_channel)
        return stub.UserStats(
            stats_query.QueryUserStatsRequest(user=address)
        ).stats

    def subaccount(self, address: str, account_number: int) -> Optional[subaccount_type.Subaccount]:
        '''
        Get subaccount information

        :param address: required
        :type address: str

        :returns: Subaccount information, including account number and sequence
        '''
        stub = subaccounts_query_grpc.QueryStub(self.grpc_channel)
        return stub.Subaccount(
            subaccounts_query.QueryGetSubaccountRequest(
                owner=address,
                number=account_number,
            )
        ).subaccount

    def subaccounts(self) -> subaccounts_query.QuerySubaccountAllResponse:
        '''
        Get all subaccounts

        :returns: Subaccount information, including account number and sequence
        '''
        stub = subaccounts_query_grpc.QueryStub(self.grpc_channel)
        return stub.SubaccountAll(
            subaccounts_query.QueryAllSubaccountRequest()
        )

    def withdrawal_and_transfers_blocked_info(self) -> subaccounts_query.QueryGetWithdrawalAndTransfersBlockedInfoResponse:
        '''
        Get withdrawal and transfers blocked info

        :returns: Withdrawal and transfers blocked info
        :rtype: QueryGetWithdrawalAndTransfersBlockedInfoResponse
        '''
        stub = subaccounts_query_grpc.QueryStub(self.grpc_channel)
        return stub.GetWithdrawalAndTransfersBlockedInfo(
            subaccounts_query.QueryGetWithdrawalAndTransfersBlockedInfoRequest()
        )
