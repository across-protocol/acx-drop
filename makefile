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
	cp raw/sybil.json sybil.json
	rm -rf raw/
	mkdir raw
	mv sybil.json raw/sybil.json
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
	python bt_cbridge.py
	python bt_hop.py
	python bt_stargate.py
	python bt_synapse.py
endif

	python bt_combine.py
	python bt_rewards.py
	python bt_final.py

# end
