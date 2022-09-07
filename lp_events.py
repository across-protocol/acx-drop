import json

import pandas as pd
import web3
import yaml

from acx.abis import BRIDGEPOOL_ABI, HUBPOOL_ABI
from acx.data.tokens import SYMBOL_TO_CHAIN_TO_ADDRESS
from acx.utils import findEvents


if __name__ == "__main__":
    # Load parameters
    with open("parameters.yaml", "r") as f:
        params = yaml.load(f, yaml.Loader)

    # Connect to RPC node
    provider = web3.Web3.HTTPProvider(
        params["rpc_node"]["mainnet"],
        request_kwargs={"timeout": 60}
    )
    w3 = web3.Web3(provider)

    # -------------------------------------
    # V1 Liquidity Add/Remove
    # -------------------------------------
    v1StartBlock = params["lp"]["v1_start_block"]
    v1EndBlock = params["lp"]["v1_end_block"]

    v1LiqAdded = {}
    v1LiqRemoved = {}
    for (token, poolAddress) in params["lp"]["v1_pools"].items():
        pool = w3.eth.contract(address=poolAddress, abi=BRIDGEPOOL_ABI)

        # Liquidity Added events
        v1LiqAdded[token] = findEvents(
            w3, pool.events.LiquidityAdded, v1StartBlock, v1EndBlock,
            500_000, {}, True
        )

        # Liquidity Removed events
        v1LiqRemoved[token] = findEvents(
            w3, pool.events.LiquidityRemoved, v1StartBlock, v1EndBlock,
            500_000, {}, True
        )

    with open("raw/v1LiquidityAdded.json", "w") as f:
        json.dump(v1LiqAdded, f)
    with open("raw/v1LiquidityRemoved.json", "w") as f:
        json.dump(v1LiqRemoved, f)

    # -------------------------------------
    # V2 Liquidity Add/Remove
    # -------------------------------------
    v2StartBlock = params["lp"]["v2_start_block"]
    v2EndBlock = params["lp"]["v2_end_block"]

    hub = w3.eth.contract(address=params["lp"]["v2_pools"]["hub"], abi=HUBPOOL_ABI)
    addresses = [
        SYMBOL_TO_CHAIN_TO_ADDRESS[token][1] for token in params["lp"]["v2_pools"]["tokens"]
    ]

    v2LiqAdded = findEvents(
        w3, hub.events.LiquidityAdded, v2StartBlock, v2EndBlock,
        500_000, {"l1Token": addresses}, True
    )
    v2LiqRemoved = findEvents(
        w3, hub.events.LiquidityRemoved, v2StartBlock, v2EndBlock,
        500_000, {"l1Token": addresses}, True
    )

    with open("raw/v2LiquidityAdded.json", "w") as f:
        json.dump(v2LiqAdded, f)

    with open("raw/v2LiquidityRemoved.json", "w") as f:
        json.dump(v2LiqRemoved, f)
