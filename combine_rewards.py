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

out = (
    pd.DataFrame(travelers).join(
        [bridgoor, lp], how="outer"
    )
    .fillna(0.0)
)
out["total"] = out.sum(axis=1)
out.index.name = "address"

out.to_json("final/final_combined.json", orient="index")
out.to_csv("final/final_combined.csv")
