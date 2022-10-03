import datetime as dt
import pandas as pd

from pyaml_env import parse_config

from acx.data.tokens import SYMBOL_TO_CGID
from acx.utils import getWithRetries


CG_BASE_URL = "https://api.coingecko.com/api/v3"


def getCoinPriceHistory(_id, startDate, endDate):
    """
    Retrieve historical data
    """

    # Build request url
    req_url = f"{CG_BASE_URL}/coins/{_id}/market_chart/range"

    # Parameters
    params = {
        "vs_currency": "usd",
        "from": startDate.timestamp(),
        "to": endDate.timestamp()
    }
    res = getWithRetries(req_url, params=params)

    return res.json()["prices"]


if __name__ == "__main__":
    # Load parameters
    params = parse_config("parameters.yaml")

    # Tokens that we want data for
    tokens = params["misc"]["price"]["tokens"]

    startDate = dt.datetime.utcfromtimestamp(params["misc"]["price"]["start_ts"])
    endDate = dt.datetime.utcfromtimestamp(params["misc"]["price"]["end_ts"])

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
