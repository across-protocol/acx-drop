import datetime as dt

import pandas as pd

from pyaml_env import parse_config

from acx.data.chains import SHORTNAME_TO_ID
from acx.data.tokens import SYMBOL_TO_DECIMALS
from acx.thegraph import submit_query_iterate


def retrieveTransfers(
        network, startBlock, endBlock,
        destinationChainIds, tokens,
        npages=10, verbose=False
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
    destinatinChainIds : list(int)
        A list of destination chain IDs that we want data from
    tokens : list(str)
        A list of tokens that we want to retrieve
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
            "destinationChainId_in": destinationChainIds,
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

    # First and last block data
    HOP_FIRST_BLOCK = params["traveler"]["hop"]["first_block"]
    HOP_LAST_BLOCK = params["traveler"]["hop"]["last_block"]

    # Chains we collect data from
    HOP_ORIGIN_CHAINS = params["traveler"]["hop"]["chains"]
    SUPPORTED_TOKENS = params["traveler"]["hop"]["tokens"]

    # Chains that we want transfers to
    SUPPORTED_CHAINS = params["traveler"]["chains"]
    SUPPORTED_CHAIN_IDS = [SHORTNAME_TO_ID[c] for c in SUPPORTED_CHAINS]

    # Retrieve mainnet transfers separately since they're special
    allDfs = []
    for chain in HOP_ORIGIN_CHAINS:
        chainId = SHORTNAME_TO_ID[chain]
        fb = HOP_FIRST_BLOCK[chainId]
        tb = HOP_LAST_BLOCK[chainId]

        # The Graph allows for retrieving 1,000 events at a time so we
        # set the number of pages to 999 as a magic number because we
        # know that no chain has more than 999,000 transfers
        transfers = retrieveTransfers(
            "xdai" if chainId == 100 else chain, fb, tb,
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

    hop.to_parquet("raw/hop_transfers.parquet")
