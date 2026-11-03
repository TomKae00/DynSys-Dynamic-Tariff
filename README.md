# Dynamic heat tariffs and PTES operation

Hourly optimisation of representative Copenhagen heat dispatch and dynamic
PTES-discharge tariffs at the VEKS–Høje Taastrup boundary. The model uses fixed
plant capacities, public regional data and explicitly documented scenario assumptions.

| Location | Contents |
|---|---|
| [model/](model/README.md) | Hourly dispatch optimisation, data pipeline, scenarios and tests |
| [Model formulation](model/docs/formulation.md) | Constraints, objectives and settlement boundaries |
| [Data sources](model/docs/data_sources.md) | Public sources, inherited inputs and assumptions |
| [Validation](model/docs/validation.md) | Executed checks and remaining scientific limits |
| `model/config/` | Plant parameters and scenario settings |
| `model/tests/` | Physical, economic and data-alignment checks |

## Run the optimisation

```sh
cd model
python -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
pytest -q
cph-dispatch demo --hours 168 --prices
```

See [model/README.md](model/README.md) for public 2024 data preparation, annual
dispatch, local discharge-credit experiments and reproducibility instructions.
The default solver is HiGHS through SciPy; no commercial solver is required.

## Research status

The new model optimises a fixed Copenhagen producer portfolio, regional storage
and local HTF/PTES operation. It includes an explicit discharge-service settlement
and a rational local-response experiment. It does not yet complete the proposed
behavioural response, upstream corrective redispatch, deviation penalty and tariff
evaluation loop. Demand-metering boundaries, plant availability, cost assumptions,
waste treatment and local settlement/pumping allocation need empirical validation
before interpreting the scenarios as a historical reconstruction or final tariff.

Historical model code remains archived in `TomKae00/DynSys-PTES`; its pinned input
provenance is recorded in `model/data/legacy/`.
