import json

import numpy as np
import pandas as pd

from pyaml_env import parse_config


if __name__ == "__main__":
    #
    # Load parameters
    #
    params = parse_config("parameters.yaml")

    # Block start and end information
    v1StartBlock = params["lp"]["v1_start_block"]
    v1EndBlock = params["lp"]["v1_end_block"]
    v2StartBlock = params["lp"]["v2_start_block"]
    v2EndBlock = params["lp"]["v2_end_block"]

    # Compute rewards per block
    nBlocks = (v2EndBlock - v2StartBlock) + (v1EndBlock - v1StartBlock)
    totalRewards = params["lp"]["parameters"]["total_rewards"]
    rewardPerBlock = totalRewards / nBlocks

    #
    # Load data
    #

    # Load block data
    BLOCKSTODATE = (
        pd.read_json("raw/blocks.json", orient="records")
        .query("chainId == 1")
        .sort_values("block")
        .loc[:, ["block", "date"]]
       )

    # Load prices data
    prices = (
        pd.read_json("raw/prices.json", orient="records")
        .set_index(["date", "symbol"])
    )

    # Load all positions an LP had at each relevant block
    v1LpPositions = pd.read_parquet("intermediate/v1CumulativeLp.parquet")
    v2LpPositions = pd.read_parquet("intermediate/v2CumulativeLp.parquet")
    for lpDf in [v1LpPositions, v2LpPositions]:
        lpDf.columns = lpDf.columns.set_names(["symbol", "lp"])

    # Create a list of all LPs - The LPs should all be in both datasets
    # but, if not, this makes sure that they are included
    lps = list(
        set(v1LpPositions.columns.get_level_values("lp").unique())
        .union(v2LpPositions.columns.get_level_values("lp").unique())
    )

    # Allocate space to save/update results
    addressRewards = pd.Series(np.zeros_like(lps, dtype=float), index=lps)

    # Separate v1 and v2 rewards
    for version in ["v1", "v2"]:
        # Depending on version get different subset of data
        if version == "v1":
            startBlock = v1StartBlock
            endBlock = v1EndBlock
            df = v1LpPositions.sort_index()
            exchangeRates = pd.read_json("raw/v1ExchangeRates.json", orient="records")
        else:
            startBlock = v2StartBlock
            endBlock = v2EndBlock
            df = v2LpPositions.sort_index()
            exchangeRates = pd.read_json("raw/v2ExchangeRates.json", orient="records")

        startIdx = BLOCKSTODATE["block"].searchsorted(startBlock, side="right") - 1
        endIdx = BLOCKSTODATE["block"].searchsorted(endBlock, side="right") - 1

        _datetoblock = BLOCKSTODATE.loc[startIdx:endIdx, :]

        # Date-by-date iteration so that the data we are working with is always
        # "small enough"
        for (idx, block_date) in _datetoblock.iterrows():
            # Extract date from _datetoblock
            date = block_date["date"]
            dailyBlockStart = max(startBlock, block_date["block"])
            print(f"Working on {date}")

            # Get daily price/exchange rate information
            dailyPrices = (
                prices.query("date == @date")
                .droplevel("date")
            )
            dailyERs = (
                exchangeRates.query("date == @date")
                .loc[:, ["symbol", "exchangeRate"]]
                .set_index("symbol")
            )

            # Convert price/exchange rate into a multiplier for each lp
            # token position
            dailyMultiplier = (
                dailyPrices.merge(
                    dailyERs, left_index=True, right_index=True,
                    how="right"
                )
                .assign(
                    multiplier=lambda x: x["price"] * x["exchangeRate"],
                )
                .loc[:, "multiplier"]
            )

            # Determine which block number to stop tracking at
            if (idx + 1) in _datetoblock.index:
                dailyBlockEnd = min(_datetoblock.at[idx+1, "block"], endBlock)
            else:
                dailyBlockEnd = endBlock

            # Break if the start and end block are the same
            if dailyBlockStart == dailyBlockEnd:
                continue

            # Create re-indexed data with all blocks for the day -- Columns are
            # given by (symbol, LP address) and index is given by block number
            dailyDf = df.reindex(index=np.arange(dailyBlockStart, dailyBlockEnd))

            # Find the last position prior to today's positions and, if there's
            # data in the first block of the day, add that as the first block
            # values
            positionIdx = df.index.searchsorted(dailyBlockStart, side="right")
            lastBlockWPosition = df.index[positionIdx]
            if lastBlockWPosition != dailyBlockStart:
                dailyDf.loc[dailyBlockStart, :] = df.loc[lastBlockWPosition, :]

            # Fill all missing blocks with the previous data -- We know
            # there's at least one in the day because we manually included
            # it above
            dailyDf = dailyDf.ffill()

            # Create a `nColumns` length array with all of the corresponding
            # multipliers for each column (i.e repeated multipliers based on
            # which symbol the column corresponds to)
            _multiplier = (
                dailyMultiplier.loc[dailyDf.columns.get_level_values("symbol")]
                .to_numpy()
            )

            # Multiply positions by the multiplier (i.e. exchange rate * price * bonus)
            dailyDf = dailyDf * _multiplier
            usdTotals = dailyDf.sum(axis=1)
            proRata = dailyDf.divide(usdTotals, axis=0)

            # Compute rewards
            dailyRewards = (
                # Convert fraction of pool -> rewards
                # blocks x (symbol, address)
                (proRata * rewardPerBlock)
                # Sum all rewards for each column
                # (symbol, address) x 1
                .sum(axis=0)
                # Move symbol to columns
                # address x symbol
                .unstack(level="symbol")
                # Sum all of the rewards for each LP
                # address x 1
                .sum(axis=1)
            )

            # Add to running total
            addressRewards += dailyRewards

    # Round small rewards to 1 ACX
    addressRewardsClipped = addressRewards.clip(lower=1)

    with open("final/lp_rewards.json", "w") as f:
        json.dump(addressRewardsClipped.to_dict(), f)
