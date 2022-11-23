import decimal
import json

from decimal import Decimal

import pandas as pd


bridgoor = pd.DataFrame(
    pd.read_json("final/bridgoor_rewards.json", typ="series"),
    columns=["bridgoor"]
)
if bridgoor["bridgoor"].isna().any():
    raise ValueError("Missing values in bridgoor data")

lp = pd.DataFrame(
    pd.read_json("final/lp_rewards.json", typ="series"),
    columns=["lp"]
)
if lp["lp"].isna().any():
    raise ValueError("Missing values in lp data")

travelers = pd.DataFrame(
    pd.read_json("final/traveler_rewards.json", typ="series"),
    columns=["bridge-traveler"]
)
if travelers["bridge-traveler"].isna().any():
    raise ValueError("Missing values in traveler data")

community = pd.DataFrame(
    pd.read_json("final/community_rewards.json", typ="series"),
    columns=["community"]
)

out = (
    pd.DataFrame(travelers).join(
        [bridgoor, community, lp], how="outer"
    )
    .fillna(0.0)
)
out.index.name = "address"

# Convert everything to decimal types for more accurate/consistent computations
out = out.applymap(lambda x: Decimal(x))

# Format for mr
mrout = {}
mrout["recipients"] = []

# Metadata
mrout["chainId"] = 1
mrout["rewardToken"] = ""
mrout["windowIndex"] = 0


# Constant 1e18 for convenience
zeros = Decimal(1e18)
runningSum = Decimal(0)

# Iterate through rows and compute total and save to merkle tree object
def removeDecimals(x):
    return x.quantize(Decimal("0"))

for (address, row) in out.iterrows():

    # Add by hand because `.sum` converted to float
    totalDecimal = row["bridge-traveler"] + row["bridgoor"] + row["community"] + row["lp"]
    runningSum += totalDecimal*zeros
    out.at[address, "total"] = totalDecimal

    entry = {
        "account": address,
        "amount": str(removeDecimals(totalDecimal*zeros)),
        "metadata": {
            "amountBreakdown": {
                "communityRewards":  str(removeDecimals(row["community"] * zeros)),
                "welcomeTravelerRewards": str(removeDecimals(row["bridge-traveler"] * zeros)),
                "earlyUserRewards": str(removeDecimals(row["bridgoor"] * zeros)),
                "liquidityProviderRewards": str(removeDecimals(row["lp"] * zeros))
            }
        }
    }
    mrout["recipients"].append(entry)

mrout["rewardsToDeposit"] = str(removeDecimals(runningSum))

out.to_json("final/final_combined.json", orient="index")
out.to_csv("final/final_combined.csv")

with open("final/mr.json", "w") as f:
    json.dump(mrout, f)
