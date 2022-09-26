import json

import pandas as pd
import web3

from pyaml_env import parse_config

from acx.abis import getABI
from acx.data.tokens import SYMBOL_TO_CHAIN_TO_ADDRESS
from acx.utils import scaleDecimals


if __name__ == "__main__":
    # Load parameters
    params = parse_config("parameters.yaml")

    # Connect to RPC node
    provider = web3.Web3.HTTPProvider(
        params["rpc_node"]["mainnet"],
        request_kwargs={"timeout": 60}
    )
    w3 = web3.Web3(provider)

    # Load block data
    BLOCKSTODATE = (
        pd.read_json("raw/blocks.json", orient="records")
        .query("chainId == 1")
        .sort_values("block")
        .loc[:, ["block", "date"]]
    )

    # Create the hub once up front
    hubInfo = params["across"]["v2"]["mainnet"]["hub"]
    hub = w3.eth.contract(address=hubInfo["address"], abi=getABI("HubPool"))

    # Block bounds -- v1 start block will depend on the pool so it
    # will be retrieved in the loop
    v2EndBlock = params["lp"]["v2_end_block"]
    v1EndBlock = params["lp"]["v1_end_block"]

    # -------------------------------------
    # Compute exchange rates
    # -------------------------------------
    v1ExchangeRates = []
    v2ExchangeRates = []
    for token in params["lp"]["tokens"]:
        # Create the v1 pool
        bridgeInfo = params["across"]["v1"]["mainnet"]["bridge"][token]
        poolAddress = bridgeInfo["address"]
        pool = w3.eth.contract(address=poolAddress, abi=getABI("BridgePool"))

        # Get the v1 first block
        v1FirstBlock = bridgeInfo["first_block"]

        # Iterate through each date to get exchange rates
        tokenErs = []
        for row in BLOCKSTODATE.itertuples():
            _date, _block = row.date, row.block
            print(f"{token} exchange rate for {_date}")

            # V1 exchange rate
            if (_block < v1FirstBlock) | (_block > v1EndBlock):
                v1Er = 0.0
            else:
                v1Er = scaleDecimals(
                    pool.functions.exchangeRateCurrent().call(block_identifier=_block), 18
                )

            v1Row = {
                "date": _date.strftime("%Y-%m-%d"),
                "block": _block,
                "symbol": token,
                "exchangeRate": v1Er
            }
            v1ExchangeRates.append(v1Row)

            # V2 exchange rate
            v2FirstBlock = params["lp"]["v2_lp_token_creation_block"][token]
            if (_block < v2FirstBlock) or (_block > v2EndBlock):
                v2Er = 0.0
            else:
                v2Er = scaleDecimals(
                    hub.functions.exchangeRateCurrent(
                        SYMBOL_TO_CHAIN_TO_ADDRESS[token][1]
                    ).call(block_identifier=_block), 18
                )

            v2Row = {
                "date": _date.strftime("%Y-%m-%d"),
                "block": _block,
                "symbol": token,
                "exchangeRate": v2Er
            }
            v2ExchangeRates.append(v2Row)

    with open("raw/v1ExchangeRates.json", "w") as f:
        json.dump(v1ExchangeRates, f)

    with open(f"raw/v2ExchangeRates.json", "w") as f:
        json.dump(v2ExchangeRates, f)

