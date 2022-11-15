import json

import pandas as pd
import web3

from pyaml_env import parse_config

from acx.utils import cutAndPowerScore


if __name__ == "__main__":
    # Load parameters
    params = parse_config("parameters.yaml")

    # Inclusion parameters
    transferCount = params["traveler"]["parameters"]["inclusion"]["transfer_count"]
    transferCountVol = params["traveler"]["parameters"]["inclusion"]["transfer_count_volume"]
    volumeInclusion = params["traveler"]["parameters"]["inclusion"]["volume_inclusion"]

    # Score parameters
    power = params["traveler"]["parameters"]["score"]["power"]
    ub = params["traveler"]["parameters"]["score"]["ub"]

    travelStartBlock = params["traveler"]["travel_start_block"]
    travelEndBlock = params["traveler"]["travel_end_block"]

    # Read all transfers that occurred on other bridges
    df = pd.read_parquet("intermediate/travelerTransfers.parquet")

    # Load prices and merge into dataframe
    prices = (
        pd.read_json("raw/prices.json", orient="records")
        .set_index(["date", "symbol"])
    )
    df = df.merge(
        prices, left_on=["date", "symbol"], right_index=True, how="left"
    )
    df["amountUSD"] = df.eval("price * amount")

    # Load Across transfers
    acrossAddresses = (
        pd.read_json("intermediate/bridgoorTransactions.json", orient="records")
        ["recipient"]
        .unique()
    )
    acrossAddresses = list(map(web3.Web3.toChecksumAddress, acrossAddresses))

    # Filter out any users that have used Across already
    df = df.query("traveler not in @acrossAddresses")

    # Load Across LPs -- Only look at pre-traveler LPs for exclusion
    v1LpPositions = (
        pd.read_parquet("intermediate/v1CumulativeLp.parquet")
        .loc[:travelStartBlock[1], :]
        .max()
        > 1e-18
    )
    v2LpPositions = (
        pd.read_parquet("intermediate/v2CumulativeLp.parquet")
        .loc[:travelStartBlock[1], :]
        .max()
        > 1e-18
    )

    acrossLps = list(
        set(v1LpPositions.index[v1LpPositions].get_level_values(1).unique())
        .union(v2LpPositions.index[v2LpPositions].get_level_values(1).unique())
    )

    # Filter out any users that have LP'd for Across (prior to BT)
    df = df.query("traveler not in @acrossLps")

    # Filter out users who have been identified as sybil
    with open("raw/sybil.json", "r") as f:
        sybils = json.loads(f.read())
    df = df.query("traveler not in @sybils")

    # Now we can aggregate and calculate scores
    travelers = (
        df.groupby("traveler")
        .agg(
            {
                "tx": "count",
                "amountUSD": "sum"
            }
        )
        .rename(columns={
            "tx": "nTransfers",
            "amountUSD": "totalVolume"
        })
    )

    # Filter to only include bridgoors who met qualifications
    query_statement = "(nTransfers >= @transferCount & totalVolume >= @transferCountVol) |"
    query_statement += "(totalVolume >= @volumeInclusion)"
    travelers = travelers.query(query_statement)

    travelers["score"] = cutAndPowerScore(
        travelers["totalVolume"], 0.0, ub, power
    )

    # Save output
    travelers = travelers.sort_values("totalVolume", ascending=False)
    (100 * travelers["score"]).to_json("final/traveler_score.json")
