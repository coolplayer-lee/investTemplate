# -*- coding: utf-8 -*-
"""按V2.1规则和2026-09-01双周锚点重建VIX定投历史。"""

import csv
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import auto_update_vix_dca as engine


ROOT = Path(__file__).resolve().parents[1]
STRATEGY_DIR = ROOT / "decision-tracking" / "vix_dca_strategy"
PUBLIC_DIR = ROOT / "public" / "vix_strategy"
CONFIG_FILE = STRATEGY_DIR / "strategy_config.json"

ANCHOR_DATE = "2026-09-01"
START_DATE = "2026-03-31"
LATEST_DATE = "2026-09-01"
NEXT_TRADE_DATE = "2026-09-15"

# VIX为定投日前一个美股交易日的Cboe收盘值；ETF为定投日513110收盘价。
# VIX: https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv
# ETF: Yahoo Finance 513110.SS历史行情。数据核对日期：2026-09-04。
TRADE_DAYS = [
    {"date": "2026-03-31", "vix_date": "2026-03-30", "vix": 30.61, "price": 1.887},
    {"date": "2026-04-14", "vix_date": "2026-04-13", "vix": 19.12, "price": 2.064},
    {"date": "2026-04-28", "vix_date": "2026-04-27", "vix": 18.02, "price": 2.197},
    {"date": "2026-05-12", "vix_date": "2026-05-11", "vix": 18.38, "price": 2.348},
    {"date": "2026-05-26", "vix_date": "2026-05-25", "vix": 16.59, "price": 2.442},
    {"date": "2026-06-09", "vix_date": "2026-06-08", "vix": 18.92, "price": 2.456},
    {"date": "2026-06-23", "vix_date": "2026-06-22", "vix": 17.28, "price": 2.454},
    {"date": "2026-07-07", "vix_date": "2026-07-06", "vix": 15.57, "price": 2.438},
    {"date": "2026-07-21", "vix_date": "2026-07-20", "vix": 18.65, "price": 2.396},
    {"date": "2026-08-04", "vix_date": "2026-08-03", "vix": 15.86, "price": 2.444},
    {"date": "2026-08-18", "vix_date": "2026-08-17", "vix": 15.19, "price": 2.510},
    {"date": "2026-09-01", "vix_date": "2026-08-31", "vix": 14.92, "price": 2.487},
]


def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def money(value):
    """按财务展示口径四舍五入到分，规避二进制浮点的0.005边界。"""
    epsilon = 1e-9 if value >= 0 else -1e-9
    return round(value + epsilon, 2)


def build_history(config):
    trades = []
    returns = []
    snapshots = []
    shares = 0
    total_cost = 0.0
    cumulative_buy = 0.0
    cash = 0.0
    previous_unrealized = 0.0

    for item in TRADE_DAYS:
        amount, label = engine.get_base_buy_amount(item["vix"], config)
        fee = max(0.01, amount * 0.0001)
        bought_shares = int((amount - fee) / item["price"])
        transaction_cost = bought_shares * item["price"] + fee
        shares += bought_shares
        total_cost += transaction_cost
        cumulative_buy += amount
        cash_before = cash
        cash += amount - transaction_cost

        market_value = shares * item["price"]
        net_value = market_value + cash
        unrealized = market_value - total_cost
        daily_pnl = unrealized - previous_unrealized
        return_pct = unrealized / total_cost * 100
        total_return_pct = (net_value - cumulative_buy) / cumulative_buy * 100
        note = f"V2.1定投；VIX数据日{item['vix_date']}"

        trade = {
            "date": item["date"],
            "vix": item["vix"],
            "vix_zone": engine.get_vix_zone(item["vix"]),
            "action": "BUY",
            "amount": amount,
            "shares": bought_shares,
            "price": item["price"],
            "fee": round(fee, 3),
            "total_cost": amount,
            "cash_before": money(cash_before),
            "cash_after": money(cash),
            "net_value": money(net_value),
            "label": label,
        }
        trades.append(trade)

        returns.append({
            "date": item["date"],
            "vix": item["vix"],
            "price": item["price"],
            "shares": shares,
            "avg_cost": round(total_cost / shares, 4),
            "market_value": money(market_value),
            "total_cost": money(total_cost),
            "unrealized_pnl": money(unrealized),
            "daily_pnl": money(daily_pnl),
            "return_pct": round(return_pct, 2),
            "total_return_pct": round(total_return_pct, 2),
            "cash": money(cash),
            "net_value": money(net_value),
            "note": note,
        })
        snapshots.append({
            "date": item["date"],
            "vix": item["vix"],
            "price": item["price"],
            "shares": shares,
            "position_value": money(market_value),
            "cash": money(cash),
            "net_value": money(net_value),
            "total_cost": money(total_cost),
            "unrealized_pnl": money(unrealized),
            "daily_pnl": money(daily_pnl),
            "return_pct": round(return_pct, 2),
            "note": note,
        })
        previous_unrealized = unrealized

    return trades, returns, snapshots


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    trades, returns, snapshots = build_history(config)
    latest = returns[-1]
    cumulative_buy = sum(t["amount"] for t in trades)
    upcoming = [
        (datetime.strptime(NEXT_TRADE_DATE, "%Y-%m-%d") + timedelta(days=14 * i)).strftime("%Y-%m-%d")
        for i in range(5)
    ]

    state = {
        "strategy": {
            "name": "VIX定投策略_纳指100",
            "version": "V2.1",
            "rules_effective_date": START_DATE,
            "start_date": START_DATE,
            "note": "历史已按V2.1规则和2026-09-01双周锚点重算",
            "etf_code": "513110",
            "etf_name": "纳斯达克100 ETF",
            "execution_frequency": "每两周周二执行一次（只买不卖）",
            "execution_anchor_date": ANCHOR_DATE,
            "update_frequency": "仅保留双周定投日快照",
        },
        "account": {
            "initial_capital": 100000,
            "capital_mode": "dca",
            "currency": "CNY",
            "cash": latest["cash"],
            "last_update": LATEST_DATE,
        },
        "position": {
            "shares": latest["shares"],
            "avg_cost": latest["total_cost"] / latest["shares"],
            "total_cost": latest["total_cost"],
            "current_price": latest["price"],
            "market_value": latest["market_value"],
            "unrealized_pnl": latest["unrealized_pnl"],
            "return_pct": latest["return_pct"],
        },
        "daily_performance": {
            "date": LATEST_DATE,
            "vix": latest["vix"],
            "daily_pnl": latest["daily_pnl"],
            "total_pnl": latest["unrealized_pnl"],
            "total_return_pct": latest["total_return_pct"],
        },
        "statistics": {
            "cumulative_buy": cumulative_buy,
            "cumulative_sell": 0,
            "trade_count": len(trades),
            "buy_count": len(trades),
            "sell_count": 0,
            "total_invested": cumulative_buy,
            "hold_days": (datetime.fromisoformat(LATEST_DATE) - datetime.fromisoformat(START_DATE)).days + 1,
            "last_trade_date": LATEST_DATE,
            "next_trade_date": NEXT_TRADE_DATE,
        },
        "schedule": {
            "frequency": "每双周周二",
            "anchor_date": ANCHOR_DATE,
            "upcoming_trade_dates": upcoming,
            "next_trade_date": NEXT_TRADE_DATE,
        },
        "history": {
            "vix_high": max(t["vix"] for t in trades),
            "vix_high_date": max(trades, key=lambda t: t["vix"])["date"],
            "vix_low": min(t["vix"] for t in trades),
            "vix_low_date": min(trades, key=lambda t: t["vix"])["date"],
            "max_unrealized_pnl": max(r["unrealized_pnl"] for r in returns),
            "max_unrealized_date": max(returns, key=lambda r: r["unrealized_pnl"])["date"],
        },
        "strategy_state": {
            "vix_based_selling_enabled": False,
            "single_period_buy_cap": 10000,
            "biweekly_vix_log": [{"date": t["date"], "vix": t["vix"]} for t in trades],
        },
    }

    dashboard_trades = [
        {key: trade[key] for key in ("date", "vix", "action", "amount", "shares", "price", "label")}
        for trade in reversed(trades[-10:])
    ]
    dashboard = {
        "strategy": "VIX定投策略_纳指100",
        "version": "V2.1",
        "last_update": LATEST_DATE,
        "account": {
            "initial_capital": cumulative_buy,
            "cash": latest["cash"],
            "total_assets": latest["net_value"],
        },
        "position": {
            "etf_code": "513110", "etf_name": "纳斯达克100 ETF", "shares": latest["shares"],
            "avg_cost": round(latest["total_cost"] / latest["shares"], 3),
            "current_price": latest["price"], "market_value": latest["market_value"],
            "total_cost": latest["total_cost"], "unrealized_pnl": latest["unrealized_pnl"],
            "return_pct": latest["return_pct"],
        },
        "performance": {
            "total_pnl": latest["unrealized_pnl"], "total_return_pct": latest["total_return_pct"],
            "daily_pnl": latest["daily_pnl"], "vix": latest["vix"], "date": LATEST_DATE,
        },
        "schedule": {
            "frequency": "每双周周二", "last_trade_date": LATEST_DATE,
            "next_trade_date": NEXT_TRADE_DATE, "days_until_next": 14,
        },
        "recent_trades": dashboard_trades,
        "daily_snapshots": [
            {
                "date": r["date"], "price": r["price"], "pnl": r["unrealized_pnl"],
                "daily_pnl": r["daily_pnl"], "total_return_pct": r["total_return_pct"],
            }
            for r in reversed(returns[-10:])
        ],
        "strategy_version": "V2.1",
        "strategy_state": {"vix_based_selling_enabled": False, "single_period_buy_cap": 10000},
    }

    save_json(STRATEGY_DIR / "state.json", state)
    save_json(STRATEGY_DIR / "dashboard_data.json", dashboard)
    save_json(PUBLIC_DIR / "dashboard_data.json", dashboard)
    write_csv(STRATEGY_DIR / "trades.csv", trades)
    write_csv(STRATEGY_DIR / "daily_returns.csv", returns)
    write_csv(STRATEGY_DIR / "daily_snapshot.csv", snapshots)
    shutil.copy2(STRATEGY_DIR / "daily_returns.csv", PUBLIC_DIR / "daily_returns.csv")

    engine.generate_returns_curve_svg(engine.RETURNS_CURVE_SVG, engine.load_daily_returns())
    engine.generate_returns_curve_html(engine.RETURNS_CURVE_HTML, engine.load_daily_returns_full())
    engine.update_markdown_template(state, LATEST_DATE, latest["vix"], latest["price"])
    engine.sync_to_public(state, dashboard)

    print(f"V2.1历史重建完成：{len(trades)}期，累计投入{cumulative_buy:,.0f}元")
    print(f"持仓{latest['shares']:,}份，市值{latest['market_value']:,.2f}元，总收益率{latest['total_return_pct']:+.2f}%")
    print(f"下次定投：{NEXT_TRADE_DATE}")


if __name__ == "__main__":
    main()
