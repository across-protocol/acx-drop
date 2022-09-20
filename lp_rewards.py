import json

import numpy as np
import pandas as pd

from pyaml_env import parse_config


# Load block data
BLOCKSTODATE = (
    pd.read_json("raw/blocks.json", orient="records")
    .query("chainId == 1")
    .sort_values("block")
    .loc[:, ["block", "date"]]
)
BLOCKS = BLOCKSTODATE["block"].to_numpy()
DATES = BLOCKSTODATE["date"].to_numpy()


def blockToDate(block):
    """
    Given a block, use `BLOCKS` and `DATES` to map the block
    to a particular date
    """
    idx = np.searchsorted(BLOCKS, block, side="right") - 1

    return DATES[idx]


if __name__ == "__main__":
    # Load parameters
    params = parse_config("parameters.yaml")

    # Load exchange rate data (TODO)
    # exchangeRates = (
    #     pd.read_json("raw/exchange_rates.json", orient="records")
    #     .set_index(["block", "token"])
    # )

    # Load prices data
    prices = (
        pd.read_json("raw/prices.json", orient="records")
        .set_index(["date", "symbol"])
    )

    # Load all positions an LP had at each relevant block --
    # `v?CumulativeLP.parquet` already restricts to only blocks of interest
    v1StartBlock = params["lp"]["v1_start_block"]
    v1EndBlock = params["lp"]["v2_end_block"]
    v2StartBlock = params["lp"]["v2_start_block"]
    v2EndBlock = params["lp"]["v2_end_block"]
    lpPositions = pd.concat(
        [
            pd.read_parquet("intermediate/v1CumulativeLp.parquet"),
            pd.read_parquet("intermediate/v2CumulativeLp.parquet")
        ], axis=0, ignore_index=False
    )
    lpPositions.columns = lpPositions.columns.set_names(["symbol", "lp"])
    lps = lpPositions.columns.get_level_values("lp").unique()

    # Compute rewards per block
    nBlocks = (v2EndBlock - v2StartBlock) + (v1EndBlock - v1StartBlock)
    totalRewards = params["lp"]["parameters"]["total_rewards"]
    rewardPerBlock = totalRewards / nBlocks

    # Iterate through all blocks of interest
    addressRewards = pd.Series(np.zeros_like(lps), index=lps)
    blocks = list(range(v1StartBlock, v1EndBlock)) + list(range(v2StartBlock, v2EndBlock))
    for block in blocks:
        if block % 100 == 0:
            print(f"Currently working on {block}")

        # Get the corresponding element of the cumulative LP positions
        # so that we can compute their relative positions
        lpIdx = lpPositions.index.searchsorted(block, side="right") - 1
        idxBlock = lpPositions.index[lpIdx]

        # Find date that corresponded to that block so we can include prices
        date = blockToDate(block)

        positions = (
            lpPositions
            .iloc[lpIdx, :]
            .reset_index()
            .merge(prices.loc[date, :], left_on="symbol", right_index=True)
            .rename(columns={idxBlock: "amount"})
        )

        # TODO: This is still missing exchange rate.
        positions["amountUSD"] = positions.eval("amount * price")

        # Compute pro-rata shares
        proRata = (
            positions.groupby("lp")["amountUSD"].sum() /
            positions["amountUSD"].sum()
        )
        addressRewards += proRata * rewardPerBlock

    with open("final/lp_rewards.json", "w") as f:
        json.dump(addressRewards.to_dict(), f)
