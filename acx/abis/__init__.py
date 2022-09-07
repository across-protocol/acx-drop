import json
import pkgutil


# General ABIs
ERC20_ABI = (
    json.loads(
        pkgutil.get_data("acx.abis", "ERC20.json")
    )
)

# Across specific ABIs
BRIDGEPOOL_ABI = (
    json.loads(
        pkgutil.get_data("acx.abis", "v1BridgePool.json")
    )
)

HUBPOOL_ABI = (
    json.loads(
        pkgutil.get_data("acx.abis", "v2HubPool.json")
    )
)
