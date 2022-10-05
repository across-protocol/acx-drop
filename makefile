##
# ACX Airdrop
#
# @file
# @version 0.1

BLOCKS_FROM_SCRATCH=true
EXCHANGERATES_FROM_SCRATCH=true
PRICES_FROM_SCRATCH=true

BRIDGOOR_FROM_SCRATCH=true
LP_FROM_SCRATCH=true
TRAVELER_FROM_SCRATCH=true

all: blocks exchangerates prices bridgoor lp traveler
	python combine_rewards.py

clean:
	rm -rf raw
	mkdir raw
	rm -rf intermediate
	mkdir intermediate
	rm -rf final
	mkdir final

blocks:

ifeq ($(BLOCKS_FROM_SCRATCH),true)
	@echo "Recompiling block-date data"
	python blocks.py
endif

exchangerates:

ifeq ($(EXCHANGERATES_FROM_SCRATCH),true)
	@echo "Recompiling block-date data"
	python lp_exchange_rates.py
endif

prices:

ifeq ($(PRICES_FROM_SCRATCH),true)
	@echo "Recompiling price data"
	python prices.py
endif

# Bridgoor rewards
bridgoor: blocks prices
	@echo "Compiling bridgoor data"

ifeq ($(BRIDGOOR_FROM_SCRATCH),true)
	@echo "Recompiling all bridgoor events"
	python bridgoor_events.py
endif

	python bridgoor_normalize.py
	python bridgoor_rewards.py

# LP rewards
lp: blocks prices exchangerates

ifeq ($(LP_FROM_SCRATCH),true)
	@echo "Recompiling all lp events"
	python lp_events.py
endif

ifeq ($(EXCHANGERATES_FROM_SCRATCH),true)
	@echo "Recompiling all lp events"
	python lp_exchange_rates.py
endif

	python lp_cumulative.py
	python lp_rewards.py

# Bridge traveler rewards
traveler: blocks prices bridgoor lp

ifeq ($(TRAVELER_FROM_SCRATCH),true)
	@echo "Recompiling all bridgoor events"
	python wt_cbridge.py
	python wt_hop.py
	python wt_stargate.py
	python wt_synapse.py
endif

	python wt_combine.py
	python wt_rewards.py

# end
