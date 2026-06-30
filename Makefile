PYTHON ?= $(shell if [ -x ./env/bin/python3 ]; then echo ./env/bin/python3; elif [ -x /home/ahmed/ardupilot_workspace/env/bin/python3 ]; then echo /home/ahmed/ardupilot_workspace/env/bin/python3; else echo python3; fi)

.PHONY: doctor launch-help inventory

doctor:
	./scripts/ops/doctor.sh

launch-help:
	./scripts/ops/launch.sh help

inventory:
	@wc -l governance/audits/migration_inventory.csv
