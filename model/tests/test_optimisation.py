import numpy as np
import pytest

from cph_dispatch.data import demo
from cph_dispatch.optimisation import build, conditional_prices, solve


def test_dispatch_physics_and_accounting(config, plants):
    frame = demo(72)
    config["solver"]["mip_rel_gap"] = 0.0001
    result = solve(build(frame, config, plants), prices=True)
    d = result.dispatch
    np.testing.assert_allclose(
        d.hx_mw + d.ptes_discharge_mw + d.city2_heat_mw + d.groundwater_heat_mw,
        d.htf_demand_mw,
        atol=1e-6,
    )
    previous = np.r_[config["ptes"]["initial_mwh"], d.ptes_energy_mwh.iloc[:-1]]
    np.testing.assert_allclose(
        d.ptes_energy_mwh,
        previous * (1 - config["ptes"]["loss_per_hour"]) + d.ptes_charge_mw - d.ptes_discharge_mw,
        atol=1e-6,
    )
    assert d.ptes_energy_mwh.iloc[-1] == pytest.approx(config["ptes"]["terminal_mwh"])
    assert (d.ptes_charge_mw * d.ptes_discharge_mw).abs().max() < 1e-6
    for name in ["AMV", "AVV"]:
        spec = config["upstream"]["accumulators"][name]
        assert d[name + "_energy_mwh"].iloc[-1] == pytest.approx(spec["energy_mwh"] / 2)
        assert (d[name + "_charge_mw"] + d[name + "_discharge_mw"]).max() <= spec["power_mw"] + 1e-6
    for name in ["city2", "groundwater"]:
        on = d[name + "_on"].round().astype(int).to_numpy()
        starts = d[name + "_start"].round().astype(int).to_numpy()
        stops = d[name + "_stop"].round().astype(int).to_numpy()
        np.testing.assert_array_equal(on - np.r_[0, on[:-1]], starts - stops)
        for t in np.flatnonzero(starts):
            assert np.all(on[t : t + 2] == 1)
        for t in np.flatnonzero(stops):
            assert np.all(on[t : t + 2] == 0)
    for column, minimum in [("ptes_charge_mw", 10), ("ptes_discharge_mw", 5)]:
        flow = d[column].to_numpy()
        assert np.all((flow < 1e-6) | (flow >= minimum - 1e-6))
        assert np.abs(np.diff(np.r_[0, flow])).max() <= 12 + 1e-6
        assert flow.max() <= 23 + 1e-6
    for lag in [1, 2]:
        assert np.all(
            d.ptes_charge_on.to_numpy()[:-lag] + d.ptes_discharge_on.to_numpy()[lag:] < 1.00001
        )
        assert np.all(
            d.ptes_discharge_on.to_numpy()[:-lag] + d.ptes_charge_on.to_numpy()[lag:] < 1.00001
        )
    for plant in plants.itertuples():
        q, p, f = [d[plant.name + s] for s in ["_heat_mw", "_power_mw", "_fuel_mw"]]
        assert f.max() <= plant.fuel_mw * plant.availability + 1e-6
        if plant.kind == "backpressure":
            b = d[plant.name + "_bypass_mw"]
            np.testing.assert_allclose(q, p / plant.cm + b, atol=1e-6)
            np.testing.assert_allclose(f, p / plant.eta_el + b / plant.eta_bypass, atol=1e-6)
        else:
            assert (p + plant.cv * q - plant.eta_el * f).max() <= 1e-6
            assert (plant.cm * q - p).max() <= 1e-6
    q_chp = sum(d[p + "_heat_mw"] for p in plants.name)
    q_peak = sum(d[f + "_boiler_heat_mw"] for f in ["gas", "oil", "bio", "electric"])
    q_store = sum(d[s + "_discharge_mw"] - d[s + "_charge_mw"] for s in ["AMV", "AVV"])
    np.testing.assert_allclose(
        q_chp + q_peak + q_store + d.waste_heat_mw + d.regional_hp_heat_mw,
        (d.regional_demand_mw - d.htf_demand_mw + d.hx_mw + d.ptes_charge_mw)
        / (1 - config["network_loss_fraction"]),
        atol=1e-6,
    )
    assert sum(result.summary["cost_contributions_dkk"].values()) == pytest.approx(result.raw.fun)
    assert sum(result.summary["operating_cost_breakdown_dkk"].values()) == pytest.approx(
        result.raw.fun
    )
    settlement = result.summary["illustrative_settlement"]
    assert settlement["heat_purchase_dkk"] - settlement["discharge_credit_dkk"] == pytest.approx(
        settlement["supplier_local_heat_revenue_dkk"]
    )


def test_thermal_capacity_with_changing_cop(config, plants):
    frame = demo(24)
    frame["electricity_dkk_mwh"] = -1000
    frame["city2_cop"] = np.linspace(2, 6, len(frame))
    config["objective"] = "local"
    config["settlement_boundary"] = "legacy_owned_store"
    d = solve(build(frame, config, plants)).dispatch
    assert d.city2_heat_mw.max() <= 1.34 + 1e-7
    np.testing.assert_allclose(
        d.local_hp_electricity_mw,
        d.city2_heat_mw / d.city2_cop + d.groundwater_heat_mw / d.groundwater_cop,
    )


def test_prices_match_fixed_commitment_demand_perturbation(config, plants):
    frame = demo(24)
    model = build(frame, config, plants)
    result = solve(model)
    dual = conditional_prices(model, result.raw)
    for i, is_integer in enumerate(model.integer):
        if is_integer:
            model.lower[i] = model.upper[i] = float(round(result.raw.x[i]))
    model.integer = [0] * len(model.integer)
    fixed = solve(model)
    row = np.flatnonzero(np.array(model.row_names) == "regional_heat_balance")[8]
    change = 0.001 / (1 - config["network_loss_fraction"])
    model.row_lower[row] += change
    model.row_upper[row] += change
    model.inputs.iloc[8, model.inputs.columns.get_loc("regional_demand_mw")] += 0.001
    second = solve(model)
    # Demand is delivered heat; the balance dual is per unit of upstream heat.
    assert (second.raw.fun - fixed.raw.fun) / 0.001 == pytest.approx(
        dual[8] / (1 - config["network_loss_fraction"]), rel=1e-4
    )


def test_endogenous_price_response(config, plants):
    config["objective"] = "local"
    config["settlement_boundary"] = "legacy_owned_store"
    frame = demo(72)
    frame["reference_tariff_dkk_mwh"] = np.tile(np.r_[np.full(12, 100), np.full(12, 600)], 3)
    baseline = solve(build(frame, config, plants))
    config["ptes"]["power_mw"] = 0.001
    config["ptes"]["min_charge_mw"] = 0
    config["ptes"]["min_discharge_mw"] = 0
    config["ptes"]["loss_per_hour"] = 0
    without = solve(build(frame, config, plants))
    assert baseline.dispatch.ptes_discharge_mw.sum() > 100
    assert baseline.raw.fun < without.raw.fun


def test_failure_is_explicit(config, plants):
    frame = demo(24)
    frame["htf_demand_mw"] = 500
    with pytest.raises(RuntimeError, match="No accepted solution"):
        solve(build(frame, config, plants))
    frame["regional_demand_mw"] = 1
    with pytest.raises(ValueError, match="Regional demand smaller"):
        build(frame, config, plants)


def test_discharge_credit_is_transfer_not_resource_cost(config, plants):
    frame = demo(24)
    base = solve(build(frame, config, plants))
    config["discharge_discount_dkk_mwh"] = 100
    second = solve(build(frame, config, plants))
    assert base.raw.fun == pytest.approx(second.raw.fun)
    assert second.summary["illustrative_settlement"]["discharge_credit_dkk"] == pytest.approx(
        second.dispatch.ptes_discharge_mw.sum() * 100
    )


def test_discharge_boundary_charging_schedule_and_bill(config, plants):
    frame = demo(48)
    central = solve(build(frame, config, plants))
    config["objective"] = "local"
    with pytest.raises(ValueError, match="charging schedule"):
        build(frame, config, plants)
    frame["scheduled_ptes_charge_mw"] = central.dispatch.ptes_charge_mw
    config["discharge_discount_dkk_mwh"] = 50
    local = solve(build(frame, config, plants))
    d = local.dispatch
    np.testing.assert_allclose(d.ptes_charge_mw, frame.scheduled_ptes_charge_mw, atol=1e-6)
    bill = (
        (d.hx_mw + d.ptes_discharge_mw) * d.reference_tariff_dkk_mwh - 50 * d.ptes_discharge_mw
    ).sum()
    s = local.summary["illustrative_settlement"]
    assert s["supplier_local_heat_revenue_dkk"] == pytest.approx(bill)
    assert local.raw.fun == pytest.approx(s["local_expenditure_dkk"])


def test_optional_gurobi_matches_highs(config, plants):
    pytest.importorskip("gurobipy")
    frame = demo(24)
    config["solver"]["mip_rel_gap"] = 1e-8
    highs = solve(build(frame, config, plants), prices=True)
    config["solver"]["backend"] = "gurobi"
    gurobi = solve(build(frame, config, plants), prices=True)
    assert gurobi.raw.fun == pytest.approx(highs.raw.fun, rel=1e-7)
    assert np.isfinite(gurobi.dispatch.conditional_upstream_value_dkk_mwh).all()
