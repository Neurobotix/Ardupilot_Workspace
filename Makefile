PYTHON ?= $(shell if [ -x ./env/bin/python3 ]; then echo ./env/bin/python3; elif [ -x /home/ahmed/ardupilot_workspace/env/bin/python3 ]; then echo /home/ahmed/ardupilot_workspace/env/bin/python3; else echo python3; fi)

.PHONY: doctor launch-help test-parity inventory

doctor:
	./scripts/ops/doctor.sh

launch-help:
	./scripts/ops/launch.sh help

test-parity:
	PYTHONPATH=src/sim_ard_gaw/compat_scripts $(PYTHON) -m unittest tests/parity/test_phase1_parity.py

inventory:
	@wc -l governance/audits/migration_inventory.csv
