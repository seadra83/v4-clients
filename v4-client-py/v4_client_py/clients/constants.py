from enum import Enum
from typing import Optional, Union
from ..chain.aerial.config import NetworkConfig


# ------------ API URLs ------------
INDEXER_API_HOST_LOCALNET = 'http://localhost:3002'
INDEXER_API_HOST_MAINNET = 'https://indexer.dydx.trade'
INDEXER_API_HOST_TESTNET = 'https://indexer.v4testnet.dydx.exchange'

INDEXER_WS_HOST_LOCALNET = 'ws://localhost:3003/v4/ws'
INDEXER_WS_HOST_MAINNET = 'wss://indexer.dydx.trade/v4/ws'
INDEXER_WS_HOST_TESTNET = 'wss://indexer.v4testnet.dydx.exchange/v4/ws'

FAUCET_API_HOST_TESTNET = 'https://faucet.v4testnet.dydx.exchange'

VALIDATOR_API_HOST_LOCALNET = 'http://localhost:1317'
VALIDATOR_API_HOST_MAINNET = 'https://dydx-ops-rest.kingnodes.com'
VALIDATOR_API_HOST_TESTNET = 'https://test-dydx.kingnodes.com'

VALIDATOR_GRPC_LOCALNET = 'localhost:9090'
VALIDATOR_GRPC_MAINNET = 'dydx-ops-grpc.kingnodes.com:443'
VALIDATOR_GRPC_TESTNET = 'test-dydx-grpc.kingnodes.com:443'

# ------------ Ethereum Network IDs ------------
NETWORK_ID_MAINNET = 'dydx-mainnet-1'
NETWORK_ID_TESTNET = 'dydx-testnet-4'

# ------------ Network Config ------------
FEE_MINIMUM_MAINNET = 0
FEE_MINIMUM_TESTNET = 4630550000000000

FEE_DENOM_MAINNET = 'ibc/8E27BA2D5493AF5636760E354E46004562C46AB7EC0CC4C1CA14E9E20E2545B5'
FEE_DENOM_TESTNET = 'adv4tnt'

STAKE_DENOM_MAINNET = 'adydx'
STAKE_DENOM_TESTNET = 'adv4tnt'

# ------------ Market Statistic Day Types ------------
MARKET_STATISTIC_DAY_ONE = '1'
MARKET_STATISTIC_DAY_SEVEN = '7'
MARKET_STATISTIC_DAY_THIRTY = '30'

# ------------ Order Types ------------
ORDER_TYPE_LIMIT = 'LIMIT'
ORDER_TYPE_MARKET = 'MARKET'
ORDER_TYPE_STOP = 'STOP_LIMIT'
ORDER_TYPE_TRAILING_STOP = 'TRAILING_STOP'
ORDER_TYPE_TAKE_PROFIT = 'TAKE_PROFIT'

# ------------ Order Side ------------
ORDER_SIDE_BUY = 'BUY'
ORDER_SIDE_SELL = 'SELL'

# ------------ Time in Force Types ------------
TIME_IN_FORCE_GTT = 'GTT'
TIME_IN_FORCE_GTX = 'GTX'
TIME_IN_FORCE_FOK = 'FOK'
TIME_IN_FORCE_IOC = 'IOC'

# ------------ Position Status Types ------------
POSITION_STATUS_OPEN = 'OPEN'
POSITION_STATUS_CLOSED = 'CLOSED'
POSITION_STATUS_LIQUIDATED = 'LIQUIDATED'

# ------------ Order Status Types ------------
ORDER_STATUS_PENDING = 'PENDING'
ORDER_STATUS_OPEN = 'OPEN'
ORDER_STATUS_FILLED = 'FILLED'
ORDER_STATUS_CANCELED = 'CANCELED'
ORDER_STATUS_UNTRIGGERED = 'UNTRIGGERED'

# ------------ Transfer Status Types ------------
TRANSFER_STATUS_PENDING = 'PENDING'
TRANSFER_STATUS_CONFIRMED = 'CONFIRMED'
TRANSFER_STATUS_QUEUED = 'QUEUED'
TRANSFER_STATUS_CANCELED = 'CANCELED'
TRANSFER_STATUS_UNCONFIRMED = 'UNCONFIRMED'

# ------------ Markets ------------
MARKET_BTC_USD = 'BTC-USD'
MARKET_ETH_USD = 'ETH-USD'


# ------------ Assets ------------
ASSET_USDC = 'USDC'
ASSET_BTC = 'BTC'
ASSET_ETH = 'ETH'
COLLATERAL_ASSET = ASSET_USDC

# ------------ Synthetic Assets by Market ------------
SYNTHETIC_ASSET_MAP = {
    MARKET_BTC_USD: ASSET_BTC,
    MARKET_ETH_USD: ASSET_ETH,
}

# ------------ API Defaults ------------
DEFAULT_API_TIMEOUT = 3000

MAX_MEMO_CHARACTERS = 256

BECH32_PREFIX = 'dydx'


class BroadcastMode(Enum):
    BroadcastTxSync = 0
    BroadcastTxCommit = 1


class IndexerConfig:
    def __init__(
        self,
        rest_endpoint: str,
        websocket_endpoint: str,
    ):
        if rest_endpoint.endswith('/'):
            rest_endpoint = rest_endpoint[:-1]
        self.rest_endpoint = rest_endpoint
        self.websocket_endpoint = websocket_endpoint


class ValidatorConfig:
    def __init__(
        self,
        grpc_endpoint: str,
        chain_id: str,
        ssl_enabled: bool,
        network_config: NetworkConfig,
    ):
        self.grpc_endpoint = grpc_endpoint
        self.chain_id = chain_id
        self.ssl_enabled = ssl_enabled
        self.network_config = network_config


class Network:
    def __init__(
        self,
        env: str,
        validator_config: ValidatorConfig,
        indexer_config: IndexerConfig,
        faucet_endpoint: Optional[str] = None,
    ):
        self.env = env
        self.validator_config = validator_config
        self.indexer_config = indexer_config
        if faucet_endpoint is not None and faucet_endpoint.endswith('/'):
            faucet_endpoint = faucet_endpoint[:-1]
        self.faucet_endpoint = faucet_endpoint

    @classmethod
    def testnet(cls):
        validator_config = ValidatorConfig(
            grpc_endpoint=VALIDATOR_GRPC_TESTNET,
            chain_id=NETWORK_ID_TESTNET,
            ssl_enabled=True,
            network_config=NetworkConfig(
                chain_id=NETWORK_ID_TESTNET,
                url='grpc+https://' + VALIDATOR_GRPC_TESTNET,
                fee_minimum_gas_price=FEE_MINIMUM_TESTNET,
                fee_denomination=FEE_DENOM_TESTNET,
                staking_denomination=STAKE_DENOM_TESTNET,
                faucet_url=FAUCET_API_HOST_TESTNET,
            ),
        )
        indexer_config = IndexerConfig(
            rest_endpoint=INDEXER_API_HOST_TESTNET,
            websocket_endpoint=INDEXER_WS_HOST_TESTNET,
        )
        return cls(
            env='testnet',
            validator_config=validator_config,
            indexer_config=indexer_config,
            faucet_endpoint=FAUCET_API_HOST_TESTNET,
        )

    @classmethod
    def localnet(cls):
        validator_config = ValidatorConfig(
            grpc_endpoint=VALIDATOR_GRPC_LOCALNET,
            chain_id=NETWORK_ID_MAINNET,
            ssl_enabled=False,
            network_config=NetworkConfig(
                chain_id=NETWORK_ID_MAINNET,
                url='grpc+http://' + VALIDATOR_GRPC_LOCALNET,
                fee_minimum_gas_price=FEE_MINIMUM_MAINNET,
                fee_denomination=FEE_DENOM_MAINNET,
                staking_denomination=STAKE_DENOM_MAINNET,
                faucet_url=None,
            ),
        )
        indexer_config = IndexerConfig(
            rest_endpoint=INDEXER_API_HOST_LOCALNET,
            websocket_endpoint=INDEXER_WS_HOST_LOCALNET,
        )
        return cls(
            env='localnet',
            validator_config=validator_config,
            indexer_config=indexer_config,
            faucet_endpoint=None,
        )

    @classmethod
    def mainnet(cls):
        validator_config = ValidatorConfig(
            grpc_endpoint=VALIDATOR_GRPC_MAINNET,
            chain_id=NETWORK_ID_MAINNET,
            ssl_enabled=True,
            network_config=NetworkConfig(
                chain_id=NETWORK_ID_MAINNET,
                url='grpc+https://' + VALIDATOR_GRPC_MAINNET,
                fee_minimum_gas_price=FEE_MINIMUM_MAINNET,
                fee_denomination=FEE_DENOM_MAINNET,
                staking_denomination=STAKE_DENOM_MAINNET,
                faucet_url=None,
            ),
        )
        indexer_config = IndexerConfig(
            rest_endpoint=INDEXER_API_HOST_MAINNET,
            websocket_endpoint=INDEXER_WS_HOST_MAINNET,
        )
        return cls(
            env='mainnet',
            validator_config=validator_config,
            indexer_config=indexer_config,
            faucet_endpoint=None,
        )

    @classmethod
    def customnet(
        cls,
        grpc_endpoint: str,
        chain_id: str,
        rest_endpoint: str,
        websocket_endpoint: str,
        fee_minimum_gas_price: Union[int, float],
        fee_denomination: str,
        staking_denomination: str,
        ssl_enabled: bool = True,
        faucet_endpoint: Optional[str] = None,
    ):
        validator_config = ValidatorConfig(
            grpc_endpoint=grpc_endpoint,
            chain_id=chain_id,
            ssl_enabled=ssl_enabled,
            network_config=NetworkConfig(
                chain_id=chain_id,
                url=['grpc+http://', 'grpc+https://'][ssl_enabled] + grpc_endpoint,
                fee_minimum_gas_price=fee_minimum_gas_price,
                fee_denomination=fee_denomination,
                staking_denomination=staking_denomination,
                faucet_url=faucet_endpoint,
            )
        )
        indexer_config = IndexerConfig(
            rest_endpoint=rest_endpoint,
            websocket_endpoint=websocket_endpoint,
        )
        return cls(
            env='customnet',
            validator_config=validator_config,
            indexer_config=indexer_config,
            faucet_endpoint=faucet_endpoint,
        )

    def string(self):
        return self.env
