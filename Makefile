# Finding Earth 2.0 -- reproducible pipeline entry points.
#
# Each target is idempotent and reads what the previous stage wrote, so any
# target can be re-run alone. `make all` runs the full pipeline end to end.

.PHONY: install data sync-gaia analyse figures deepdive validate-transit export report web web-build all test test-py test-web clean

install:
	python -m pip install -e ".[dev,products]"
	cd web && npm install

data:
	python -m earth2 sync

sync-gaia:
	python -m earth2 sync-gaia

analyse:
	python -m earth2 analyse

figures:
	python -m earth2 figures

deepdive:
	python -m earth2 deepdive -n 10 --transit --rv

validate-transit:
	python -m earth2 validate-transit

export:
	python -m earth2 export

report:
	python -m earth2 report

web:
	cd web && npm run dev

web-build:
	cd web && npm run build

all: data sync-gaia analyse figures deepdive validate-transit export report

test: test-py

test-py:
	python -m pytest tests/ -v

test-web:
	cd web && npm run typecheck && npm run build

clean:
	rm -rf web/.next web/out
	find . -name "__pycache__" -type d -prune -exec rm -rf {} \;
