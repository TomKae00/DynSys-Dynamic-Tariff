# Validation record — 3 November 2026

These checks validate implementation and numerical feasibility. They do not
calibrate the scenario against actual producer dispatch or establish a final tariff.
The executed input audit is retained in [validation_inputs.json](validation_inputs.json).
Compact solve results are retained in `validation_metrics.json`.

## Automated checks

All **13 tests** pass under Python 3.12, NumPy 2.3.5, pandas 2.2.3 and SciPy 1.17.0.
Ruff lint and formatting checks pass. The offline 48-hour CI demonstration also
solves with fixed-commitment LP marginal values. GitHub Actions is configured to
repeat those offline checks; a local pass is not a claim that hosted CI has run.

The tests cover both heat-node balances, shared CHP fuel/conversion regions,
PTES power limits/ramps/mode exclusivity/reversal delays, inventory endpoints,
regional accumulator endpoints, HP commitment duration and thermal ceilings under
variable COP, objective/settlement accounting, endogenous price response,
infeasibility rejection, leap-year/DST alignment, bounded opt-in repairs and API
error flags. A finite-difference demand perturbation verifies marginal-value sign
and loss scaling. Discharge credits are checked as transfers outside system cost.
The optional Gurobi 13.0.3 backend matches HiGHS on a 24-hour integer case and
extracts fixed-commitment LP duals. That test is skipped when Gurobi is not installed;
the default CI environment runs the 12 solver-independent/HiGHS tests.

## Public 2024 inputs

The complete model year contains 8784 unique consecutive UTC hours. Preparation
repaired **87 data cells**: 41 CTR, 43 VEKS and 3 waste values. This includes a
39-hour consumption outage and the missing repeated hour at the autumn clock
change. Every replacement and method is recorded, not silently filled.

After these explicit repairs, CTR consumption totals 6.2055 TWh and VEKS 2.5670 TWh.
The inherited 2019 HTF seasonal template contributes 0.34955 TWh when mapped into
the 2024 model year. These are scenario inputs, not a verified compatible set of
gross-demand measurements. A 2% upstream loss assumption is then applied in the
model; it has not been estimated from those totals.

## Executed dispatch checks

| Case | Hours | Net operating objective DKK | Reported relative gap | Maximum balance/constraint residual MW or MWh |
|---|---:|---:|---:|---:|
| Winter, 8–14 January UTC | 168 | 30,161,388.99 | 0.00000179 | < 1e-9 |
| Summer, 15–21 July UTC | 168 | −16,760,860.79 | 0.00000934 | < 1e-9 |
| Annual LP relaxation | 8784 | −233,802,529.77 | 0 | < 1e-9 |

The annual LP has 386,496 variables and 404,061 constraints. Its relaxed modes are
not an operational PTES schedule. The seasonal MILPs include fixed-commitment LP
price extraction. The full-year endogenous-HP MILP was interrupted after about
608 seconds without an accepted exported result. The solver's 120-second limit
did not provide a strict process wall limit. No annual integer schedule, cycles
or prices are claimed from that attempt; complete it on the intended research
machine with an explicit runtime budget. This is a computational validation limit,
not a proof of infeasibility.
A separate annual must-run-HP attempt also exceeded an external 90-second process
budget and exported no result. No full-year Gurobi case was run; it requires a
licence covering the annual model size. The optional backend is provided for that
research environment, without claiming it resolves the annual case here.

Negative objectives include electricity-sales revenue, including extraction-unit
condensing generation. They are not negative heat tariffs, observed utility costs
or pure heat-production resource costs. Compare like-for-like scenarios and retain
the electricity and fuel cost components. An annual LP cycling result must not be
reported as a physical integer-operation result.

A local winter discharge-service experiment holds the same central charging
schedule fixed. The zero-credit local objective is 3,649,447.92 DKK; a constant
illustrative 50 DKK/MWh credit gives 3,575,797.92 DKK. These are local expenditures.
The difference is not demonstrated system savings: upstream corrective redispatch
is not part of this experiment. No conclusion about an optimal tariff follows.

## Scientific checks still required

Confirm the CTR/VEKS/HTF metering boundary; replace the inherited local demand
template where observations exist; verify 2024 plant availability and contract/fuel
costs; test fixed/must-take waste treatment and congestion; calibrate PTES losses
and pumping; confirm the discharge settlement boundary; and compare optimised
flows with independent measured energy totals. Test 23/30 MW PTES capacity,
loss assumptions, HP must-run policy, demand boundaries and horizon endpoints.

Add tariff derivation, downstream response assumptions and upstream corrective
redispatch before evaluating the complete proposed soft-coupling workflow.
Reconcile the manuscript equations/results with this model after that validation.
