import datetime as dt
import time

import pandas as pd
import web3

from pyaml_env import parse_config

from acx.abis import getABI
from acx.data.chains import SHORTNAME_TO_ID
from acx.data.tokens import CHAIN_TO_ADDRESS_TO_SYMBOL, SYMBOL_TO_DECIMALS
from acx.utils import findEvents, scaleDecimals


if __name__ == "__main__":
    # Load parameters
    params = parse_config("parameters.yaml")

    cbridgeRelays = []
    for chain in params["bt"]["cbridge"]["chains"]:
        chainId = SHORTNAME_TO_ID[chain]
        chainInfo = params["bt"]["cbridge"]["contract_info"][chainId]

        # Web 3 instance for particular chain
        provider = web3.Web3.HTTPProvider(
            params["rpc_node"][chain],
            request_kwargs={"timeout": 60}
        )
        w3 = web3.Web3(provider)

        # Create the cBridge bridge
        bridgeAddress = chainInfo["address"]
        bridge = w3.eth.contract(
            address=bridgeAddress, abi=getABI("cBridgeBridge")
        )

        # Get first, last block, and number of blocks to query at once
        fb = chainInfo["first_block"]
        lb = chainInfo["last_block"]
        nBlocks = 50_000

        relays = findEvents(
            w3, bridge.events.Relay, startBlock, lastBlock,
            nBlocks, {}, True
        )



def retrieveRelays(w3, bridge, startBlock, lastBlock, nBlocks):
    """
    Collect data about the `Relay` event from the CBridge
    contracts

    Parameters
    ----------
    w3 : web3.Web3
        A web3 object
    pool : web3.Contract
        A web3
    start_block : int
        The starting block to collect
    last_block : int
        The ending block (inclusive)

    Returns
    -------
    df : pd.DataFrame
        A DataFrame with all of the pool data for relevant time period
    """
    # Meta data about the pool
    chainId = w3.eth.chainId
    ADDRESS_TO_SYMBOL = CHAIN_TO_ADDRESS_TO_SYMBOL[chainId]

    # Collect swap data
    relays = findEvents(
        w3, bridge.events.Relay, startBlock, lastBlock,
        nBlocks, {}, True
    )

    out = []
    for relay in relays:
        relayArgs = relay["args"]

        # Token address
        tokenAddress = relayArgs["token"]
        if tokenAddress not in ADDRESS_TO_SYMBOL.keys():
            continue

        symbol = ADDRESS_TO_SYMBOL[tokenAddress]
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

    return out
