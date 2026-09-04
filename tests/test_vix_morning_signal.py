from datetime import date

from scripts.generate_vix_morning_signal import build_signal


CONFIG = {
    "version": "V2.1",
    "buy_rules": {
        "base_tiers": [
            {"vix_min": 0, "vix_max": 15, "amount": 4000, "label": "低波动"},
            {"vix_min": 15, "vix_max": 20, "amount": 5000, "label": "常规定投"},
            {"vix_min": 20, "vix_max": 25, "amount": 6000, "label": "温和加仓"},
            {"vix_min": 25, "vix_max": 30, "amount": 8000, "label": "明显恐慌加仓"},
            {"vix_min": 30, "vix_max": 999, "amount": 10000, "label": "极端恐慌封顶"},
        ]
    },
}


def state_for(next_trade_date):
    return {"schedule": {"next_trade_date": next_trade_date}}


def snapshot(vix, market_date, fallback=False):
    return {
        "value": vix,
        "market_date": market_date,
        "source": "test",
        "fallback": fallback,
    }


def test_non_trade_day_only_displays_reference_amount():
    signal = build_signal(
        date(2026, 9, 4), snapshot(15.42, "2026-09-03"), state_for("2026-09-08"), CONFIG
    )
    assert signal["action_code"] == "HOLD"
    assert signal["action_amount"] == 0
    assert signal["reference_amount"] == 5000


def test_trade_day_uses_fixed_vix_tier():
    signal = build_signal(
        date(2026, 9, 8), snapshot(26, "2026-09-07"), state_for("2026-09-08"), CONFIG
    )
    assert signal["action_code"] == "BUY"
    assert signal["action_amount"] == 8000


def test_trade_day_blocks_stale_or_fallback_data():
    stale = build_signal(
        date(2026, 9, 8), snapshot(26, "2026-09-01"), state_for("2026-09-08"), CONFIG
    )
    fallback = build_signal(
        date(2026, 9, 8), snapshot(26, "2026-09-07", True), state_for("2026-09-08"), CONFIG
    )
    assert stale["action_code"] == "VERIFY_DATA"
    assert fallback["action_code"] == "VERIFY_DATA"
    assert stale["action_amount"] == fallback["action_amount"] == 0
