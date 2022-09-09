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

    v1LiqAdded = {}
    v1LiqRemoved = {}
    for token in params["lp"]["v1_pools"]["tokens"]:
        # Get information about specific BridgePool
        # NOTE: We have to start with `bridgeInfo["first_block"]` because
        #       we need to track liquidity deposits/removals that occurred
        #       prior to the first block we track for...
        bridgeInfo = params["across"]["v1"]["mainnet"]["bridge"][token]
        poolAddress = bridgeInfo["address"]
        firstBlock = bridgeInfo["first_block"]
        v1EndBlock = params["lp"]["v1_end_block"]

        # Create BridgePool object
        pool = w3.eth.contract(address=poolAddress, abi=getABI("BridgePool"))

        # Liquidity Added events
        v1LiqAdded[token] = findEvents(
            w3, pool.events.LiquidityAdded, firstBlock, v1EndBlock,
            nBlocks, {}, True
        )

        # Liquidity Removed events
        v1LiqRemoved[token] = findEvents(
            w3, pool.events.LiquidityRemoved, firstBlock, v1EndBlock,
            nBlocks, {}, True
        )

    with open("raw/v1LiquidityAdded.json", "w") as f:
        json.dump(v1LiqAdded, f)
    with open("raw/v1LiquidityRemoved.json", "w") as f:
        json.dump(v1LiqRemoved, f)

    # -------------------------------------
    # V2 Liquidity Add/Remove
    # -------------------------------------
    hubInfo = params["across"]["v2"]["mainnet"]["hub"]
    v2StartBlock = hubInfo["first_block"]
    v2EndBlock = params["lp"]["v2_end_block"]

    hub = w3.eth.contract(address=hubInfo["address"], abi=getABI("HubPool"))
    addresses = [
        SYMBOL_TO_CHAIN_TO_ADDRESS[token][1]
        for token in params["lp"]["v2_pools"]["tokens"]
    ]

    for event in [hub.events.LiquidityAdded, hub.events.LiquidityRemoved]:
        # Get event name
        eventName = event.event_name

        events = findEvents(
            w3, event, v2StartBlock, v2EndBlock,
            nBlocks, {"l1Token": addresses}, True
        )

        with open(f"raw/v2{eventName}.json", "w") as f:
            json.dump(events, f)
