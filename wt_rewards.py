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
        pd.read_json("intermediate/allBridges.json", orient="records")
        ["recipient"]
        .unique()
    )
    acrossAddresses = list(map(web3.Web3.toChecksumAddress, acrossAddresses))

    # Filter out any users that have used Across already
    df = df.query("traveler not in @acrossAddresses")

    # Load Across LPs
    acrossLps = pd.read_json("final/lp_rewards.json", typ="series").index

    # Filter out any users that have LP'd for Across
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
    travelers["score"].to_json("final/traveler_rewards.json")
