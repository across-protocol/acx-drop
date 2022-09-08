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
    # Make sure block arguments are meaningful... i.e. >0 and an integer
    assert((startBlock >= 0) and isinstance(startBlock, int))
    assert((endBlock > 0) and isinstance(endBlock, int))
    assert((blockStep > 0) and isinstance(blockStep, int))
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
        nOcurrences = len(eventOcurrences)

        if v:
            print(f"Blocks {bs} to {be} contained {nOcurrences} transactions")

        if nOcurrences > 0:
            # Convert everything to JSON readable
            eventOccurrences = [
                json.loads(w3.toJSON(x)) for x in eventOccurrences
            ]

            events.extend(eventOccurrences)

    return events


def createNewSubsetDict(newKey, newValue, d):
    return {x[newKey]: x[newValue] for x in d}

