import json

import numpy as np
import pandas as pd

from pyaml_env import parse_config

from acx.data.chains import SHORTNAME_TO_ID
from acx.utils import cutAndPowerScore



if __name__ == "__main__":
    # Load parameters
    params = parse_config("parameters.yaml")

    # Create block to date lookup function
    blocks = pd.read_json("raw/blocks.json", orient="records")

    blockLookup = {}
    for chain in params["bridgoor"]["chains"]:
        chainId = SHORTNAME_TO_ID[chain]

        blockToDate = blocks.query("chainId == @chainId").sort_values("block")
        _block = blockToDate["block"].to_numpy()
        _date = blockToDate["date"].to_numpy()

        blockLookup[chainId] = {"blocks": _block, "dates": _date}


    def determineDate(x):
        chainId = 1 if x["version"] == 1 else x["originChain"]

        bl = blockLookup[chainId]

        _idx = np.searchsorted(bl["blocks"], x["block"])
        _date = bl["dates"][_idx]

        return _date

    # Inclusion parameters
    transferCount = params["bridgoor"]["parameters"]["inclusion"]["transfer_count"]
    transferCountVol = params["bridgoor"]["parameters"]["inclusion"]["transfer_count_volume"]
    volumeInclusion = params["bridgoor"]["parameters"]["inclusion"]["volume_inclusion"]

    # Score parameters
    power = params["bridgoor"]["parameters"]["score"]["power"]
    ub = params["bridgoor"]["parameters"]["score"]["ub"]

    totalACX = params["bridgoor"]["parameters"]["total_rewards"]

    # Load bridge data
    bridgeData = pd.read_json("intermediate/allBridges.json", orient="records")
    bridgeData["date"] = bridgeData.apply(determineDate, axis=1)

    # Load prices data
    prices = (
        pd.read_json("raw/prices.json", orient="records")
        .set_index(["date", "symbol"])
    )

    # Combine bridge and price data
    bridgesWPrices = bridgeData.merge(
        prices, left_on=["date", "symbol"], right_on=["date", "symbol"],
        how="left"
    )
    bridgesWPrices["amountUSD"] = bridgesWPrices.eval("price * amount")

    # Make sure we have prices for all observations
    if bridgesWPrices["price"].isna().any():
        raise ValueError("Missing prices and cannot compute bridgoor rewards")

    # Get transaction count and volume
    bridgoors = (
        bridgesWPrices
        .groupby("recipient")
        .agg(
            {
                "tx": "count",
                "amountUSD": "sum",
            }
        )
        .rename(
            columns={
                "tx": "nTransfers",
                "amountUSD": "totalVolume"
            }
        )
        .reset_index()
    )

    # Only users that meet criteria specified included in score
    bridgoors = bridgoors.query(
        "(totalVolume > @volumeInclusion) |" +
        "((nTransfers >= @transferCount) & (totalVolume > @transferCountVol))"
    )
    bridgoors["score"] = cutAndPowerScore(
        bridgoors["totalVolume"], 0.0, ub, power
    )
    bridgoors["acx"] = bridgoors.eval("score * @totalACX")

    out = bridgoors.set_index("recipient")["acx"].to_dict()
    with open("final/bridgoor_rewards.json", "w") as f:
        json.dump(out, f)
