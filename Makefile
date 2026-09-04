.PHONY: test recover diagnose compare crosscheck all

test:
	uv run --with pytest python -m pytest tests/ -q

recover:
	python3 scripts/recover_tables.py

diagnose:
	python3 scripts/daghi_diagnosis.py

compare:          ## requires R with metafor; skips cleanly without it
	python3 scripts/compare_conv2x2.py

crosscheck:       ## our kappa against every R implementation on this machine
	python3 scripts/cross_check_kappa.py

all: test recover diagnose compare crosscheck
