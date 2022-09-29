import pandas as pd
import web3

from pyaml_env import parse_config

from acx.abis import getABI
from acx.data.chains import SHORTNAME_TO_ID
from acx.data.tokens import CHAIN_TO_ADDRESS_TO_SYMBOL, SYMBOL_TO_DECIMALS
from acx.utils import findEvents, scaleDecimals


def retrieveSwapRemotes(w3, pool, startBlock, lastBlock, nBlocks):
    """
    Collect data about the `SwapRemote` events from the Stargate Pool
    contracts

    Parameters
    ----------
    w3 : web3.Web3
        A web3 object
    pool : web3.Contract
        A web3
    start_block : int
        The starting block to collect
    last_block : int
        The ending block (inclusive)

    Returns
    -------
    df : pd.DataFrame
        A DataFrame with all of the pool data for relevant time period
    """
    # Meta data about the pool
    chainId = w3.eth.chainId
    tokenAddress = pool.functions.token().call()
    symbol = CHAIN_TO_ADDRESS_TO_SYMBOL[chainId][tokenAddress]
    decimals = SYMBOL_TO_DECIMALS[symbol]

    # Collect swap data
    swaps = findEvents(
        w3, pool.events.SwapRemote, startBlock, lastBlock,
        nBlocks, {}, True
    )

    out = []
    for swap in swaps:
        swapArgs = swap["args"]

        # Save row by row
        row = {}

        row["block"] = swap["blockNumber"]
        row["tx"] = swap["transactionHash"]
        row["destinationChainId"] = chainId
        row["to"] = swapArgs["to"]
        row["symbol"] = symbol
        row["amount"] = scaleDecimals(swapArgs["amountSD"], decimals)

        out.append(row)

    return out


if __name__ == "__main__":
    # Load parameters
    params = parse_config("parameters.yaml")


    swapRemotes = []
    for chain in params["bt"]["stg"]["chains"][3:]:
        # Find chain ID
        chainId = SHORTNAME_TO_ID[chain]

        # Create a web3 instance
        provider = web3.Web3.HTTPProvider(
            params["rpc_node"][chain],
            request_kwargs={"timeout": 60}
        )
        w3 = web3.Web3(provider)
        nBlocks = params["bt"]["stg"]["n_blocks"][chainId]

        for token in params["bt"]["stg"]["tokens"]:
            # Check whether the pool exists -- If not, move on to the next
            if token not in params["bt"]["stg"]["contract_info"][chainId].keys():
                continue

            # Get pool address and first/last block from params
            poolAddress = params["bt"]["stg"]["contract_info"][chainId][token]["address"]
            fb = params["bt"]["stg"]["contract_info"][chainId][token]["first_block"]
            lb = params["bt"]["stg"]["contract_info"][chainId][token]["last_block"]

            # Create pool
            pool = w3.eth.contract(
                address=poolAddress, abi=getABI("StargatePool")
            )

            _swaps = retrieveSwapRemotes(w3, pool, fb, lb, nBlocks)
            swapRemotes.extend(_swaps)

    stg = pd.DataFrame(swapRemotes)
    stg.to_parquet("raw/stg_transfers.parquet")
