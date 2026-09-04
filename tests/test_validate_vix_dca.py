from scripts.validate_vix_dca import build_cumulative_buy_history


def test_cumulative_buy_history_uses_complete_ledger():
    rows = [
        {"date": "2026-03-24"},
        {"date": "2026-04-07"},
        {"date": "2026-04-08"},
    ]
    trades = [
        {"date": "2026-03-24", "action": "BUY", "amount": "3000"},
        {"date": "2026-04-07", "action": "BUY", "amount": "1500"},
    ]

    assert build_cumulative_buy_history(rows, trades) == {
        "2026-03-24": 3000.0,
        "2026-04-07": 4500.0,
        "2026-04-08": 4500.0,
    }


def test_cumulative_buy_history_ignores_sells():
    rows = [{"date": "2026-03-24"}, {"date": "2026-04-07"}]
    trades = [
        {"date": "2026-03-24", "action": "BUY", "amount": "3000"},
        {"date": "2026-04-07", "action": "SELL", "amount": "500"},
    ]

    history = build_cumulative_buy_history(rows, trades)
    assert history["2026-04-07"] == 3000.0
