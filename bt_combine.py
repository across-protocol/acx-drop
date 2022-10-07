import datetime as dt

import numpy as np
import pandas as pd
import web3

from pyaml_env import parse_config

from acx.data.chains import SHORTNAME_TO_ID


if __name__ == "__main__":
    # Load parameters
    params = parse_config("parameters.yaml")

    # Create block to date lookup function
    blocks = pd.read_json("raw/blocks.json", orient="records")

    blockLookup = {}
    for chain in params["traveler"]["chains"]:
        chainId = SHORTNAME_TO_ID[chain]

        blockToDate = blocks.query("chainId == @chainId").sort_values("block")
        _block = blockToDate["block"].to_numpy()
        _date = blockToDate["date"].to_numpy()

        blockLookup[chainId] = {"blocks": _block, "dates": _date}


    def determineDate(x):
        chainId = x["chainId"]

        bl = blockLookup[chainId]

        _idx = np.searchsorted(bl["blocks"], x["blockNumber"], side="right")
        _date = bl["dates"][_idx]

        return _date

    # Load data from each and transform to a common format
    cbridge = (
        pd.read_parquet("raw/cbridge_transfers.parquet")
        .rename(
            columns={
                "block": "blockNumber",
                "receiver": "traveler",
                "destinationChainId": "chainId"
            }
        )
        .loc[:, ["chainId", "blockNumber", "tx", "traveler", "symbol", "amount"]]
    )
    cbridge["date"] = cbridge.apply(determineDate, axis=1)

    hop = (
        pd.read_parquet("raw/hop_transfers.parquet")
        .rename(
            columns={
                "originChainId": "chainId",
                "recipient": "traveler",
            }
        )
        .loc[:, ["chainId", "blockNumber", "tx", "traveler", "symbol", "amount", "timestamp"]]
    )
    hop["date"] = hop["timestamp"].map(
        lambda x: dt.datetime.utcfromtimestamp(x).replace(
            hour=0,
            minute=0,
            second=0,
        )
    )
    hop = hop.drop(["timestamp"], axis="columns")

    stg = (
        pd.read_parquet("raw/stg_transfers.parquet")
        .rename(
            columns={
                "block": "blockNumber",
                "destinationChainId": "chainId",
                "to": "traveler"
            }
        )
        .loc[:, ["chainId", "blockNumber", "tx", "traveler", "symbol", "amount"]]
    )
    stg["date"] = stg.apply(determineDate, axis=1)

    syn = (
        pd.read_parquet("raw/synapse_transfers.parquet")
        .rename(
            columns={
                "block": "blockNumber",
                "recipient": "traveler",
            }
        )
        .loc[:, ["chainId", "blockNumber", "tx", "traveler", "symbol", "amount"]]
    )
    syn["date"] = syn.apply(determineDate, axis=1)

    # Stack normalized data together
    df = pd.concat([cbridge, hop, stg, syn], axis=0, ignore_index=True)

    # Make sure all addresses are checksum
    df["traveler"] = df["traveler"].map(web3.Web3.toChecksumAddress)

    # Convert less common symbols to more common counterparts
    df["symbol"] = df["symbol"].replace(
        {
            "SGETH": "WETH",
            "nETH": "WETH",
            "nUSD": "UDSC"
        }
    )

    df.sort_values("date").to_parquet("intermediate/travelerTransfers.parquet")
