import pandas as pd
import web3

from pyaml_env import parse_config

from acx.abis import getABI
from acx.data.chains import SHORTNAME_TO_ID
from acx.data.tokens import (
    CHAIN_TO_ADDRESS_TO_SYMBOL, SYMBOL_TO_CHAIN_TO_ADDRESS, SYMBOL_TO_DECIMALS
)
from acx.utils import findEvents, scaleDecimals


if __name__ == "__main__":
    # Load parameters
    params = parse_config("parameters.yaml")

    # Tokens to support
    SUPPORTED_CHAINS = params["traveler"]["cbridge"]["chains"]
    SUPPORTED_TOKENS = params["traveler"]["cbridge"]["tokens"]

    cbridgeRelays = []
    for chain in SUPPORTED_CHAINS:
        chainId = SHORTNAME_TO_ID[chain]
        chainInfo = params["traveler"]["cbridge"]["contract_info"][chainId]

        # Web 3 instance for particular chain
        provider = web3.Web3.HTTPProvider(
            params["rpc_node"][chain],
            request_kwargs={"timeout": 60}
        )
        w3 = web3.Web3(provider)

        # Create the cBridge bridge
        bridgeAddress = chainInfo["address"]
        bridge = w3.eth.contract(
            address=bridgeAddress, abi=getABI("cBridge")
        )

        # Get first, last block, and number of blocks to query at once
        fb = chainInfo["first_block"]
        lb = chainInfo["last_block"]
        nBlocks = params["traveler"]["n_blocks"][chainId]

        # Find token addresses that we might be interested in
        wantedTokenAddresses = []
        for token in SUPPORTED_TOKENS:
            if chainId in SYMBOL_TO_CHAIN_TO_ADDRESS[token].keys():
                wantedTokenAddresses.append(
                    SYMBOL_TO_CHAIN_TO_ADDRESS[token][chainId]
                )

        relays = findEvents(
            w3, bridge.events.Relay, fb, lb,
            nBlocks, {}, True
        )

        out = []
        for relay in relays:
            relayArgs = relay["args"]

            # Skip tokens that aren't in our "tokens universe"
            tokenAddress = relayArgs["token"]
            if tokenAddress not in wantedTokenAddresses:
                continue

            symbol = CHAIN_TO_ADDRESS_TO_SYMBOL[chainId][tokenAddress]
            decimals = SYMBOL_TO_DECIMALS[symbol]

            # Save row by row
            row = {}

            row["block"] = relay["blockNumber"]
            row["tx"] = relay["transactionHash"]
            row["originChainId"] = relayArgs["srcChainId"]
            row["destinationChainId"] = chainId
            row["transferId"] = relayArgs["transferId"]
            row["sender"] = relayArgs["sender"]
            row["receiver"] = relayArgs["receiver"]
            row["symbol"] = symbol
            row["amount"] = scaleDecimals(relayArgs["amount"], decimals)

            out.append(row)
        chainDf = pd.DataFrame(out)
        cbridgeRelays.append(chainDf)

    df = pd.concat(cbridgeRelays, axis=0, ignore_index=True)
    df.to_parquet("raw/cbridge_transfers.parquet")
