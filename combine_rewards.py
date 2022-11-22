import json

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
out["total"] = out.sum(axis=1)
out.index.name = "address"

out.to_json("final/final_combined.json", orient="index")
out.to_csv("final/final_combined.csv")

# Format for mr
mrout = {}
zeros = "0"*18

mrout["recipients"] = []
for (address, row) in out.iterrows():
    entry = {
        "account": address,
        "amount": str(int(row["total"] * 1e18)),
        "metadata": {
            "amountBreakdown": {
                "communityRewards":  str(int(row["community"] * 1e18)),
                "welcomeTravelerRewards": str(int(row["bridge-traveler"] * 1e18)),
                "earlyUserRewards": str(int(row["bridgoor"] * 1e18)),
                "liquidityProviderRewards": str(int(row["lp"] * 1e18))
            }
        }
    }
    mrout["recipients"].append(entry)

# Metadata
mrout["chainId"] = 1
mrout["rewardToken"] = ""
mrout["windowIndex"] = 0
mrout["rewardsToDeposit"] = str(int(out["total"].sum() * 1e18))

with open("final/mr.json", "w") as f:
    json.dump(mrout, f)
