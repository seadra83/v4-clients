import logging
from typing import Optional

import grpc  # type: ignore

from v4_proto.cosmos.auth.v1beta1 import (  # type: ignore
    auth_pb2 as auth_type,
    query_pb2 as auth_query,
    query_pb2_grpc as auth_query_grpc,
)
from v4_proto.cosmos.authz.v1beta1 import (  # type: ignore
    query_pb2_grpc as authz_query_grpc,
)
from v4_proto.cosmos.bank.v1beta1 import (  # type: ignore
    query_pb2_grpc as bank_query_grpc,
    query_pb2 as bank_query,
)
from v4_proto.cosmos.base.tendermint.v1beta1 import (  # type: ignore
    query_pb2 as tendermint_query,
    query_pb2_grpc as tendermint_query_grpc,
)
from v4_proto.cosmos.tx.v1beta1 import (  # type: ignore
    service_pb2_grpc as tx_service_grpc,
    service_pb2 as tx_service,
)
from v4_proto.dydxprotocol.assets import (  # type: ignore
    query_pb2_grpc as assets_query_grpc,
)
from v4_proto.dydxprotocol.clob import (  # type: ignore
    query_pb2_grpc as clob_query_grpc,
    query_pb2 as clob_query,
    clob_pair_pb2 as clob_pair_type,
    equity_tier_limit_config_pb2 as equity_tier_limit_config_type,
)
from v4_proto.dydxprotocol.perpetuals import (  # type: ignore
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
        self.chain_channel = (
            grpc.secure_channel(config.grpc_endpoint, credentials) if config.ssl_enabled
            else grpc.insecure_channel(config.grpc_endpoint)
        )
        self.config = config

        # chain stubs
        self.stubCosmosTendermint = tendermint_query_grpc.ServiceStub(
            self.chain_channel
        )
        self.stubAuth = auth_query_grpc.QueryStub(self.chain_channel)
        self.stubAuthz = authz_query_grpc.QueryStub(self.chain_channel)
        self.stubBank = bank_query_grpc.QueryStub(self.chain_channel)
        self.stubTx = tx_service_grpc.ServiceStub(self.chain_channel)
        self.stubAssets = assets_query_grpc.QueryStub(self.chain_channel)
        self.stubSubaccounts = subaccounts_query_grpc.QueryStub(self.chain_channel)
        self.stubPerpetuals = perpetuals_query_grpc.QueryStub(self.chain_channel)
        self.stubPrices = prices_query_grpc.QueryStub(self.chain_channel)
        self.stubClob = clob_query_grpc.QueryStub(self.chain_channel)
        self.stubRateLimit = rate_limit_query_grpc.QueryStub(self.chain_channel)

    # default client methods
    def latest_block(self) -> tendermint_query.GetLatestBlockResponse:
        '''
        Get lastest block

        :returns: Response, containing block information

        '''
        return self.stubCosmosTendermint.GetLatestBlock(
            tendermint_query.GetLatestBlockRequest()
        )

    def sync_timeout_height(self):
        try:
            block = self.latest_block()
            self.timeout_height = block.block.header.height + DEFAULT_TIMEOUTHEIGHT
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
        return self.stubTx.GetTx(tx_service.GetTxRequest(hash=tx_hash))

    def bank_balances(self, address: str):
        '''
        Get wallet account balances

        :returns: All assets in the wallet
        '''
        return self.stubBank.AllBalances(
            bank_query.QueryAllBalancesRequest(address=address)
        )

    def bank_balance(self, address: str, denom: str):
        '''
        Get wallet asset balance

        :param denom: required
        :type demon: str

        :returns: Asset balance given the denom

        :raises: DydxAPIError
        '''
        return self.stubBank.Balance(
            bank_query.QueryBalanceRequest(address=address, denom=denom)
        )

    def account(self, address: str) -> Optional[auth_type.BaseAccount]:
        '''
        Get account information

        :param address: required
        :type address: str

        :returns: Account information, including account number and sequence
        '''
        account_any = self.stubAuth.Account(
            auth_query.QueryAccountRequest(address=address)
        ).account
        account = auth_type.BaseAccount()
        if account_any.Is(account.DESCRIPTOR):
            account_any.Unpack(account)
            return account
        else:
            return None

    def subaccounts(self) -> subaccounts_query.QuerySubaccountAllResponse:
        '''
        Get all subaccounts

        :returns: Subaccount information, including account number and sequence
        '''
        return self.stubSubaccounts.SubaccountAll(
            subaccounts_query.QueryAllSubaccountRequest()
        )

    def subaccount(self, address: str, account_number: int) -> Optional[subaccount_type.Subaccount]:
        '''
        Get subaccount information

        :param address: required
        :type address: str

        :returns: Subaccount information, including account number and sequence
        '''
        return self.stubSubaccounts.Subaccount(
            subaccounts_query.QueryGetSubaccountRequest(
                owner=address,
                number=account_number,
            )
        ).subaccount

    def clob_pairs(self) -> clob_query.QueryClobPairAllResponse:
        '''
        Get all pairs

        :returns: All pairs
        '''
        return self.stubClob.ClobPairAll(
            clob_query.QueryAllClobPairRequest()
        )

    def clob_pair(self, pair_id: int) -> clob_pair_type.ClobPair:
        '''
        Get pair information

        :param pair_id: required
        :type pair_id: int

        :returns: Pair information
        '''
        return self.stubClob.ClobPair(
            clob_query.QueryGetClobPairRequest(id=pair_id)
        ).clob_pair

    def prices(self) -> prices_query.QueryAllMarketPricesResponse:
        '''
        Get all market prices

        :returns: All market prices
        '''
        return self.stubPrices.AllMarketPrices(
            prices_query.QueryAllMarketPricesRequest()
        )

    def price(self, market_id: int) -> market_price_type.MarketPrice:
        '''
        Get market price

        :param market_id: required
        :type market_id: int

        :returns: Market price
        '''
        return self.stubPrices.MarketPrice(
            prices_query.QueryMarketPriceRequest(id=market_id)
        ).market_price

    def equity_tier_limit_config(self) -> equity_tier_limit_config_type.EquityTierLimitConfiguration:
        '''
        Get equity tier limit configuration

        :returns: Equity tier limit configuration
        '''
        return self.stubClob.EquityTierLimitConfiguration(
            clob_query.QueryEquityTierLimitConfigurationRequest()
        ).equity_tier_limit_config

    def withdrawal_and_transfers_blocked_info(self) -> subaccounts_query.QueryGetWithdrawalAndTransfersBlockedInfoResponse:
        '''
        Get withdrawal and transfers blocked info

        :returns: Withdrawal and transfers blocked info
        :rtype: QueryGetWithdrawalAndTransfersBlockedInfoResponse
        '''
        return self.stubSubaccounts.GetWithdrawalAndTransfersBlockedInfo(
            subaccounts_query.QueryGetWithdrawalAndTransfersBlockedInfoRequest()
        )

    def withdrawal_capacity_by_denom(self, denom: str) -> rate_limit_query.QueryCapacityByDenomResponse:
        '''
        Get withdrawal capacity by denom

        :param denom: required
        :type denom: str

        :returns: Withdrawal capacity by denom
        :rtype: QueryCapacityByDenomResponse
        '''
        return self.stubRateLimit.CapacityByDenom(
            rate_limit_query.QueryCapacityByDenomRequest(denom=denom)
        )
