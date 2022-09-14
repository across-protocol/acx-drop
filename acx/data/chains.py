import json
import pkgutil


# Load the chain list
CHAINLIST = json.loads(
    pkgutil.get_data("acx.data", "chains.json")
)


#
# Use the chainlist to generate helpful mappings
#
ID_TO_NAME = {
    x["chainId"]: x["chainName"] for x in CHAINLIST
}

ID_TO_SHORTNAME = {
    x["chainId"]: x["shortName"] for x in CHAINLIST
}

SHORTNAME_TO_ID = {
    x["shortName"]: x["chainId"] for x in CHAINLIST
}
