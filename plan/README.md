# Plan: from draft to an Applied Energy submission

Working plan for turning the November 2026 draft into a submission to *Applied Energy*.
It lists what to strengthen, in which order, what depends on external data, and which
risks could stop the paper and how to reduce them.

Status: 10 November 2026. Draft sent to HTF; data requested from HTF and Varmelast.
Model branch: `DynSys-PTES/feature/rolling-horizon-demand`.

---

## 1. Goal and core message

**Research question.** Can a dynamic PTES discharge credit, derived from the value of
storage in the coordinated heat schedule, make both the local operator (HTF) and the
upstream side (VEKS and producers) better off than the current settlement?

**Contribution to defend.** Not marginal-cost pricing of heat as such, but:

1. a settlement for a storage that is **scheduled by one party and implemented by
   another**, at the boundary between a transmission and a distribution company;
2. a credit derived from the dual values of the coordinated schedule, tested against
   the operator's **own best response**, not assumed compliance;
3. an evaluation against **measured operation**, with the distribution of gains between
   the actors;
4. design insights that carry over to other storage at ownership boundaries: timing
   matters more than level, a small credit suffices, and the transfer is a design choice.

**What the paper must show convincingly.** (a) The mechanism works under realistic
planning (forecasts, daily re-planning), (b) the result is robust to the uncertain
inputs, (c) the tariff parameters are justified rather than chosen, and (d) the
findings generalise beyond Høje Taastrup.

---

## 2. Status of the current draft

| Element | Status |
|---|---|
| Framework (coordinated schedule, credit, HTF response, corrective dispatch) | Done |
| Measured 2024 reference, validation against Varmelast production (< 1 %) | Done |
| Weekly perfect-foresight results, value sharing, schedule following, 23 vs 30 MW | Done (Gurobi) |
| HTF demand at 2024 level and weather | Done, rerun pending |
| Rolling daily planning (24 h and 7 days) | Implemented, runs pending |
| Sensitivities (minimum flows, pumping, heat-pump electricity cost, credit level) | Configs ready, runs pending |
| Tariff parameter sweep | Not started |
| Local generation at HTF (data centres, solar, recovered heat) | On hold, waiting for HTF |
| Forecasts and planned schedules | Requested from Varmelast |
| Literature review, generalisation, policy section | To be extended |

---

## 3. Workstreams

Each workstream lists the tasks, the output for the paper and what it depends on.
Owner: **T** = Tom, **C** = Claude (code, analysis, drafting support), **H** = Henrik
and co-authors, **E** = external (HTF, Varmelast, VEKS).

### A. Realistic planning (addresses: perfect foresight)

| Task | Owner | Depends on | Output |
|---|---|---|---|
| A1. Weekly study with 2024 demand (`paper_weekly_metered_2024.yaml` + `--htf-demand`) | T | – | Updated benchmark numbers |
| A2. Rolling 24 h study (`paper_rolling24_2024.yaml`) | T | A1 | Validation: model without credit vs measured operation |
| A3. Rolling 7-day study (`paper_rolling_2024.yaml`) | T | A1 | Main estimate of the tariff effect |
| A4. Analyse A2–A3: share of the weekly saving that survives daily planning | C | A2, A3 | Results table and figure: weekly (upper bound) vs rolling |
| A5. Replace planning inputs with Varmelast forecasts | C | E: forecasts | Rolling study with real information sets |
| A6. Compare planned 2024 schedules with measured operation | C | E: schedules | Neutral explanation of the measured operation |

*Decision point after A2:* if the 24 h rolling run is far from the measured operation,
find out why (network restrictions, local operation, model) before writing results.

### B. Tariff design (addresses: ad hoc parameters)

| Task | Owner | Depends on | Output |
|---|---|---|---|
| B1. Sweep mean credit level (e.g. 1–15 DKK/MWh) and strength *g* (0–1) | C (config), T (run) | A1 | Frontier of system saving vs transfer to HTF |
| B2. Identify the smallest credit that gives most of the saving; check both-sides-gain in all weeks | C | B1 | Justified parameter choice |
| B3. Compare hourly credit, value share and a payment for following the schedule | C | B1, existing runs | Design comparison section |
| B4. Implementation: credit announced with the day-ahead plan, settlement period, revisions | T, H | A3, E: Varmelast view | Discussion section |

### C. Robustness (addresses: provisional inputs)

| Task | Owner | Depends on | Output |
|---|---|---|---|
| C1. Run `paper_sensitivity_metered_2024.yaml` (minimum flows 2/2 MW, pumping, heat-pump electricity cost) with 2024 demand | T | A1 | Sensitivity table |
| C2. Add gas price ±25 % (monthly gas prices if time allows), transmission loss 1–4 %, PTES loss | C | – | Extended sensitivity table |
| C3. Old (2019) vs new (2024-weather) demand | C | A1 | Robustness note |
| C4. One-pass response: test one further iteration (re-derive the credit after the upstream adapts) | C | A1 | Justification of one-pass coupling or iterated results |
| C5. Solver robustness: Gurobi vs HiGHS on key cases | T, C | – | Appendix note |
| C6. Heat values after the upstream adjustment vs planned values (small-player check) | C | A1 | Supports one-pass coupling |
| C7. Day-ahead commitment and balancing: price deviations of upstream electricity output from the plan at imbalance prices (see section 7) | C | Imbalance prices (public); E: planned schedules for the reference | Cost of deviating from the schedule, value of following it |

### D. Local system (addresses: HTF side of the model)

| Task | Owner | Depends on | Output |
|---|---|---|---|
| D1. Replace the demand profile with HTF's measured hourly 2024 data | C | E: HTF data | Calibrated demand |
| D2. Add data-centre heat pumps, other recovered heat and solar heat as fixed local supply | C | E: HTF on how they are operated | Correct summer room for discharge |
| D3. Calibrate City2 and Mølleholmen (output, limits, electricity costs) | C | E: HTF data | Credible heat-pump result |
| D4. Discharge limits in practice (23 MW, summer conditions, network) | T | E: HTF | Correct constraints, discussion |
| D5. Peak coverage: heat exchanger vs local peak units | T | E: HTF | Confirm or change `hx.cover_peak` |

### E. Paper (addresses: novelty, generalisation, presentation)

| Task | Owner | Depends on | Output |
|---|---|---|---|
| E1. Literature review: storage remuneration and flexibility pricing; multi-actor district heating and third-party access; coordination between transmission and distribution operators (electricity analogues); bilevel and mechanism-design approaches; PTES operation studies | T, C | – | Extended introduction, clear gap |
| E2. Sharpen contribution statements and research question around the ownership boundary | T, H | E1 | Introduction |
| E3. Generalisation section: conditions under which the result transfers (who schedules, who pays pumping, settlement structure, storage size relative to the system) | T, C | B, C | Discussion section |
| E4. Policy implications for Danish district heating (non-profit regulation, heat purchase agreements) | T, H | B4 | Discussion section |
| E5. Figures: framework, weekly operation, annual distribution, rolling vs weekly, tariff frontier, sensitivity tornado | C | A–C | Final figures |
| E6. Journal formalities: highlights, graphical abstract, CRediT statement, data and code availability, competing interests, current Guide for Authors | T | E1–E5 | Submission package |
| E7. Internal review by co-authors; external read by HTF/VEKS for factual accuracy and wording | H, E | E6 | Final manuscript |

### F. Reproducibility

| Task | Owner | Output |
|---|---|---|
| F1. Tag the model version used for every result; keep configs and result summaries in the repo | C | Traceable results |
| F2. One script that regenerates all paper numbers and figures from the result folders | C | `paper_numbers.py` extended |
| F3. Clarify which data can be published (metered PTES data, HTF data, Varmelast data) | T, E | Data availability statement |

---

## 4. Timeline

The phases overlap; external data decides how fast phase 3 can finish.

| Phase | Weeks | Content |
|---|---|---|
| 1. Runs that need no new data | 1–2 | A1–A3, C1, C5; parameter sweep config (B1) |
| 2. Analysis and method | 2–6 | A4, B1–B3, C2–C4; literature review (E1, E2) |
| 3. Data-dependent work | 3–10 | A5, A6, D1–D5 as data arrive |
| 4. Writing | 6–12 | E3–E5, rewrite of results around rolling and sweep |
| 5. Review and submission | 11–14 | E6, E7, final check of all numbers (F2) |

Target: submission roughly three months after the start of phase 1, if HTF and
Varmelast data arrive within about six weeks. Otherwise submit with the data available
and report the remaining points as limitations.

*Journal decision point (with Henrik), end of phase 3:* Applied Energy if A–C are done
and at least part of D; otherwise *Energy* or *Smart Energy*.

---

## 5. Risks and mitigation

Likelihood and impact: H = high, M = medium, L = low.

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | **Novelty judged incremental** ("marginal-cost heat pricing is known"), desk rejection | M | H | Frame the contribution around the ownership boundary and the operator's own response, tested against measured operation (E1, E2); show design insights (B); ask Henrik to check the framing before submission |
| 2 | **Savings shrink under daily planning and forecasts** | M | M | Report it as a result: the share of the value that is robust to planning practice. The mechanism and distribution findings remain; the weekly run becomes the upper bound |
| 3 | **HTF or Varmelast data do not arrive or arrive late** | M | M | Paper is designed to work without them: rolling runs with actual data, sensitivities on the uncertain inputs, transparent limitations; set a cut-off date for waiting |
| 4 | **Data cannot be published** (confidential metered or planning data) | M | M | Agree early what can be shown (aggregates, normalised profiles); state it in the data availability statement (F3) |
| 5 | **Stakeholder sensitivity**: results read as criticism of HTF's operation | M | H | Keep neutral wording (settlement, planning information, not behaviour); let HTF and VEKS check facts before submission (E7); acknowledge their input |
| 6 | **Single case study** limits generality | H | M | Generalisation section (E3) with transfer conditions; sensitivities covering other system sizes or prices if time allows |
| 7 | **Reviewers expect uncertainty treatment** (stochastic or robust optimisation) | M | M | Rolling planning with forecasts (A5); forecast-error sensitivity; discuss stochastic extension as further work |
| 8 | **Simplified upstream model** (one heat node, constant fuel prices, no CHP start-ups) | M | L | Validation against Varmelast production; gas-price sensitivity; argue that the credit depends on day-to-day value differences, which the model captures |
| 9 | **Tariff parameters look arbitrary** | H | M | Parameter sweep and frontier (B1, B2) |
| 10 | **One-pass coupling criticised** | M | M | Iteration test (C4) and small-player check (C6); argue that announce-then-respond is the implementable sequence; if differences are small, keep one pass and state it |
| 15 | **Corrective dispatch too optimistic**: upstream re-dispatch at day-ahead prices ignores that electricity bids are already placed, so balancing costs of deviations are missing | M | M | Two-settlement evaluation (C7); report the deviation volumes now and the balancing cost once imbalance prices are added |
| 11 | **Heat-pump result driven by a placeholder cost** | H | L | Present it as a secondary finding with a sensitivity; calibrate with HTF data (D3) |
| 12 | **Compute time** for rolling studies and sweeps | M | L | Run on Gurobi overnight; split configs; start with the 24 h run |
| 13 | **Scope creep** (adding many extensions) | M | M | Keep this plan as the scope; new ideas go to "further work" unless they answer a reviewer risk above |
| 14 | **Inconsistent numbers** across text, tables and figures after reruns | M | M | Generate all numbers from one script (F2); final consistency check before submission |

---

## 6. Immediate next steps

1. Tom: run A1 (weekly with 2024 demand), then A2 and A3 (rolling) with Gurobi; upload
   the result folders.
2. Claude: prepare the parameter sweep config (B1), the extra sensitivities (C2) and
   the iteration test (C4).
3. Tom: start the literature review (E1) with the topics listed above.
4. Tom and Henrik: agree on the target journal criteria and the cut-off date for
   external data.
5. Follow up with HTF and Varmelast about two weeks after the requests.

---

## 7. How to address the expected reviewer points

### 7.1 Ad hoc tariff parameters (mean 5 DKK/MWh, strength 0.25)

Turn the choice into a result in three steps.

1. **Bound the level by theory.** The derivation gives the limits. The credit must at
   least cover HTF's pumping cost per MWh discharged (about 3–4 DKK/MWh with current
   assumptions); below that, HTF never discharges voluntarily. It should not exceed the
   storage value spread; above it, HTF would discharge when the system would rather keep
   the heat stored. 5 DKK/MWh is then "pumping cost plus a small margin".
2. **Sweep and show the frontier (B1).** Grid of mean levels (2, 3, 4, 5, 7, 10 DKK/MWh)
   and strengths (0 = constant, 0.25, 0.5, 1); plot system saving against the transfer to
   HTF, with the value-share cases in the same figure. The frontier shows which designs
   are efficient, where the hourly credit sits and where more credit stops helping.
3. **State the design criteria and derive the choice (B2).** For example: both sides gain
   in nearly every week, at least 90 % of the maximum recoverable saving, smallest
   transfer to HTF. The paper then reports the smallest credit that meets them.

Optional: repeat the sweep with low and high pumping costs. If the efficient level moves
with the pumping cost, this confirms the general rule "credit = implementation cost +
timing from the storage value".

### 7.2 One-pass response

Use a justification and a test together.

- **Justification.** Announce-then-respond is the implementable sequence: a tariff must be
  known before HTF acts, and prices cannot be changed after the response. The coordinated
  schedule is the upper bound, so the paper already reports the full gap between one
  pass and the optimum; iterating could only close part of it.
- **Small player (C6).** The PTES discharges at most 30 MW into a regional demand of about
  1–3 GW. Compare the heat values after the upstream adjustment with the planned ones; a
  mean change of a few DKK/MWh supports price-taking behaviour.
- **Test (C4).** Derive a new credit from the values after the upstream adjustment, let HTF
  respond again and compare the saving. A change of a few percent: keep one pass and
  report the test in an appendix. A large change: a finding in itself, showing that the
  timing of the price announcement matters.

### 7.3 Day-ahead commitment and balancing costs (extends 7.2)

The corrective dispatch re-optimises the upstream units at day-ahead electricity prices
with full flexibility. In reality the heat plan is made before the day-ahead auction, and
the CHP electricity bids follow from it. If the PTES operation differs from the plan, the
upstream units must change their electricity output after the auction. That creates
imbalances, which are traded intraday or settled at imbalance prices. The current model
therefore **underestimates the cost of deviating from the schedule**, and so the value of
following it.

First numbers from the weekly study with 2024 demand (deviation of upstream net
electricity output from the coordinated plan, summed over the year):

| Case | Deviation from plan | Hours > 10 MW |
|---|---|---|
| Measured 2024 operation | 45 GWh | 587 |
| HTF response to the hourly credit | 5.9 GWh | 132 |
| Full value share | 5.2 GWh | 128 |

Caveat: for the measured operation the relevant plan is Varmelast's, not the model's
perfect-foresight schedule, so this deviation is an upper estimate until the planned 2024
schedules are available.

**How to model it (C7).** A two-settlement evaluation: the plan fixes the day-ahead
electricity position of the upstream units; in the corrective dispatch, deviations from
that position are priced at DK2 imbalance prices (published on Energi Data Service)
instead of the day-ahead price. In the rolling setup this maps naturally onto
"day-ahead plan vs. actual day". Expected result: the measured operation becomes more
costly relative to the plan, the value of the tariff and of following the schedule rises,
and the case for a credit (or a payment for following the schedule) becomes stronger.
Points to clarify with Varmelast: how deviations from the heat plan are handled today
(intraday trading, regulating power, accumulators), and whether producers bear the
balancing costs or pass them on.

### 7.4 Generalisability

- Name the conditions behind the result: one party schedules and another implements; the
  settlement price is flat while the value of heat varies; the implementer bears an
  operating cost; the store is small relative to the system. Where these hold, the rule
  "credit = value of delivering heat now minus value of keeping it stored" carries over.
- Transferability table: Høje Taastrup against other multi-actor district heating systems
  with large stores, and the electricity analogue (distribution-level flexibility used by
  the transmission operator).
- Test other market conditions: another price year (2023 or 2025) or more volatile
  electricity prices.
- Policy guidance: remunerate the use of storage, not only its capacity; derive the credit
  from the planner's own heat values and announce it with the plan; treat the size of the
  transfer as negotiable, since it hardly affects efficiency.

### 7.5 Literature review

Four themes, each ending in the gap for this case:
1. pricing of heat and flexibility in district heating (marginal-cost and time-varying
   heat prices);
2. remuneration of storage, in electricity and heat;
3. multi-actor district heating (third-party access, heat purchase agreements,
   coordination between producers and distribution companies);
4. coordination between transmission and distribution operators and mechanism design
   (the electricity analogue; bilevel and leader-follower models framing the one-pass
   setup).

Search Scopus or Web of Science per theme and select 5–8 core papers each. Every
reference is checked against the source.

### 7.6 Provisional inputs

- Tornado chart of the hourly credit's system saving and HTF's gain over minimum flows,
  pumping, heat-pump electricity cost, transmission losses and gas price.
- Break-even values, e.g. "the conclusion holds as long as pumping costs below X".
- Replace placeholders as HTF's data arrive; mark measured vs. assumed inputs in the
  parameter table.
