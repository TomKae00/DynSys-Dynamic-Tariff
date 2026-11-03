# Representative Copenhagen dispatch optimisation

This is an hourly operational **optimisation**, with fixed plant capacities and
endogenous CHP output, heat pumps, boilers and storage. It replaces the previous
single CHP heat-cost proxy with a small Copenhagen supply portfolio. It is a
transparent research scenario, not a replica of Varmelast's confidential model.

The manuscript and this extension currently describe different model versions.
Existing manuscript results have not been overwritten or presented as results of
this model. See [the formulation](docs/formulation.md), [input provenance](docs/data_sources.md)
and [validation record](docs/validation.md) before interpreting numerical output.

## Run

From this directory, with Python 3.12:

```sh
python -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
pytest -q
cph-dispatch demo --hours 168 --prices --output results/demo
```

The demo is synthetic and works offline. It is never used as a fallback for a
failed public-data download. Tested direct dependency versions are recorded in
`requirements-tested.txt`; install those first to reproduce the tested environment.

Prepare public inputs and run the real-data scenario:

```sh
cph-dispatch prepare --year 2024
# The strict command rejects gaps. To apply the documented repair policy:
cph-dispatch prepare --year 2024 --repair
cph-dispatch solve --start 2024-01-08T00:00Z --hours 168 --prices --output results/winter
cph-dispatch solve --start 2024-07-15T00:00Z --hours 168 --prices --output results/summer
cph-dispatch solve --prices --output results/annual
```

Each solve writes `dispatch.csv` and `summary.json`, including the complete scenario,
solver status, gap/bound, independent feasibility checks, input hashes and versions.
No accepted solution means a nonzero exit and no new result export. Use a distinct
output directory for each scenario; old files in an existing directory are not deleted.
`--relax` explicitly requests a diagnostic LP relaxation and labels the result.
The default MILP has integer PTES and local heat-pump operating modes; upstream
CHPs and regional accumulators remain continuous approximations.
`--hp-policy must_run` selects the stakeholder operating-policy sensitivity;
`--time-limit` and `--mip-gap` override solver settings. Solver time limits are
not strict process wall limits. The full-year endogenous-HP MILP did not complete
within the validation budget; see the validation record before planning annual runs.
For your licensed research environment, the same matrix also supports Gurobi:

```sh
pip install -e '.[gurobi]'
cph-dispatch solve --solver gurobi --time-limit 1800 --prices --output results/annual_gurobi
```

This requires a licence covering the full model size. Only a small Gurobi/HiGHS
equivalence case was tested here; no full-year Gurobi result is claimed.

## Discharge tariff experiment

First solve the coordinated system. Then hold its charging schedule fixed and
optimise local HTF operation under an announced discharge credit:

```sh
cph-dispatch solve --hours 168 --output results/central
cph-dispatch solve --hours 168 --objective local --schedule results/central/dispatch.csv \
  --discount 0 --output results/local_reference
cph-dispatch solve --hours 168 --objective local --schedule results/central/dispatch.csv \
  --discount 50 --output results/local_credit50
```

The values 0 and 50 are **illustrative experiment parameters**, not estimated
tariffs. Direct heat retains the monthly reference price; discharge pays that price
less the credit. Charging heat belongs to the upstream settlement boundary.
An hourly `discharge_discount_dkk_mwh` column in a supplied `--inputs` file overrides
the constant credit. Reference and alternative runs must use identical inputs,
horizons, inventory endpoints and charging schedules.

This local optimisation is a rational response benchmark, not a behavioural model.
It does not yet redispatch the upstream system after local deviations, calculate
an imbalance penalty, or derive a final tariff. A local bill reduction alone is
not evidence of a system cost saving. The separately named `legacy_owned_store`
settlement option reproduces the old charging-purchase experiment; it is not the
default paper boundary.

## Structure and migration

| Location | Purpose |
|---|---|
| `src/cph_dispatch/data.py` | Public data retrieval, UTC alignment and repair audit |
| `src/cph_dispatch/optimisation.py` | One sparse LP/MILP formulation and solver checks |
| `src/cph_dispatch/cli.py` | Common command line entry point |
| `config/base.yaml`, `config/plants.csv` | Scenario assumptions and plant parameters |
| `data/legacy/` | Small inherited research inputs and pinned provenance |
| `data/raw/`, `data/processed/`, `results/` | Generated, ignored files |
| `tests/` | Physical, economic and time-alignment regression checks |

The starting equations and small inputs come from `TomKae00/DynSys-PTES` at
`48e49c0b8dc6415611cf0ed6ce985ea3b2d1ef50`. No old notebooks, solver exports or
duplicated model scripts are copied. That repository remains the historical archive.
This extension formulates the equations directly as sparse matrices for SciPy/HiGHS,
rather than depending on PyPSA component internals or a Gurobi licence. Existing
PyPSA `.nc` results are not compatible or recomputed by this package.

Corrected inherited issues include free terminal inventory depletion, electrical
heat-pump ratings based on mean COP, timestamp overwriting and unrestricted gap
filling. The old 12-hour full-charge/full-discharge rule is still not implemented;
it requires a precise operational definition and is not claimed as covered.
