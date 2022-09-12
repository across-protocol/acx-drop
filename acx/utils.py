import json
import requests

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import web3

from typing import Any, Dict, Union

from eth_typing import HexStr
from hexbytes import HexBytes
from web3.datastructures import AttributeDict
from web3._utils.encoding import FriendlyJsonSerde


class Web3JsonEncoder(json.JSONEncoder):
    "Based on https://github.com/ethereum/web3.py/blob/master/web3/_utils/encoding.py#L286-L292"
    def default(self, obj: Any) -> Union[Dict[Any, Any], HexStr]:
        if isinstance(obj, AttributeDict):
            return {k: v for k, v in obj.items()}
        if isinstance(obj, HexBytes):
            return HexStr(obj.hex())
        # If any of the args are bytes, just convert them to hex... Pray
        # to the blockchain gods that this is what it's meant to be
        if isinstance(obj, bytes):
            return obj.hex()
        return json.JSONEncoder.default(self, obj)


def to_json(obj: Dict[Any, Any]) -> str:
    """
    Convert a complex object (like a transaction object) to a JSON string
    """
    return FriendlyJsonSerde().json_encode(obj, cls=Web3JsonEncoder)


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
                json.loads(to_json(x)) for x in eventOccurrences
            ]

            events.extend(eventOccurrences)

    return events


def scaleDecimals(x, decimals=18):
    return  x / 10**decimals


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
