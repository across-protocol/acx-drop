import json

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
    events = []
    blockStarts = range(startBlock, endBlock, blockStep)

    for bs in blockStarts:
        be = min(bs + blockStep - 1, endBlock)

        if v:
            print(f"Beginning block {bs}")
            print(f"Ending block {be}")

        event_occurrences = []
        event_occurrences = event.getLogs(
            fromBlock=bs, toBlock=be, argument_filters=argFilters
        )
        if v:
            print(f"Blocks {bs} to {be} contained {len(event_occurrences)} transactions")

        # Convert everything to JSON readable
        event_occurrences = [
            json.loads(w3.toJSON(x)) for x in event_occurrences
        ]
        events.extend(event_occurrences)

    return events


def createNewSubsetDict(newKey, newValue, d):
    return {x[newKey]: x[newValue] for x in d}

