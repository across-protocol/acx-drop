import json

import pandas as pd
import web3

from pyaml_env import parse_config


if __name__ == "__main__":
    # Load parameters
    params = parse_config("parameters.yaml")

    # Reward parameters
    rewardLb = params["traveler"]["parameters"]["rewards"]["tokens_lb"]
    rewardUb = params["traveler"]["parameters"]["rewards"]["tokens_ub"]
    bonusThreshold = params["traveler"]["parameters"]["rewards"]["bonus_threshold"]
    clipThreshold = params["traveler"]["parameters"]["rewards"]["clip_threshold"]

    # Traveler blocks
    travelStartBlock = params["traveler"]["travel_start_block"]
    travelEndBlock = params["traveler"]["travel_end_block"]

    # Qualified travelers
    travelerRewards = pd.DataFrame(
        pd.read_json("final/traveler_score.json", typ="series"),
        columns=["bridge-traveler"]
    )
    travelers = travelerRewards.index

    # Read across transactions
    across = pd.read_json(
        "intermediate/allAcrossTransactions.json",
        orient="records"
    )

    # Filter only transfers that can qualify for BT
    def filterTravelerTransfers(x):
        chainId = x["originChain"]

        travelerBlocks = (
            (x["block"] >= travelStartBlock[chainId]) &
            (x["block"] <= travelEndBlock[chainId])
        )
        travelerQuantity = (
            (x["symbol"] == "WETH") & (x["amount"] > 0.099) |
            (x["symbol"] == "USDC") & (x["amount"] > 149.99)
        )
        isTraveler = x["sender"] in travelers

        return travelerBlocks & travelerQuantity & isTraveler
    travelerRelevant = across.apply(filterTravelerTransfers, axis=1)
    travelerTransfers = across.loc[travelerRelevant, :]
    completedTravelers = travelerTransfers["sender"].unique()
    bridgeTravelers = travelerRewards.loc[completedTravelers]

    # Determine how many rewards will be distributed
    conversionRate = bridgeTravelers.size / travelers.size
    totalBtReward = (
        rewardLb +
        (conversionRate > bonusThreshold)*(rewardUb - rewardLb)
    )

    # Rescale everyone's share based on participation
    bridgeTravelers = bridgeTravelers / bridgeTravelers.sum()
    bridgeTravelers["airdrop"] = (
        (bridgeTravelers * totalBtReward).clip(0.0, clipThreshold)
    )

    bridgeTravelers["airdrop"].to_json("final/traveler_rewards.json")
