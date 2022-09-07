# Across Airdrop Qualifications

This repository contains code used to generate the lists used for the Across airdrop.

In order to run this code in its entirety, you will need access to a rpc node for mainnet,
optimism, polygon, boba, and arbitrum. The LP portion only requires access to a rpc node
for mainnet. However, for convenience (and to allow others to double check our work!), we have
saved a list of the relevant event occurrences in the `raw` folder.

The script will require the following variables to be defined in the `parameters.yaml` file:

* `rpc_node.mainnet`:
* `rpc_node.optimism`:
* `rpc_node.polygon`:
* `rpc_node.boba`:
* `rpc_node.arbitrum`:

For example, if your Infura project identifier were `iL0veACXt0k3nsTHAnky0u` then you might use the following settings:

```
rpc_node:
  mainnet: "https://mainnet.infura.io/v3/iL0veACXtok3nsThAnkY0u"
  optimism: "https://optimism-mainnet.infura.io/v3/iL0veACXtok3nsThAnkY0u"
  polygon: "https://polygon-mainnet.infura.io/v3/iL0veACXtok3nsThAnkY0u"
  boba: "https://lightning-replica.boba.network"
  arbitrum: "https://arbitrum-mainnet.infura.io/v3/iL0veACXtok3nsThAnkY0u"
```

as the rpc settings in your `parameters.yaml` file


## Bridgoors

15,000,000 ACX tokens will be distributed to individuals who have bridged using Across from
November 8, 2021 (v1 launch) to July 18, 2022.

In order to filter out noise, we have chosen to exclude transfers that fall below


## Liquidity Providers

65,000,000 ACX tokens will be distributed to liquidity providers who provided DAI, ETH/WETH, USDC,
or WBTC to our liquidity pools. These distributions are pro-rated by (by USD equivalent size) and a
fixed number of tokens will be emitted at each block since the inception of the protocol.

(TODO: Describe what qualifies a liquidity provider for the airdrop)

Liquidity providers
