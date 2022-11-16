import json

import pandas as pd
import web3

from pyaml_env import parse_config

from acx.abis import getABI
from acx.data.tokens import SYMBOL_TO_CHAIN_TO_ADDRESS
from acx.utils import findEvents


if __name__ == "__main__":
    # Load parameters
    params = parse_config("parameters.yaml")
    nBlocks = params["bridgoor"]["n_blocks"]

    #
    # V1 bridges
    #
    provider = web3.Web3.HTTPProvider(
        params["rpc_node"]["mainnet"],
        request_kwargs={"timeout": 60}
    )
    w3 = web3.Web3(provider)

    v1StartBlock = params["bridgoor"]["v1_start_block"]
    v1EndBlock = params["bridgoor"]["v1_end_block"]

    # Iterate through each of the relevant pools
    # All v1 transfers are L2->L1 so we can only look at relays on L1
    v1Disputes = {}
    v1Relays = {}
    for token in params["bridgoor"]["tokens"]:
        # Get information about specific BridgePool
        bridgeInfo = params["across"]["v1"]["mainnet"]["bridge"][token]
        poolAddress = bridgeInfo["address"]

        # Create BridgePool object
        pool = w3.eth.contract(address=poolAddress, abi=getABI("BridgePool"))

        # Collect dispute information so they can be excluded
        v1Disputes[token] = findEvents(
            w3, pool.events.RelayDisputed, v1StartBlock, v1EndBlock,
            nBlocks[w3.eth.chainId], {}, True
        )

        v1Relays[token] = findEvents(
            w3, pool.events.DepositRelayed, v1StartBlock, v1EndBlock,
            nBlocks[w3.eth.chainId], {}, True
        )

    with open("raw/v1DisputedRelays.json", "w") as f:
        json.dump(v1Disputes, f)
    with open("raw/v1Relays.json", "w") as f:
        json.dump(v1Relays, f)


    #
    # V2 bridges
    #
    v2Deposits = []
    for chain in params["bridgoor"]["chains"]:
        # No longer only L2->L1 so we need to retrieve data from each
        # chain
        provider = web3.Web3.HTTPProvider(
            params["rpc_node"][chain],
            request_kwargs={"timeout": 60}
        )
        w3 = web3.Web3(provider)
        chainId = w3.eth.chainId

        # Create that chain's spoke pool
        spokeInfo = params["across"]["v2"][chain]["spoke"]
        spokeAddress = spokeInfo["address"]
        spoke = w3.eth.contract(address=spokeAddress, abi=getABI("SpokePool"))

        # Get token addresses that qualify
        addresses = [
            SYMBOL_TO_CHAIN_TO_ADDRESS[token][chainId]
            for token in params["bridgoor"]["tokens"]
        ]

        # Get start block for qualifying
        v2StartBlock = params["bridgoor"]["v2_start_block"][chainId]

        # Collect data throughout end of BT (we'll need this for traveler)
        v2EndBlock = params["traveler"]["travel_end_block"][chainId]

        # Retrieve deposits
        deposits = findEvents(
            w3, spoke.events.FundsDeposited, v2StartBlock, v2EndBlock,
            nBlocks[w3.eth.chainId], {"originToken": addresses}, True
        )
        v2Deposits.extend(deposits)

    with open("raw/v2Deposits.json", "w") as f:
        json.dump(v2Deposits, f)
