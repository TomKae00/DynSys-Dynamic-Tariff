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
| 10 | **One-pass coupling criticised** | M | M | Iteration test (C4); if differences are small, keep one pass and state it |
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
