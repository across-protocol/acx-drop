import json

import numpy as np
import pandas as pd
import web3
import yaml

from acx.data.tokens import SYMBOL_TO_DECIMALS, CHAIN_TO_ADDRESS_TO_SYMBOL
from acx.utils import scaleDecimals


def processTransfers(lpTransfers):
    """
    Helper to process transfers and store in an LP friendly format
    """
    out = []
    for token in lpTransfers.keys():
        for transfer in lpTransfers[token]:
            args = transfer["args"]

            # Person that transfer is to is increasing their LP position
            rowTo = {
                "block": transfer["blockNumber"],
                "tx": transfer["transactionHash"],
                "lp": args["to"],
                "symbol": token,
                "amount": scaleDecimals(args["value"], 18),
            }
            out.append(rowTo)

            # Person that transfer is from is decreasing their LP position
            rowFrom = {
                "block": transfer["blockNumber"],
                "tx": transfer["transactionHash"],
                "lp": args["from"],
                "symbol": token,
                "amount": -scaleDecimals(args["value"], 18)
            }
            out.append(rowFrom)

    return out


if __name__ == "__main__":
    # Load parameters
    with open("parameters.yaml", "r") as f:
        params = yaml.load(f, yaml.Loader)

    # Get start/end blocks for LP rewards
    v1StartBlock = params["lp"]["v1_start_block"]
    v1EndBlock = params["lp"]["v1_end_block"]

    v2StartBlock = params["lp"]["v2_start_block"]
    v2EndBlock = params["lp"]["v2_end_block"]

    # Load raw data
    with open("raw/v1Transfers.json", "r") as f:
        v1TransfersRaw = json.loads(f.read())
    v1Transfers = pd.DataFrame(processTransfers(v1TransfersRaw))

    with open("raw/v2Transfers.json", "r") as f:
        v2TransfersRaw = json.loads(f.read())
    v2Transfers = pd.DataFrame(processTransfers(v2TransfersRaw))

    # Get all blocks and LPs
    allLps = list(
        set(v1Transfers["lp"].unique())
        .union(set(v2Transfers["lp"].unique()))
    )
    allTokens = params["lp"]["tokens"]
    newIndex = pd.MultiIndex.from_product([allTokens, allLps])

    # Cumulative totals
    v1Df = (
        v1Transfers
        .pivot_table(
            index="block", columns=["symbol", "lp"], values="amount"
        )
        .fillna(0.0)
        .reindex(columns=newIndex, fill_value=0.0)
        .sort_index()
        .cumsum()
        .loc[v1StartBlock:v1EndBlock, :]
    )
    v1Df.to_parquet("intermediate/v1CumulativeLP.parquet")

    # Cumulative totals
    v2Df = (
        v2Transfers
        .pivot_table(
            index="block", columns=["symbol", "lp"], values="amount"
        )
        .fillna(0.0)
        .reindex(columns=newIndex, fill_value=0.0)
        .sort_index()
        .cumsum()
        .loc[v2StartBlock:v2EndBlock, :]
    )
    v2Df.to_parquet("intermediate/v2CumulativeLP.parquet")
