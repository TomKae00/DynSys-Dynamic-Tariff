"""Sparse linear/MILP formulation; SciPy's bundled HiGHS needs no commercial licence."""

from copy import deepcopy
from dataclasses import dataclass
from types import SimpleNamespace

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, linprog, milp
from scipy.sparse import coo_matrix, vstack


class LinearModel:
    def __init__(self, hours):
        self.hours = hours
        self.variables = {}
        self.cost, self.lower, self.upper, self.integer = [], [], [], []
        self.row, self.col, self.data = [], [], []
        self.row_lower, self.row_upper, self.row_names = [], [], []

    def variable(self, name, *, lower=0, upper=np.inf, cost=0, integer=False):
        if name in self.variables:
            raise ValueError(f"Duplicate variable {name}")
        indices = np.arange(len(self.cost), len(self.cost) + self.hours)
        self.variables[name] = indices
        for target, value in [
            (self.cost, cost),
            (self.lower, lower),
            (self.upper, upper),
            (self.integer, int(integer)),
        ]:
            target.extend(np.broadcast_to(value, self.hours).tolist())
        return indices

    def constraint(self, name, terms, *, lower=-np.inf, upper=np.inf):
        size = len(terms[0][0])
        rows = np.arange(len(self.row_lower), len(self.row_lower) + size)
        for indices, coefficient in terms:
            if len(indices) != size:
                raise ValueError(f"Misaligned constraint {name}")
            self.row.extend(rows)
            self.col.extend(indices)
            self.data.extend(np.broadcast_to(coefficient, size))
        self.row_lower.extend(np.broadcast_to(lower, size))
        self.row_upper.extend(np.broadcast_to(upper, size))
        self.row_names.extend([name] * size)
        return rows

    def equality(self, name, terms, rhs):
        return self.constraint(name, terms, lower=rhs, upper=rhs)

    def matrix(self):
        return coo_matrix(
            (self.data, (self.row, self.col)), shape=(len(self.row_lower), len(self.cost))
        ).tocsc()


def validate_inputs(frame, config, plants):
    required = [
        "regional_demand_mw",
        "htf_demand_mw",
        "waste_available_mw",
        "electricity_dkk_mwh",
        "city2_cop",
        "groundwater_cop",
        "reference_tariff_dkk_mwh",
    ]
    if len(frame) < 2 or not isinstance(frame.index, pd.DatetimeIndex) or frame.index.tz is None:
        raise ValueError("At least two timezone-aware hourly snapshots required")
    if frame.index.has_duplicates or not np.all(np.diff(frame.index.asi8) == 3600 * 10**9):
        raise ValueError("Snapshots must be unique and consecutive UTC hours")
    if not np.isfinite(frame[required].to_numpy(dtype=float)).all():
        raise ValueError("Inputs contain non-finite values")
    if (frame[["regional_demand_mw", "htf_demand_mw", "waste_available_mw"]] < 0).any().any():
        raise ValueError("Negative heat demand or waste availability")
    if (frame[["city2_cop", "groundwater_cop"]] <= 1).any().any():
        raise ValueError("Heat-pump COP must exceed one")
    if config["demand_boundary"] not in ("assumed_gross_including_htf", "residual_excluding_htf"):
        raise ValueError("Unresolved demand boundary; net withdrawals need historical HTF metering")
    if config["objective"] not in ("system", "local"):
        raise ValueError("Objective must be system or local")
    if config["settlement_boundary"] not in ("discharge_service", "legacy_owned_store"):
        raise ValueError("Unknown settlement boundary")
    if config["objective"] == "local" and config["settlement_boundary"] == "discharge_service":
        if (
            "scheduled_ptes_charge_mw" not in frame
            or not np.isfinite(frame.scheduled_ptes_charge_mw).all()
        ):
            raise ValueError(
                "Discharge-service response needs a complete central charging schedule"
            )
    if not 0 <= config["network_loss_fraction"] < 1:
        raise ValueError("Network loss fraction must be in [0,1)")
    for group in [config["ptes"], *config["upstream"]["accumulators"].values()]:
        if group["energy_mwh"] <= 0 or group["power_mw"] <= 0:
            raise ValueError("Storage capacities must be positive")
        if not 0 <= group["loss_per_hour"] < 1:
            raise ValueError("Storage hourly loss must be in [0,1)")
    ptes = config["ptes"]
    if not all(0 <= ptes[k] <= ptes["energy_mwh"] for k in ["initial_mwh", "terminal_mwh"]):
        raise ValueError("PTES boundary inventories exceed capacity")
    if not all(0 < ptes[k] <= 1 for k in ["charge_efficiency", "discharge_efficiency"]):
        raise ValueError("PTES efficiencies must be in (0,1]")
    if not 0 <= config["hx"]["minimum_mw"] <= config["hx"]["capacity_mw"]:
        raise ValueError("Invalid HX bounds")
    if plants.name.duplicated().any() or not plants.kind.isin(["backpressure", "extraction"]).all():
        raise ValueError("Plant names must be unique and kinds explicitly supported")
    if ((plants.availability < 0) | (plants.availability > 1)).any():
        raise ValueError("Availability factors must be in [0,1]")


def add_storage(model, name, settings, *, terminal, initial):
    charge = model.variable(name + "_charge_mw", upper=settings["power_mw"])
    discharge = model.variable(name + "_discharge_mw", upper=settings["power_mw"])
    energy = model.variable(name + "_energy_mwh", upper=settings["energy_mwh"])
    retention = 1 - settings["loss_per_hour"]
    ec = settings.get("charge_efficiency", 1.0)
    ed = settings.get("discharge_efficiency", 1.0)
    model.equality(
        name + "_initial",
        [(energy[:1], 1), (charge[:1], -ec), (discharge[:1], 1 / ed)],
        retention * initial,
    )
    model.equality(
        name + "_balance",
        [(energy[1:], 1), (energy[:-1], -retention), (charge[1:], -ec), (discharge[1:], 1 / ed)],
        0,
    )
    model.equality(name + "_terminal", [(energy[-1:], 1)], terminal)
    return charge, discharge, energy


def add_heat_pump(model, name, capacity, cop, price, settings, *, integer):
    q = model.variable(name + "_heat_mw", upper=capacity, cost=price / cop)
    policy = settings.get("policy", "endogenous")
    if policy == "must_run":
        model.equality(name + "_must_run", [(q, 1)], capacity)
        return q
    if policy != "endogenous":
        raise ValueError("Heat pump policy must be endogenous or must_run")
    on = model.variable(name + "_on", upper=1, integer=integer)
    start = model.variable(
        name + "_start", upper=1, integer=integer, cost=capacity * settings["startup_dkk_per_mw"]
    )
    stop = model.variable(name + "_stop", upper=1, integer=integer)
    model.constraint(name + "_maximum", [(q, 1), (on, -capacity)], upper=0)
    model.constraint(
        name + "_minimum", [(q, 1), (on, -capacity * settings["minimum_fraction"])], lower=0
    )
    model.equality(name + "_initial_off", [(on[:1], 1), (start[:1], -1), (stop[:1], 1)], 0)
    model.equality(
        name + "_transition", [(on[1:], 1), (on[:-1], -1), (start[1:], -1), (stop[1:], 1)], 0
    )
    model.constraint(name + "_one_transition", [(start, 1), (stop, 1)], upper=1)
    for event, duration, sign in [
        (start, settings["minimum_up_hours"], 1),
        (stop, settings["minimum_down_hours"], -1),
    ]:
        for lag in range(duration):
            count = len(q) - lag
            if count <= 0:
                continue
            model.constraint(
                name + f"_duration_{sign}_{lag}",
                [(event[:count], 1), (on[lag:], -sign)],
                upper=0 if sign == 1 else 1,
            )
        # Forbid transitions whose minimum duration extends beyond the horizon.
        if duration > 1:
            model.equality(name + f"_end_transition_{sign}", [(event[-(duration - 1) :], 1)], 0)
    return q


def build(frame, config, plants):
    config = deepcopy(config)
    validate_inputs(frame, config, plants)
    n = len(frame)
    model = LinearModel(n)
    integer = config["integer_operation"]
    system = config["objective"] == "system"
    price = frame.electricity_dkk_mwh.to_numpy()
    tariff = frame.reference_tariff_dkk_mwh.to_numpy()
    discount = (
        frame.discharge_discount_dkk_mwh.to_numpy()
        if "discharge_discount_dkk_mwh" in frame
        else np.full(n, config["discharge_discount_dkk_mwh"])
    )
    hx = model.variable(
        "hx_mw",
        lower=config["hx"]["minimum_mw"],
        upper=config["hx"]["capacity_mw"],
        cost=0 if system else tariff,
    )
    ptes = config["ptes"]
    charge, discharge, _energy = add_storage(
        model, "ptes", ptes, initial=ptes["initial_mwh"], terminal=ptes["terminal_mwh"]
    )
    pump = ptes["pump_mwh_el_per_mwh_heat"] * (
        price + config["heat_pumps"]["electricity_adder_dkk_mwh"]
    )
    owned = config["settlement_boundary"] == "legacy_owned_store"
    if not system and not owned:
        model.equality(
            "central_charging_schedule", [(charge, 1)], frame.scheduled_ptes_charge_mw.to_numpy()
        )
    # The paper boundary bills direct heat and discharge; charging belongs upstream.
    # The explicitly named legacy experiment instead purchases charging heat locally.
    for ids, cost in [
        (charge, pump if system else (tariff + pump if owned else 0)),
        (discharge, pump if system else pump - discount + (0 if owned else tariff)),
    ]:
        np_cost = np.array(model.cost, dtype=float)
        np_cost[ids] += cost
        model.cost = np_cost.tolist()
    yc = model.variable("ptes_charge_on", upper=1, integer=integer)
    yd = model.variable("ptes_discharge_on", upper=1, integer=integer)
    for flow, status, minimum in [
        (charge, yc, ptes["min_charge_mw"]),
        (discharge, yd, ptes["min_discharge_mw"]),
    ]:
        model.constraint("ptes_mode_max", [(flow, 1), (status, -ptes["power_mw"])], upper=0)
        model.constraint("ptes_mode_min", [(flow, 1), (status, -minimum)], lower=0)
        model.constraint(
            "ptes_ramp",
            [(flow[1:], 1), (flow[:-1], -1)],
            lower=-ptes["ramp_mw_h"],
            upper=ptes["ramp_mw_h"],
        )
        model.constraint("ptes_initial_idle_ramp", [(flow[:1], 1)], upper=ptes["ramp_mw_h"])
    model.constraint("ptes_exclusive", [(yc, 1), (yd, 1)], upper=1)
    for lag in range(1, ptes["reversal_hours"] + 1):
        if lag < n:
            model.constraint("ptes_no_reversal", [(yc[:-lag], 1), (yd[lag:], 1)], upper=1)
            model.constraint("ptes_no_reversal", [(yd[:-lag], 1), (yc[lag:], 1)], upper=1)
    model.constraint(
        "shared_htf_connection", [(hx, 1), (charge, 1)], upper=config["hx"]["capacity_mw"]
    )
    hp = config["heat_pumps"]
    local_terms = [(hx, 1), (discharge, 1)]
    for name in ["city2", "groundwater"]:
        spec = hp[name]
        q = add_heat_pump(
            model,
            name,
            spec["capacity_mw"],
            frame[spec["cop_column"]].to_numpy(),
            price + hp["electricity_adder_dkk_mwh"],
            hp,
            integer=integer,
        )
        local_terms.append((q, 1))
    model.equality("local_heat_balance", local_terms, frame.htf_demand_mw.to_numpy())
    if system:
        upstream = config["upstream"]
        regional = frame.regional_demand_mw.to_numpy()
        residual = (
            regional - frame.htf_demand_mw.to_numpy()
            if config["demand_boundary"] == "assumed_gross_including_htf"
            else regional
        )
        if (residual < 0).any():
            raise ValueError("Regional demand smaller than HTF demand; check boundary, do not clip")
        loss_multiplier = 1 / (1 - config["network_loss_fraction"])
        supply = [(hx, -loss_multiplier), (charge, -loss_multiplier)]
        for plant in plants.itertuples(index=False):
            a = plant.availability
            q = model.variable(
                plant.name + "_heat_mw",
                upper=(plant.heat_mw + plant.bypass_mw) * a,
                cost=plant.vom_dkk_mwh_heat,
            )
            p = model.variable(plant.name + "_power_mw", upper=plant.power_mw * a, cost=-price)
            fuel = model.variable(
                plant.name + "_fuel_mw", upper=plant.fuel_mw * a, cost=plant.fuel_dkk_mwh
            )
            if plant.kind == "backpressure":
                bypass = model.variable(plant.name + "_bypass_mw", upper=plant.bypass_mw * a)
                model.equality(
                    plant.name + "_heat_region", [(q, 1), (p, -1 / plant.cm), (bypass, -1)], 0
                )
                model.equality(
                    plant.name + "_fuel_balance",
                    [(fuel, 1), (p, -1 / plant.eta_el), (bypass, -1 / plant.eta_bypass)],
                    0,
                )
            else:
                model.constraint(
                    plant.name + "_extraction_region",
                    [(p, 1), (q, plant.cv), (fuel, -plant.eta_el)],
                    upper=0,
                )
                model.constraint(
                    plant.name + "_backpressure_limit", [(p, 1), (q, -plant.cm)], lower=0
                )
            supply.append((q, 1))
        peaks = []
        for fuel in ["gas", "oil", "bio", "electric"]:
            cost = (
                (price + upstream["electricity_adder_dkk_mwh"])
                if fuel == "electric"
                else upstream[fuel + "_dkk_mwh_fuel"]
            )
            q = model.variable(
                fuel + "_boiler_heat_mw",
                upper=upstream[fuel + "_mw"],
                cost=cost / upstream[fuel + "_efficiency"] + upstream["boiler_vom_dkk_mwh"],
            )
            peaks.append((q, 1))
            supply.append((q, 1))
        model.constraint("peak_shared_fuel_capacity", peaks, upper=upstream["shared_peak_mw"])
        if upstream["waste_policy"] != "observed_upper_bound":
            raise ValueError("Only observed_upper_bound waste policy is supported")
        waste = model.variable(
            "waste_heat_mw",
            upper=np.minimum(frame.waste_available_mw.to_numpy(), upstream["waste_capacity_mw"]),
            cost=upstream["waste_vom_dkk_mwh_heat"] - price * upstream["waste_power_heat_ratio"],
        )
        supply.append((waste, 1))
        regional_hp = model.variable(
            "regional_hp_heat_mw",
            upper=upstream["heat_pump_mw"],
            cost=(price + upstream["electricity_adder_dkk_mwh"]) / upstream["heat_pump_cop"],
        )
        supply.append((regional_hp, 1))
        for name, settings in upstream["accumulators"].items():
            c, d, _ = add_storage(
                model,
                name,
                settings,
                initial=settings["energy_mwh"] / 2,
                terminal=settings["energy_mwh"] / 2,
            )
            # Continuous accumulators are an explicit relaxation: gross flows are bounded
            # and reported; a shared converter prevents doubling rated heat exchange.
            model.constraint(
                name + "_shared_converter", [(c, 1), (d, 1)], upper=settings["power_mw"]
            )
            supply.extend([(c, -1), (d, 1)])
        model.equality("regional_heat_balance", supply, residual * loss_multiplier)
    model.config, model.inputs, model.plants = config, frame.copy(), plants.copy()
    return model


@dataclass
class Solution:
    dispatch: pd.DataFrame
    summary: dict
    raw: object


def gurobi_solve(model, *, lower=None, upper=None, integer=None):
    """Optional licensed backend for the exact same sparse matrix, including LP duals."""
    try:
        import gurobipy as gp
    except ImportError as error:
        raise RuntimeError(
            "Install the optional gurobi extra and supply a valid licence"
        ) from error
    try:
        with gp.Env(params={"OutputFlag": 0}) as env, gp.Model(env=env) as optimisation:
            settings = model.config["solver"]
            optimisation.Params.TimeLimit = settings["time_limit"]
            optimisation.Params.MIPGap = settings["mip_rel_gap"]
            optimisation.Params.Threads = settings.get("threads", 4)
            discrete = np.array(model.integer if integer is None else integer, dtype=bool)
            variables = optimisation.addMVar(
                len(model.cost),
                lb=np.array(model.lower if lower is None else lower),
                ub=np.array(model.upper if upper is None else upper),
                obj=np.array(model.cost),
                vtype=np.where(discrete, "I", "C"),
            )
            matrix = model.matrix().tocsr()
            low, high = np.array(model.row_lower), np.array(model.row_upper)
            eq = low == high
            blocks = []
            for mask, sense, rhs in [
                (eq, "=", low),
                (~eq & np.isfinite(high), "<", high),
                (~eq & np.isfinite(low), ">", low),
            ]:
                if mask.any():
                    blocks.append(
                        (mask, optimisation.addMConstr(matrix[mask], variables, sense, rhs[mask]))
                    )
            optimisation.optimize()
            has_solution = optimisation.SolCount > 0
            optimal = optimisation.Status == gp.GRB.OPTIMAL
            duals = np.full(len(low), np.nan)
            if optimal and not discrete.any():
                for mask, block in blocks:
                    duals[mask] = block.Pi
            return SimpleNamespace(
                x=variables.X if has_solution else None,
                fun=optimisation.ObjVal if has_solution else np.nan,
                success=optimal,
                status=0 if optimal else int(optimisation.Status),
                message=f"Gurobi termination status {optimisation.Status}",
                mip_gap=optimisation.MIPGap if has_solution and discrete.any() else 0.0,
                mip_dual_bound=(
                    optimisation.ObjBound
                    if discrete.any()
                    else optimisation.ObjVal
                    if has_solution
                    else np.nan
                ),
                duals=duals,
            )
    except gp.GurobiError as error:
        raise RuntimeError(f"Gurobi could not solve this case: {error}") from error


def conditional_prices(model, solution):
    """LP duals with MILP commitments fixed. They are NOT nonconvex market-clearing prices."""
    matrix = model.matrix().tocsr()
    low, high = np.array(model.row_lower), np.array(model.row_upper)
    equality = low == high
    upper = ~equality & np.isfinite(high)
    lower = ~equality & np.isfinite(low)
    bounds = np.array([model.lower, model.upper], dtype=float).T
    discrete = np.array(model.integer, dtype=bool)
    bounds[discrete, 0] = np.rint(solution.x[discrete])
    bounds[discrete, 1] = np.rint(solution.x[discrete])
    if model.config["solver"].get("backend", "highs") == "gurobi":
        result = gurobi_solve(
            model, lower=bounds[:, 0], upper=bounds[:, 1], integer=np.zeros(len(model.integer))
        )
        if not result.success:
            raise RuntimeError(f"Fixed-commitment LP failed: {result.message}")
        return result.duals[np.array(model.row_names) == "regional_heat_balance"]
    result = linprog(
        model.cost,
        A_ub=vstack([matrix[upper], -matrix[lower]]),
        b_ub=np.r_[high[upper], -low[lower]],
        A_eq=matrix[equality],
        b_eq=low[equality],
        bounds=bounds,
        method="highs",
        options={"time_limit": model.config["solver"]["time_limit"]},
    )
    if not result.success:
        raise RuntimeError(f"Fixed-commitment LP failed: {result.message}")
    names = np.array(model.row_names)[equality]
    return result.eqlin.marginals[names == "regional_heat_balance"]


def solve(model, *, prices=False):
    config = model.config
    backend = config["solver"].get("backend", "highs")
    if backend not in ("highs", "gurobi"):
        raise ValueError("Unknown solver backend")
    result = (
        gurobi_solve(model)
        if backend == "gurobi"
        else milp(
            np.array(model.cost),
            integrality=np.array(model.integer),
            bounds=Bounds(model.lower, model.upper),
            constraints=LinearConstraint(model.matrix(), model.row_lower, model.row_upper),
            options={k: config["solver"][k] for k in ["time_limit", "mip_rel_gap"]},
        )
    )
    if result.x is None or (not result.success and not config["solver"]["allow_suboptimal"]):
        raise RuntimeError(f"No accepted solution: {result.message}")
    activity = model.matrix() @ result.x
    constraint_violation = np.maximum(
        np.array(model.row_lower) - activity, activity - np.array(model.row_upper)
    ).max(initial=0.0)
    bound_violation = np.maximum(
        np.array(model.lower) - result.x, result.x - np.array(model.upper)
    ).max(initial=0.0)
    integer = np.array(model.integer, dtype=bool)
    integer_violation = np.abs(result.x[integer] - np.rint(result.x[integer])).max(initial=0.0)
    if max(constraint_violation, bound_violation, integer_violation) > 1e-5:
        raise RuntimeError("Solver incumbent failed independent feasibility check")
    dispatch = model.inputs.copy()
    for name, indices in model.variables.items():
        dispatch[name] = result.x[indices]
    hp = config["heat_pumps"]
    dispatch["local_hp_electricity_mw"] = sum(
        dispatch[name + "_heat_mw"] / dispatch[hp[name]["cop_column"]]
        for name in ["city2", "groundwater"]
    )
    dispatch["ptes_pump_electricity_mw"] = (
        dispatch.ptes_charge_mw + dispatch.ptes_discharge_mw
    ) * config["ptes"]["pump_mwh_el_per_mwh_heat"]
    owned = config["settlement_boundary"] == "legacy_owned_store"
    local_pump = (
        dispatch.ptes_pump_electricity_mw
        if owned
        else dispatch.ptes_discharge_mw * config["ptes"]["pump_mwh_el_per_mwh_heat"]
    )
    electricity_cost = (dispatch.local_hp_electricity_mw + local_pump) * (
        dispatch.electricity_dkk_mwh + hp["electricity_adder_dkk_mwh"]
    )
    starts = sum(
        dispatch.get(name + "_start", pd.Series(0.0, index=dispatch.index)).sum()
        * hp[name]["capacity_mw"]
        * hp["startup_dkk_per_mw"]
        for name in ["city2", "groundwater"]
    )
    discount = (
        dispatch.discharge_discount_dkk_mwh
        if "discharge_discount_dkk_mwh" in dispatch
        else config["discharge_discount_dkk_mwh"]
    )
    billed_storage_flow = dispatch.ptes_charge_mw if owned else dispatch.ptes_discharge_mw
    heat_payment = (dispatch.hx_mw + billed_storage_flow) * dispatch.reference_tariff_dkk_mwh
    discharge_credit = dispatch.ptes_discharge_mw * discount
    settlements = {
        "heat_purchase_dkk": float(heat_payment.sum()),
        "discharge_credit_dkk": float(discharge_credit.sum()),
        "supplier_local_heat_revenue_dkk": float((heat_payment - discharge_credit).sum()),
        "local_electricity_and_startup_dkk": float(electricity_cost.sum() + starts),
        "local_expenditure_dkk": float(
            (heat_payment - discharge_credit).sum() + electricity_cost.sum() + starts
        ),
    }
    contributions = {
        name: float(np.dot(result.x[ids], np.array(model.cost)[ids]))
        for name, ids in model.variables.items()
    }
    warnings = [
        "Representative scenario; not a calibrated operator model",
        "Unverified demand boundary and 2019 HTF seasonal demand template",
        "Scenario fuel, fiscal and O&M costs; not historical contracts",
        "PTES loss and pumping assumptions require validation",
        "Settlement boundary and reference tariff need contractual verification",
    ]
    if not config["integer_operation"]:
        warnings.append("LP relaxation: fractional modes and simultaneous storage flows possible")
    if config["objective"] == "system":
        warnings.append("Upstream CHP commitment and accumulator operating modes are relaxed")
    summary = {
        "objective_kind": config["objective"],
        "objective_definition": "Net operating expenditure; includes scenario grid/fiscal adders",
        "solver_backend": backend,
        "objective_dkk": float(result.fun),
        "solver_status": int(result.status),
        "solver_message": result.message,
        "mip_gap": float(getattr(result, "mip_gap", 0.0) or 0.0),
        "mip_dual_bound_dkk": (
            float(result.mip_dual_bound)
            if getattr(result, "mip_dual_bound", None) is not None
            else float(result.fun)
        ),
        "accepted_suboptimal": not bool(result.success),
        "hours": len(dispatch),
        "variables": len(model.cost),
        "constraints": len(model.row_lower),
        "max_constraint_violation": float(max(0, constraint_violation)),
        "max_bound_violation": float(max(0, bound_violation)),
        "max_integer_violation": float(integer_violation),
        "ptes_charge_mwh": float(dispatch.ptes_charge_mw.sum()),
        "ptes_discharge_mwh": float(dispatch.ptes_discharge_mw.sum()),
        "ptes_equivalent_cycles": float(
            dispatch.ptes_discharge_mw.sum() / config["ptes"]["energy_mwh"]
        ),
        "ptes_terminal_mwh": float(dispatch.ptes_energy_mwh.iloc[-1]),
        "cost_contributions_dkk": contributions,
        "illustrative_settlement": settlements,
        "assumptions": config,
        "warnings": warnings,
    }
    summary["absolute_optimality_gap_dkk"] = abs(
        summary["objective_dkk"] - summary["mip_dual_bound_dkk"]
    )
    if config["objective"] == "system":
        up = config["upstream"]
        fuel_cost = sum(
            float((dispatch[p.name + "_fuel_mw"] * p.fuel_dkk_mwh).sum())
            for p in model.plants.itertuples()
        )
        fuel_cost += sum(
            float(
                dispatch[f + "_boiler_heat_mw"].sum()
                / up[f + "_efficiency"]
                * up[f + "_dkk_mwh_fuel"]
            )
            for f in ["gas", "oil", "bio"]
        )
        upstream_el = (
            dispatch.electric_boiler_heat_mw / up["electric_efficiency"]
            + dispatch.regional_hp_heat_mw / up["heat_pump_cop"]
        )
        local_el = dispatch.local_hp_electricity_mw + dispatch.ptes_pump_electricity_mw
        power = sum(dispatch[p + "_power_mw"] for p in model.plants.name)
        power += dispatch.waste_heat_mw * up["waste_power_heat_ratio"]
        variable_cost = sum(
            float((dispatch[p.name + "_heat_mw"] * p.vom_dkk_mwh_heat).sum())
            for p in model.plants.itertuples()
        )
        variable_cost += sum(
            float(dispatch[f + "_boiler_heat_mw"].sum() * up["boiler_vom_dkk_mwh"])
            for f in ["gas", "oil", "bio", "electric"]
        )
        variable_cost += float(dispatch.waste_heat_mw.sum() * up["waste_vom_dkk_mwh_heat"])
        summary["operating_cost_breakdown_dkk"] = {
            "fuel": fuel_cost,
            "variable_om": variable_cost,
            "electricity_spot_imports": float(
                ((upstream_el + local_el) * dispatch.electricity_dkk_mwh).sum()
            ),
            "electricity_adders": float(
                (
                    upstream_el * up["electricity_adder_dkk_mwh"]
                    + local_el * hp["electricity_adder_dkk_mwh"]
                ).sum()
            ),
            "hp_startups": float(starts),
            "electricity_sales_credit": -float((power * dispatch.electricity_dkk_mwh).sum()),
        }
        summary["waste_unused_availability_mwh"] = float(
            (
                np.minimum(dispatch.waste_available_mw, config["upstream"]["waste_capacity_mw"])
                - dispatch.waste_heat_mw
            ).sum()
        )
        summary["regional_accumulator_simultaneous_hours"] = {
            name: int(
                (
                    (dispatch[name + "_charge_mw"] > 1e-6)
                    & (dispatch[name + "_discharge_mw"] > 1e-6)
                ).sum()
            )
            for name in config["upstream"]["accumulators"]
        }
    if prices:
        if config["objective"] != "system":
            raise ValueError("Upstream marginal values require the system objective")
        dispatch["conditional_upstream_value_dkk_mwh"] = conditional_prices(model, result)
        summary["price_method"] = "LP regional-balance dual with all integer decisions fixed"
    return Solution(dispatch, summary, result)
