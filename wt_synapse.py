import pandas as pd
import web3

from pyaml_env import parse_config

from acx.abis import getABI
from acx.data.chains import SHORTNAME_TO_ID
from acx.data.tokens import (
    CHAIN_TO_ADDRESS_TO_SYMBOL, SYMBOL_TO_CHAIN_TO_ADDRESS, SYMBOL_TO_DECIMALS
)
from acx.utils import findEvents, scaleDecimals


# Mapping comes from going to the pool contract and identifying
# the tokens using `getToken` function
# List of pools can be found at: https://github.com/BlazeWasHere/SYN-Tracker-API/blob/819309573e0288f8b2466bb3455a949e4ebf3495/syn/utils/data.py#L110-L268
CHAIN_TO_SYNTOKEN_TO_SWAPSYMBOL = {
    1: {
        # USD pool
        "0x1B84765dE8B7566e4cEAF4D0fD3c5aF52D3DdE4F": {
            0: "DAI",
            1: "USDC",
            2: "USDT"
        }
    },
    10: {
        # USD pool
        "0x67C10C397dD0Ba417329543c1a40eb48AAa7cd00": {
            0: "nUSD",
            1: "USDC",
        },
        # ETH pool
        "0x809DC529f07651bD43A172e8dB6f4a7a0d771036": {
            0: "nETH",
            1: "WETH"
        }
    },
    137: {
        # USD pool
        "0xB6c473756050dE474286bED418B77Aeac39B02aF": {
            0: "nUSD",
            1: "DAI",
            2: "USDC",
            3: "USDT"
        }
    },
    288: {
        # USD pool
        "0x6B4712AE9797C199edd44F897cA09BC57628a1CF": {
            0: "nUSD",
            1: "DAI",
            2: "USDC",
            3: "USDT"
        },
        "0x96419929d7949D6A801A6909c145C8EEf6A40431": {
            0: "nETH",
            1: "WETH"
        }
    },
    42161: {
        # USD pool
        "0x2913E812Cf0dcCA30FB28E6Cac3d2DCFF4497688": {
            0: "nUSD",
            1: "MIM",
            2: "USDC",
            3: "USDT"
        },
        # ETH pool
        "0x3ea9B0ab55F34Fb188824Ee288CeaEfC63cf908e": {
            0: "nETH",
            1: "WETH"
        }
    },
}


if __name__ == "__main__":
    # Load parameters
    params = parse_config("parameters.yaml")

    # Chains/Tokens to support
    SUPPORTED_CHAINS = params["traveler"]["synapse"]["chains"]
    SUPPORTED_TOKENS = params["traveler"]["synapse"]["tokens"]
    contractInfo = params["traveler"]["synapse"]["contract_info"]

    synapseInflows = []
    for chain in SUPPORTED_CHAINS:
        chainId = SHORTNAME_TO_ID[chain]
        chainInfo = contractInfo[chainId]

        # Select a single chain so we have address -> symbol
        ADDRESS_TO_SYMBOL = CHAIN_TO_ADDRESS_TO_SYMBOL[chainId]

        # Web 3 instance for particular chain
        provider = web3.Web3.HTTPProvider(
            params["rpc_node"][chain],
            request_kwargs={"timeout": 60}
        )
        w3 = web3.Web3(provider)

        # First, last block, and number of blocks to search at once
        fb = chainInfo["first_block"]
        lb = chainInfo["last_block"]
        nBlocks = params["traveler"]["n_blocks"][chainId]

        # Create synapse bridge
        bridgeAddress = chainInfo["address"]
        bridge = w3.eth.contract(
            address=bridgeAddress, abi=getABI("SynapseBridge")
        )

        # Inflow events as defined by Synapse here:
        # https://github.com/synapsecns/synapse-indexer/blob/6d3fcb4cd57d2413800a1c6858b8215a880b27f3/config/topics.js
        inflowEvents = [
            bridge.events.TokenWithdraw, bridge.events.TokenWithdrawAndRemove,
            bridge.events.TokenMint, bridge.events.TokenMintAndSwap
        ]

        for event in inflowEvents:
            # Get event name so that we can do logic on it
            eventName = event.event_name

            # Collect event data
            inflows = findEvents(w3, event, fb, lb, nBlocks, {}, True)

            for inflow in inflows:
                # Separate args into more accessible object
                inflowArgs = inflow["args"]

                # Extract token address and make sure that it's a token
                # in our list of tokens
                tokenAddress = inflowArgs["token"]
                if tokenAddress not in ADDRESS_TO_SYMBOL.keys():
                    continue

                # Depending on the event type, we have to do different things
                if eventName in ["TokenWithdraw", "TokenMint"]:
                    symbolFrom = ADDRESS_TO_SYMBOL[tokenAddress]
                    symbolTo = symbolFrom

                elif eventName == "TokenWithdrawAndRemove":
                    symbolFrom = ADDRESS_TO_SYMBOL[tokenAddress]

                    if inflowArgs["swapSuccess"]:
                        idxTo = inflowArgs["swapTokenIndex"]
                        symbolTo = CHAIN_TO_SYNTOKEN_TO_SWAPSYMBOL[chainId][tokenAddress][idxTo]
                    else:
                        symbolTo = ADDRESS_TO_SYMBOL[tokenAddress]

                elif eventName == "TokenMintAndSwap":
                    # Determine index of entry and exit
                    idxFrom = inflowArgs["tokenIndexFrom"]
                    if inflowArgs["swapSuccess"]:
                        idxTo = inflowArgs["tokenIndexTo"]
                    else:
                        idxTo = inflowArgs["tokenIndexFrom"]

                    symbolFrom = CHAIN_TO_SYNTOKEN_TO_SWAPSYMBOL[chainId][tokenAddress][idxFrom]
                    symbolTo = CHAIN_TO_SYNTOKEN_TO_SWAPSYMBOL[chainId][tokenAddress][idxTo]

                # Make sure it is a token that we are tracking for bridge traveler
                if symbolTo not in SUPPORTED_TOKENS:
                    continue

                decimalsFrom = SYMBOL_TO_DECIMALS[symbolFrom]
                decimalsTo = SYMBOL_TO_DECIMALS[symbolTo]

                # Save row by row
                row = {}

                row["eventName"] = eventName
                row["kappa"] = inflowArgs["kappa"]
                row["block"] = inflow["blockNumber"]
                row["tx"] = inflow["transactionHash"]
                row["chainId"] = chainId
                row["recipient"] = inflowArgs["to"]
                row["symbol"] = symbolTo
                row["amount"] = scaleDecimals(inflowArgs["amount"], decimalsTo)
                row["fee"] = scaleDecimals(inflowArgs["fee"], decimalsFrom)

                synapseInflows.append(row)

    df = pd.DataFrame(synapseInflows)
    df.to_parquet("raw/synapse_transfers.parquet")
