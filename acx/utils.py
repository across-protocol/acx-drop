import json
import requests

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import web3


def findEvents(w3, event, startBlock, endBlock, blockStep, argFilters, v=False):
    """
    Find all instances of a particular event between `startBlock` and
    `endBlock`

    Parameters
    ----------
    w3 : web3.Web3
        A web3 object
    event : web3.Contract.Event
        A particular event from a contract (i.e. contract.event.EVENT)
    startBlock : int
        The block to start searching on
    endBlock : int
        The block to stop searching on
    blockStep : int
        The number of blocks to download at a time -- This could be
        "infinite" if the RPC provider could deliver sufficient
        information per request, but, in practice, there are heavy
        constraints (for example, on Infura one can only retrieve 10,000
        events at a time on mainnet and 3,500 blocks at a time on
        Polygon
    argFilters : dict
        The filters to be applied on indexed arguments
    v : bool
        Verbose

    Returns
    -------
    events : list(dict)
        A list of dictionaries that contain the event information
    """
    # Make sure block arguments are meaningful... i.e. >0 and an integer
    assert(isinstance(startBlock, int) and startBlock >= 0)
    assert(isinstance(endBlock, int) and endBlock > 0)
    assert(isinstance(blockStep, int) and blockStep > 0)
    assert(startBlock < endBlock)

    events = []
    blockStarts = range(startBlock, endBlock, blockStep)
    for bs in blockStarts:
        be = min(bs + blockStep - 1, endBlock)

        if v:
            print(
                f"Beginning block {bs}\n"
                f"Ending block {be}"
            )

        eventOccurrences = event.getLogs(
            fromBlock=bs, toBlock=be, argument_filters=argFilters
        )
        nOccurrences = len(eventOccurrences)

        if v:
            print(f"Blocks {bs} to {be} contained {nOccurrences} transactions")

        if nOccurrences > 0:
            # Convert everything to JSON readable
            eventOccurrences = [
                json.loads(w3.toJSON(x)) for x in eventOccurrences
            ]

            events.extend(eventOccurrences)

    return events


def createNewSubsetDict(newKey, newValue, d):
    return {x[newKey]: x[newValue] for x in d}


def getWithRetries(url, params, nRetries=5, backoffFactor=1.0):
    # Create requests session
    session = requests.Session()

    # Retry adapter
    retry_strategy = Retry(
        total=nRetries,
        backoff_factor=backoffFactor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    res = session.get(url, params=params)

    return res
