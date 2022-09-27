import datetime as dt

import pandas as pd

from pyaml_env import parse_config

from acx.data.chains import SHORTNAME_TO_ID
from acx.data.tokens import SYMBOL_TO_DECIMALS
from acx.thegraph import submit_query_iterate


def retrieveTransfers(
        network, startBlock, endBlock,
        chainIds, tokens, npages=10, verbose=False
):
    """
    Grabs all of the transfers from `network`

    Parameters
    ----------
    network : str
        A short name identifier for a network
    start_block : int
        The block to start collecting data from
    end_block : int
        The block to stop collecting data from
    npages : int
        The maximum number of pages to retrieve
    verbose : bool
        Whether to print information about which transfers are
        being retrieved
    """
    # Build query inputs
    if network == "mainnet":
        table = "transferSentToL2S"
    else:
        table = "transferSents"

    variables = [
        "id", "blockNumber", "transactionHash", "timestamp",
        "destinationChainId", "from", "recipient",
        "token", "amount",
    ]
    arguments = {
        "first": 1_000,
        "where": {
            "blockNumber_gt": startBlock,
            "blockNumber_lte": endBlock,
            "destinationChainId_in": chainIds,
            "token_in": "[\"" + "\", \"".join(tokens) + "\"]"
        },
    }

    # Determine which subgraph to query
    transfers = submit_query_iterate(
        table, variables, arguments,
        "hop-protocol", f"hop-{network}",
        npages=npages, verbose=verbose
    )

    return transfers


if __name__ == "__main__":
    # Load parameters
    params = parse_config("parameters.yaml")

    HOP_FIRST_BLOCK = params["bt"]["hop"]["first_block"]
    HOP_LAST_BLOCK = params["bt"]["hop"]["last_block"]
    SUPPORTED_CHAINS = params["bt"]["hop"]["chains"]
    SUPPORTED_CHAIN_IDS = [SHORTNAME_TO_ID[c] for c in SUPPORTED_CHAINS]
    SUPPORTED_TOKENS = params["bt"]["hop"]["tokens"]

    # Retrieve mainnet transfers separately since they're special
    allDfs = []
    for chain in SUPPORTED_CHAINS:
        chainId = SHORTNAME_TO_ID[chain]
        fb = HOP_FIRST_BLOCK[chainId]
        tb = HOP_LAST_BLOCK[chainId]

        transfers = retrieveTransfers(
            chain, fb, tb,
            SUPPORTED_CHAIN_IDS, SUPPORTED_TOKENS,
            npages=999, verbose=True
        )

        # Put data into a dataframe so we can transform certain pieces of it
        _df = pd.DataFrame(transfers)
        _df["originChainId"] = chainId

        # Convert things to integers
        int_cols = ["destinationChainId", "blockNumber", "timestamp"]
        for col in int_cols:
            _df.loc[:, col] = pd.to_numeric(_df.loc[:, col])

        # Convert dates to date
        _df["dt"] = _df.loc[:, "timestamp"].map(
            lambda x: dt.datetime.utcfromtimestamp(x)
        )

        _scaleDecimals = (
            10**_df["token"].map(lambda x: SYMBOL_TO_DECIMALS[x])
        )
        _df.loc[:, "amount"] = (
            _df.loc[:, "amount"].astype(float) / _scaleDecimals
        )
        allDfs.append(_df)

    hop = pd.concat(allDfs)

    # Rename columns
    hop = hop.rename(
        columns={
            "transactionHash": "tx",
            "token": "symbol",
            "from": "sender"
        }
    )

