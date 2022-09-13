import json

import pandas as pd
import yaml

from acx.abis import getABI
from acx.data.tokens import (
    CHAIN_TO_ADDRESS_TO_SYMBOL, SYMBOL_TO_CHAIN_TO_ADDRESS, SYMBOL_TO_DECIMALS
)
from acx.utils import scaleDecimals


def getV1DisputeHashes(v1DisputesRaw):
    disputeHashes = []
    for token in v1DisputesRaw.keys():
        disputes = v1DisputesRaw[token]

        disputeHashes.extend([x["args"]["depositHash"] for x in disputes])

    return disputeHashes


def unpackV1Relays(v1RelaysRaw, disputes):
    out = []
    for token in v1RelaysRaw.keys():
        # Get all relays of a certain token
        relays = v1RelaysRaw[token]

        # Get decimals
        decimals = SYMBOL_TO_DECIMALS[token]

        for relay in relays:
            # Unpack deposit/relay data
            depositData = relay["args"]["depositData"]
            relayData = relay["args"]["relay"]

            if relay["args"]["depositHash"] in disputes:
                continue

            row = {
                "originChain": depositData[0],
                "destinationChain": 1,
                "block": relay["blockNumber"],
                "tx": relay["transactionHash"],
                "sender": depositData[3],
                "recipient": depositData[2],
                "symbol": token,
                "amount": scaleDecimals(depositData[4], decimals),
                "version": 1
            }
            out.append(row)

    return pd.DataFrame(out)


def unpackV2Deposits(v2DepositsRaw):
    out = []
    for deposit in v2DepositsRaw:
        # Unpack pieces of useful data
        args = deposit["args"]

        originChainId = args["originChainId"]

        tokenAddress = args["originToken"]
        symbol = CHAIN_TO_ADDRESS_TO_SYMBOL[originChainId][tokenAddress]
        decimals = SYMBOL_TO_DECIMALS[symbol]

        row = {
            "originChain": originChainId,
            "destinationChain": args["destinationChainId"],
            "block": deposit["blockNumber"],
            "tx": deposit["transactionHash"],
            "sender": args["depositor"],
            "recipient": args["recipient"],
            "symbol": symbol,
            "amount": scaleDecimals(args["amount"], decimals),
            "version": 2
        }
        out.append(row)


    return pd.DataFrame(out)


if __name__ == "__main__":
    # Load parameters
    with open("parameters.yaml", "r") as f:
        params = yaml.load(f, yaml.Loader)

    # Load data
    with open("raw/v1DisputedRelays.json", "r") as f:
        v1DisputesRaw = json.loads(f.read())
    with open("raw/v1Relays.json", "r") as f:
        v1RelaysRaw = json.loads(f.read())
    with open("raw/v2Deposits.json", "r") as f:
        v2DepositsRaw = json.loads(f.read())

    # Put into DataFrames
    v1Disputes = getV1DisputeHashes(v1DisputesRaw)
    v1Relays = unpackV1Relays(v1RelaysRaw, v1Disputes)
    v2Deposits = unpackV2Deposits(v2DepositsRaw)

    # Restrict v1 to only relevant blocks
    v1StartBlock = params["bridgoor"]["v1_start_block"]
    v1EndBlock = params["bridgoor"]["v1_end_block"]
    v1Relays = v1Relays.query("(block >= @v1StartBlock) & (block <= @v1EndBlock)")

    # Restrict v2 to only relevant blocks
    v2StartBlock = params["bridgoor"]["v2_start_block"]
    v2EndBlock = params["bridgoor"]["v2_end_block"]
    def v2Filter(x):
        gtBlock = x["block"] >= v2StartBlock[x["originChain"]]
        ltBlock = x["block"] <= v2EndBlock[x["originChain"]]

        return gtBlock & ltBlock
    v2DepositsKeep = v2Deposits.apply(v2Filter, axis=1)
    v2Deposits = v2Deposits.loc[v2DepositsKeep, :]

    bridgoors = pd.concat([v1Relays, v2Deposits], axis=0, ignore_index=True)
    bridgoors.to_json("intermediate/allBridges.json", orient="records")
