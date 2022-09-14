import json

import pandas as pd
import web3
import yaml

from acx.abis import getABI
from acx.data.tokens import SYMBOL_TO_CHAIN_TO_ADDRESS
from acx.utils import findEvents


if __name__ == "__main__":
    # Load parameters
    with open("parameters.yaml", "r") as f:
        params = yaml.load(f, yaml.Loader)
    nBlocks = params["lp"]["n_blocks"]

    # Connect to RPC node
    provider = web3.Web3.HTTPProvider(
        params["rpc_node"]["mainnet"],
        request_kwargs={"timeout": 60}
    )
    w3 = web3.Web3(provider)

    # -------------------------------------
    # V1 Liquidity Add/Remove
    # -------------------------------------
    v1EndBlock = params["lp"]["v1_end_block"]

    v1Transfers = {}
    for token in params["lp"]["tokens"]:
        # Get information about specific BridgePool
        # NOTE: We have to start with `bridgeInfo["first_block"]` because
        #       we need to track liquidity deposits/removals that occurred
        #       prior to the first block we track for...
        bridgeInfo = params["across"]["v1"]["mainnet"]["bridge"][token]
        poolAddress = bridgeInfo["address"]
        v1FirstBlock = bridgeInfo["first_block"]
        v1EndBlock = params["lp"]["v1_end_block"]

        # Create BridgePool object
        pool = w3.eth.contract(address=poolAddress, abi=getABI("BridgePool"))

        # Track transfer events
        v1Transfers[token] = findEvents(
            w3, pool.events.Transfer, v1FirstBlock, v1EndBlock,
            nBlocks, {}, True
        )

    with open("raw/v1Transfers.json", "w") as f:
        json.dump(v1Transfers, f)

    # -------------------------------------
    # V2 Liquidity Add/Remove
    # -------------------------------------
    hubInfo = params["across"]["v2"]["mainnet"]["hub"]
    v2FirstBlock = hubInfo["first_block"]
    v2EndBlock = params["lp"]["v2_end_block"]

    hub = w3.eth.contract(address=hubInfo["address"], abi=getABI("HubPool"))

    v2Transfers = {}
    for token in params["lp"]["tokens"]:
        lpTokenAddress = hub.functions.pooledTokens(SYMBOL_TO_CHAIN_TO_ADDRESS[token][1]).call()[0]
        lpToken = w3.eth.contract(address=lpTokenAddress, abi=getABI("ERC20"))

        v2Transfers[token] = findEvents(
            w3, lpToken.events.Transfer, v2FirstBlock, v2EndBlock,
            nBlocks, {}, True
        )

        with open(f"raw/v2Transfers.json", "w") as f:
            json.dump(events, f)
