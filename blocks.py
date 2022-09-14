import datetime as dt
import json
import time

from pyaml_env import parse_config

from acx.data.chains import SHORTNAME_TO_ID
from acx.utils import getWithRetries


CHAIN_TO_URL = {
    # ETHERSCAN
    1: "https://api.etherscan.io/api",
    # OPTIMISTIC ETHERSCAN
    10: "https://api-optimistic.etherscan.io/api",
    # POLYGONSCAN
    137: "https://api.polygonscan.com/api",
    # BOBASCAN
    288: "https://api.bobascan.com/api",
    # ARBISCAN
    42161: "https://api.arbiscan.io/api"
}


def findMostRecentBlockAfterTs(ts: int, chainId: int=1, key=""):
    """
    Finds the most recent block that occurs after a particular UTC
    timestamp

    This requires that the `action=getblocknobytime` api command is
    defined

    Parameters
    ----------
    ts : int
        The timestamp that we want to find the block after
    chainId : int
        The identifier for the chain of interest
    """
    apiurl = CHAIN_TO_URL[chainId]

    params = {
        "module": "block",
        "action": "getblocknobytime",
        "closest": "after",
        "timestamp": ts,
        "apikey": key
    }
    res = getWithRetries(apiurl, params=params, backoffFactor=1.5, preSleep=0.5)

    if res.json()["status"] == "1":
        return int(res.json()["result"])
    else:
        print(res.json())
        raise ValueError("Failed to find block")


if __name__ == "__main__":
    # Load parameters
    params = parse_config("parameters.yaml")

    # Find relevant blocks for all chains
    blockData = []
    for chain in params["bridgoor"]["chains"]:
        print(f"Starting on chain: {chain}")

        # Get chain id and scan api key
        chainId = SHORTNAME_TO_ID[chain]
        someScanKey = params["etherscan_keys"][chain]


        # Get timestamps to start searching for
        if chain == "mainnet":
            blockStartTs = params["misc"]["block_start_ts_mainnet"]
        else:
            blockStartTs = params["misc"]["block_start_ts_nonmainnet"]
        blockEndTs = params["misc"]["block_end_ts"]

        # Get the block number for each day between (blockStartTs, blockEndTs)
        dateStarts = range(blockStartTs, blockEndTs, 24*60*60)
        for _ts in dateStarts:
            # Optimism - June 1, 2022
            if (_ts == 1654041600) and (chain == "optimism"):
                block = 9621060
            # Optimism June 2, 2022
            elif (_ts == 1654128000) and (chain == "optimism"):
                block = 10108895
            # Optimism - August 6, 2022
            elif (_ts == 1659744000) and (chain == "optimism"):
                block = 17974360
            # Boba - March 6, 2022
            elif (_ts == 1646524800) and (chain == "boba"):
                block = 382645
            else:
                block = findMostRecentBlockAfterTs(_ts, chainId, key=someScanKey)

            row = {
                "chain": chain,
                "chainId": chainId,
                "date": dt.datetime.utcfromtimestamp(_ts).strftime("%Y-%m-%dT00:00"),
                "block": block
            }
            blockData.append(row)
            print(row)

    with open("raw/blocks.json", "w") as f:
        json.dump(blockData, f)
