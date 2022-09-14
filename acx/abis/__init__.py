import json
import pkgutil


# Mapping of ABI names to filenames
ABIs = {
    "BridgePool": "v1BridgePool.json",
    "HubPool": "v2HubPool.json",
    "SpokePool": "v2SpokePool.json",
    "ERC20": "ERC20.json"
}


def getABI(x: str):
    """
    Retrieve an ABI from the acx.abis folder using its contract name

    Available ABIs are:

    * "ERC20"
    * "BridgePool"
    * "HubPool"
    """
    if x in ABIs.keys():
        filename = ABIs[x]
    else:
        raise ValueError("Only certain ABIs available. Rtfd")

    return json.loads(pkgutil.get_data("acx.abis", filename))
