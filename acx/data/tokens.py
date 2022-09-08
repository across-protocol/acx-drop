import json
import pkgutil

from acx.utils import createNewSubsetDict

# Load the token list
TOKENLIST = json.loads(
    pkgutil.get_data("acx.data", "tokens.json")
)

# Make sure the keys are integers... JSON forces it to be a string
# when stored
for el in TOKENLIST:
    el["address"] = {
        int(k): v for k, v in el["address"].items()
    }

#
# Use the token list to generate helpful mappings
#
SYMBOL_TO_CGID = createNewSubsetDict("symbol", "cgId", TOKENLIST)
SYMBOL_TO_DECIMALS = createNewSubsetDict("symbol", "decimals", TOKENLIST)
SYMBOL_TO_CHAIN_TO_ADDRESS = createNewSubsetDict("symbol", "address", TOKENLIST)
CHAIN_TO_ADDRESS_TO_SYMBOL = {}
for el in TOKENLIST:
    _symbol = el["symbol"]
    _chain_to_address = el["address"]

    for (_chain, _address) in _chain_to_address.items():
        subdict = CHAIN_TO_ADDRESS_TO_SYMBOL.get(_chain, dict())
        subdict.update({_address: _symbol})

        CHAIN_TO_ADDRESS_TO_SYMBOL[_chain] = subdict

