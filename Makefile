.PHONY: test compare crosscheck build all

test:
	uv run --with pytest python -m pytest tests/ -q

compare:          ## against metafor::conv.2x2; needs R with metafor, skips without
	python3 scripts/compare_conv2x2.py

crosscheck:       ## this kappa against every R implementation installed
	python3 scripts/cross_check_kappa.py

build:
	uv build

all: test compare crosscheck
