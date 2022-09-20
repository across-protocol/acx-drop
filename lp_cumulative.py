import json

import pandas as pd

from pyaml_env import parse_config

from acx.data.tokens import SYMBOL_TO_DECIMALS
from acx.utils import scaleDecimals


def processTransfers(lpTransfers, version=1):
    """
    Helper to process transfers and store in an LP friendly format
    """
    out = []
    for token in lpTransfers.keys():
        decimals = SYMBOL_TO_DECIMALS[token]

        for transfer in lpTransfers[token]:
            args = transfer["args"]

            for dest in ["to", "from"]:
                # Person that transfer is to is increasing their LP position while
                # the person it is from is decreasing their LP position
                sign = 1 if dest == "to" else -1
                row = {
                    "block": transfer["blockNumber"],
                    "tx": transfer["transactionHash"],
                    "lp": args[dest],
                    "symbol": token,
                    "amount": sign * scaleDecimals(args["value"], decimals),
                }
                out.append(row)

    return out


if __name__ == "__main__":
    # Load parameters
    params = parse_config("parameters.yaml")

    # Get start/end blocks for LP rewards
    v1StartBlock = params["lp"]["v1_start_block"]
    v1EndBlock = params["lp"]["v1_end_block"]

    v2StartBlock = params["lp"]["v2_start_block"]
    v2EndBlock = params["lp"]["v2_end_block"]

    # Load raw data
    with open("raw/v1Transfers.json", "r") as f:
        v1TransfersRaw = json.loads(f.read())
    v1Transfers = pd.DataFrame(processTransfers(v1TransfersRaw, 1))

    with open("raw/v2Transfers.json", "r") as f:
        v2TransfersRaw = json.loads(f.read())
    v2Transfers = pd.DataFrame(processTransfers(v2TransfersRaw, 2))

    # Get all blocks and LPs -- We will exclude the 0x0 address since it
    # isn't a real LP and is just used in minting/burning
    allLps = list(
        set(v1Transfers["lp"].unique())
        .union(set(v2Transfers["lp"].unique()))
        .difference(set(["0x0000000000000000000000000000000000000000"]))
    )
    allTokens = params["lp"]["tokens"]
    newIndex = pd.MultiIndex.from_product([allTokens, allLps])

    # Cumulative totals
    for version in [1, 2]:
        if version == 1:
            _df = v1Transfers
            startBlock, endBlock = v1StartBlock, v1EndBlock
        elif version == 2:
            _df = v2Transfers
            startBlock, endBlock = v2StartBlock, v2EndBlock
        else:
            raise ValueError("Version must be 1 or 2")

        data = (
            _df
            .pivot_table(
                index="block", columns=["symbol", "lp"], values="amount",
                aggfunc="sum"
            )
            .fillna(0.0)
            .reindex(columns=newIndex, fill_value=0.0)
            .sort_index()
            .cumsum()
            .loc[startBlock:endBlock, :]
        )
        data.to_parquet(f"intermediate/v{version}CumulativeLp.parquet")
