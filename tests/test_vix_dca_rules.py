import importlib.util
import csv
import json
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "decision-tracking" / "vix_dca_strategy" / "strategy_config.json"
SCRIPT_PATH = ROOT / "scripts" / "auto_update_vix_dca.py"


def load_strategy_module():
    spec = importlib.util.spec_from_file_location("auto_update_vix_dca", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_v21_vix_tier_boundaries():
    module = load_strategy_module()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    cases = [
        (0, 4000),
        (14.99, 4000),
        (15, 5000),
        (19.99, 5000),
        (20, 6000),
        (24.99, 6000),
        (25, 8000),
        (29.99, 8000),
        (30, 10000),
        (80, 10000),
    ]

    for vix, expected_amount in cases:
        amount, _ = module.get_base_buy_amount(vix, config)
        assert amount == expected_amount


def test_v21_has_no_vix_sell_or_tactical_overlays():
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    assert config["version"] == "V2.1"
    assert "sell_rules" not in config
    assert "trend_adjustment" not in config["buy_rules"]
    assert "extreme_risk_control" not in config["buy_rules"]
    assert "reflow_rules" not in config
    assert "emergency_buy" not in config
    assert config["execution_frequency"]["anchor_date"] == "2026-09-01"
    assert config["history_policy"]["trade_days_only"] is True


def test_v21_extreme_vix_buys_instead_of_selling():
    module = load_strategy_module()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    state = json.loads(
        (CONFIG_PATH.parent / "state.json").read_text(encoding="utf-8")
    )
    before_shares = state["position"]["shares"]
    updated_state = deepcopy(state)

    _, trade_infos, _ = module.update_state(
        updated_state, config, "2026-09-15", 40, 2.50, True
    )

    assert len(trade_infos) == 1
    assert trade_infos[0]["action"] == "BUY"
    assert trade_infos[0]["amount"] == 10000
    assert trade_infos[0]["shares"] > 0
    assert updated_state["position"]["shares"] > before_shares


def test_rebased_history_contains_only_new_biweekly_dates():
    strategy_dir = CONFIG_PATH.parent
    with (strategy_dir / "trades.csv").open(encoding="utf-8", newline="") as handle:
        trades = list(csv.DictReader(handle))
    with (strategy_dir / "daily_returns.csv").open(encoding="utf-8", newline="") as handle:
        returns = list(csv.DictReader(handle))

    expected_dates = [
        "2026-03-31", "2026-04-14", "2026-04-28", "2026-05-12",
        "2026-05-26", "2026-06-09", "2026-06-23", "2026-07-07",
        "2026-07-21", "2026-08-04", "2026-08-18", "2026-09-01",
    ]
    assert [row["date"] for row in trades] == expected_dates
    assert [row["date"] for row in returns] == expected_dates
    assert sum(float(row["amount"]) for row in trades) == 64000
