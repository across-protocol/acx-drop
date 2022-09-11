import datetime as dt
import requests
import time

import pandas as pd

from acx.data.tokens import SYMBOL_TO_CGID


CG_BASE_URL = "https://api.coingecko.com/api/v3/"


def getCoinPriceHistory(_id, startDate, endDate):
    """
    Retrieve historical data
    """
    # Build request url
    _ending = f"coins/{_id}/market_chart/range"
    req_url = CG_BASE_URL + _ending

    # Parameters
    params = {
        "vs_currency": "usd",
        "from": startDate.timestamp(),
        "to": endDate.timestamp()
    }

    time.sleep(1.5)
    res = requests.get(req_url, params=params)

    return res.json()["prices"]


if __name__ == "__main__":

    # Tokens that we want data for
    tokens = ["DAI", "ETH", "USDC", "WBTC", "WETH"]

    startDate = dt.datetime.utcfromtimestamp(1609459200)  # 2021-01-01T00:00
    endDate = dt.datetime.utcfromtimestamp(1662508800)  # 2022-09-08T00:00

    dfs = []
    for token in tokens:
        # Get the Coingecko id
        cgid = SYMBOL_TO_CGID[token]

        prices = pd.DataFrame(
            getCoinPriceHistory(cgid, startDate, endDate),
            columns=["dt", "price"]
        )
        prices["date"] = (
            prices["dt"]
            .map(lambda x: dt.datetime.utcfromtimestamp(x/1000))
            .dt.date
        )
        prices["symbol"] = token

        dfs.append(prices.loc[:, ["date", "symbol", "price"]])

    priceDf = pd.concat(dfs, axis=0)
    priceDf.to_json("raw/prices.json", orient="records")
