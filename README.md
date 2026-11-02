# Dynamic heat tariffs and PTES operation

## Compile

Open `main.tex` in Overleaf and use **pdfLaTeX**. The bibliography now uses
**BibTeX**, not Biber. A normal Overleaf Recompile runs the required passes.
Locally, with TeX Live's `elsarticle` class installed:

```sh
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

The default is Elsevier's two-column `5p` article layout. To prepare a
single-column review version, change the class options to `[preprint,12pt]`.
There is no publisher logo, journal name, or claim of acceptance/submission.
TikZ figure bodies are included directly; shell escape is not needed.

## Layout references

- Schledorn et al. (2022), *Frigg: Soft-linking energy system and demand response
  models*, Applied Energy 317, 119074. https://doi.org/10.1016/j.apenergy.2022.119074
- Schledorn et al. (2024), *Frigg 2.0: Integrating price-based demand response into
  large-scale energy system analysis*, Applied Energy 364, 122960.
  https://doi.org/10.1016/j.apenergy.2024.122960
- Dominković et al. (2020), *Implementing flexibility into energy planning models:
  Soft-linking of a high-level energy planning model and a short-term operational
  model*, Applied Energy 260, 114292. https://doi.org/10.1016/j.apenergy.2019.114292
- Dominković et al. (2018), *Influence of different technologies on dynamic pricing
  in district heating systems: Comparative case studies*, Energy 153, 136–148
  (already cited in the manuscript).

These are presentation references: numbered section hierarchy, compact equations
with prose definitions, grouped constraints, nomenclature, and simple table rules.
No text or numerical findings from those papers have been copied.

## Formatting and notation changes

- Replace the report cover and contents with article front matter; retain authors.
- Move the existing abstract to `sections/00_Abstract.tex`.
- Add nomenclature and label each equation group and constituent constraint.
- Use upright descriptive subscripts/superscripts and a shared heat-pump index.
- Make the hourly duration explicit: powers are integrated using `Delta t = 1 h`;
  start-up charges are per event. This does not change the hourly numerical model.
- State valid initial/ramping/switching index domains: no references beyond the
  final period, and ramp differences start at the second operating period.
- Use one consistent biomass fossil-emission-factor symbol in equation and prose.
- Move the existing detailed COP calculation and assumptions to Appendix A.
- Relabel the existing optimization objective consistently as local operating
  expenditure in the results table and discussion.
- Keep the five-step future workflow; identify it as a proposed extension.
- Preserve loose discussion notes in the uncompiled `sections/00_notes.tex`.
- Remove a duplicate bibliography key and supply three previously missing entries.
- Simplify the workflow figure to straight borders and labelled arrows, and
  correct its producer label to match the single biomass CHP
  proxy currently described in the methodology (waste incineration is not yet
  modelled in this manuscript formulation).

## Scientific work still open

This is a formatted working manuscript, not a completed submission. The current
introduction focuses on a **PTES-discharge tariff**, while the existing operational
formulation still purchases external heat for direct supply and charging.
The discharge tariff, pumping costs, retention value, and its settlement boundary
must therefore be made explicit and reconciled with the model and final results.
The Copenhagen supply-portfolio extension has not been implemented by this edit.

Numerical results are retained from the source manuscript and have not been
recomputed or validated against model code. The fixed-tariff charging/discharging
hours, annual horizon, and comparison metrics need checking before publication.
Behavioural response and the five-step feedback loop remain future work.
The source conclusion/acknowledgements are empty and are not printed until written.
The abstract still needs final results after the analysis is complete.

The newly resolved PlanEnergi project reference documents the installation;
the exact annual compensation and contractual allocation still require a primary
contract or stakeholder record. Institutional descriptions have not been fact
audited as part of the layout edit.

## Layout validation

The final pdfLaTeX/BibTeX build passes with no undefined references or citations,
no duplicate bibliography keys, and no overfull boxes. All 14 rendered pages were
visually reviewed. This validates typesetting, not the numerical model.
