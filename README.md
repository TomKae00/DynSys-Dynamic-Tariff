# Dynamic heat tariffs and PTES operation

Research on dynamic PTES-discharge tariffs at the VEKS–Høje Taastrup boundary.
This repository contains the working manuscript and a representative Copenhagen
heat-dispatch optimisation. Numerical model validation and manuscript typesetting
are separate checks; the current paper results have not been replaced with new
portfolio-model results.

| Location | Contents |
|---|---|
| `main.tex`, `sections/`, `figures/` | Working paper, equations and scientific figures |
| `References.bib`, `preamble.tex` | Bibliography and paper formatting |
| [model/](model/README.md) | Hourly dispatch optimisation, data pipeline, scenarios and tests |
| [Model formulation](model/docs/formulation.md) | Constraints, objectives and settlement boundaries |
| [Data sources](model/docs/data_sources.md) | Public sources, inherited inputs and assumptions |
| [Validation](model/docs/validation.md) | Executed checks and remaining scientific limits |
| [Layout record](docs/manuscript_layout.md) | Earlier manuscript-formatting changes and references |

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

## Compile the paper

Use pdfLaTeX and BibTeX in Overleaf. With TeX Live and `elsarticle` installed:

```sh
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

The default is Elsevier's two-column `5p` layout. Change the class options to
`[preprint,12pt]` for a single-column review version. TikZ figures do not require
shell escape. Formatting does not imply acceptance or submission to a journal.

## Research status

The new model optimises a fixed Copenhagen producer portfolio, regional storage
and local HTF/PTES operation. It includes an explicit discharge-service settlement
and a rational local-response experiment. It does not yet complete the proposed
behavioural response, upstream corrective redispatch, deviation penalty and tariff
evaluation loop. Demand-metering boundaries, plant availability, cost assumptions,
waste treatment and local settlement/pumping allocation need empirical validation
before interpreting the scenarios as a historical reconstruction or final tariff.

The existing manuscript's scope, equations and results must be reconciled with the
validated extension before submission. Historical model code remains archived in
`TomKae00/DynSys-PTES`; its pinned input provenance is recorded in `model/data/legacy/`.
