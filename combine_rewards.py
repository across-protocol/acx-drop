import pandas as pd


bridgoor = pd.DataFrame(
    pd.read_json("final/bridgoor_rewards.json", typ="series"),
    columns=["bridgoor"]
)

lp = pd.DataFrame(
    pd.read_json("final/lp_rewards.json", typ="series"),
    columns=["lp"]
)

travelers = pd.DataFrame(
    pd.read_json("final/traveler_rewards.json", typ="series"),
    columns=["traveler"]
)

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
