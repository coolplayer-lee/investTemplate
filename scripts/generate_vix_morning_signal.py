# -*- coding: utf-8 -*-
"""Generate the pre-market VIX action card used by the strategy page."""

import argparse
import csv
import html
import io
import json
import shutil
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

try:
    from auto_update_vix_dca import (
        get_base_buy_amount,
        get_vix_from_investing,
        get_vix_from_yfinance,
    )
except ImportError:
    from scripts.auto_update_vix_dca import (
        get_base_buy_amount,
        get_vix_from_investing,
        get_vix_from_yfinance,
    )


ROOT = Path(__file__).resolve().parents[1]
STRATEGY_DIR = ROOT / "decision-tracking" / "vix_dca_strategy"
PUBLIC_DIR = ROOT / "public" / "vix_strategy"
CONFIG_FILE = STRATEGY_DIR / "strategy_config.json"
STATE_FILE = STRATEGY_DIR / "state.json"
SIGNAL_FILE = STRATEGY_DIR / "today_signal.json"
SIGNAL_HTML_FILE = STRATEGY_DIR / "today_signal.html"
BEIJING_TZ = timezone(timedelta(hours=8))


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def business_day_age(market_date, signal_date):
    """Count weekdays after the market date through the signal date."""
    current = market_date + timedelta(days=1)
    count = 0
    while current <= signal_date:
        if current.weekday() < 5:
            count += 1
        current += timedelta(days=1)
    return count


def fetch_vix_snapshot():
    """Prefer dated closes; use an undated page quote only as a fallback."""
    try:
        request = urllib.request.Request(
            "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv",
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            rows = list(csv.DictReader(io.StringIO(response.read().decode("utf-8-sig"))))
        if rows:
            latest = rows[-1]
            market_date = datetime.strptime(latest["DATE"], "%m/%d/%Y").date()
            return {
                "value": float(latest["CLOSE"]),
                "market_date": market_date.isoformat(),
                "source": "Cboe VIX历史收盘数据",
                "fallback": False,
            }
    except Exception as error:
        print(f"[VIX] Cboe获取失败: {error}")

    result = get_vix_from_yfinance()
    if result:
        return {
            "value": float(result["value"]),
            "market_date": str(result["date"]),
            "source": "Yahoo Finance (^VIX)",
            "fallback": False,
        }

    result = get_vix_from_investing()
    if result:
        return {
            "value": float(result["value"]),
            "market_date": str(result["date"]),
            "source": "Investing.com",
            "fallback": True,
        }
    return None


def resolve_next_trade_date(state):
    return (
        state.get("schedule", {}).get("next_trade_date")
        or state.get("statistics", {}).get("next_trade_date")
    )


def build_signal(signal_date, snapshot, state, config):
    next_trade_date = resolve_next_trade_date(state)
    weekend = signal_date.weekday() >= 5
    scheduled_today = not weekend and next_trade_date == signal_date.isoformat()

    if snapshot:
        vix = float(snapshot["value"])
        market_date = date.fromisoformat(snapshot["market_date"])
        age = business_day_age(market_date, signal_date)
        data_status = "fallback" if snapshot.get("fallback") else "fresh"
        if market_date > signal_date or age > 2:
            data_status = "stale"
        source = snapshot["source"]
        amount, tier_label = get_base_buy_amount(vix, config)
    else:
        perf = state.get("daily_performance", {})
        vix = float(perf.get("vix", 0) or 0)
        market_date_text = perf.get("date")
        market_date = date.fromisoformat(market_date_text) if market_date_text else None
        age = business_day_age(market_date, signal_date) if market_date else None
        data_status = "stale"
        source = "本地历史状态（自动数据获取失败）"
        amount, tier_label = get_base_buy_amount(vix, config) if vix > 0 else (0, "数据缺失")

    if weekend:
        action_code = "HOLD"
        action_text = "今日周末休市，无需操作"
        action_amount = 0
        tone = "normal"
    elif data_status != "fresh" and scheduled_today:
        action_code = "VERIFY_DATA"
        action_text = "VIX数据需要核对，暂不操作"
        action_amount = 0
        tone = "warning"
    elif scheduled_today:
        action_code = "BUY"
        action_text = f"今日定投：买入513110，计划金额{amount:,}元"
        action_amount = amount
        tone = "action"
    else:
        action_code = "HOLD"
        action_text = "今天不是定投日，无需操作"
        action_amount = 0
        tone = "normal"

    return {
        "schema_version": 1,
        "strategy_version": config.get("version", "V2.1"),
        "signal_date": signal_date.isoformat(),
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "vix": round(vix, 2),
        "vix_market_date": market_date.isoformat() if market_date else None,
        "vix_source": source,
        "data_status": data_status,
        "business_day_age": age,
        "tier": tier_label,
        "scheduled_trade_day": scheduled_today,
        "action_code": action_code,
        "action_text": action_text,
        "action_amount": action_amount,
        "reference_amount": amount,
        "next_trade_date": next_trade_date,
        "tone": tone,
        "note": "参考美国上一交易日VIX收盘值；实盘下单前检查513110溢价并使用限价单。",
    }


def render_html(signal):
    tone_colors = {
        "normal": ("#eff6ff", "#1d4ed8", "#bfdbfe"),
        "action": ("#ecfdf5", "#047857", "#a7f3d0"),
        "warning": ("#fff7ed", "#c2410c", "#fed7aa"),
    }
    background, accent, border = tone_colors[signal["tone"]]
    status_text = {
        "fresh": "数据正常",
        "fallback": "备用数据源",
        "stale": "数据需核对",
    }[signal["data_status"]]
    next_trade = signal["next_trade_date"] or "待确定"
    reference = f'{signal["reference_amount"]:,}元'

    def esc(value):
        return html.escape(str(value))

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>VIX今日操作</title>
<style>
*{{box-sizing:border-box}} body{{margin:0;padding:12px;background:transparent;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif;color:#111827}}
.card{{border:1px solid {border};background:{background};border-radius:14px;padding:20px;box-shadow:0 4px 16px rgba(15,23,42,.06)}}
.top{{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;flex-wrap:wrap}} h2{{font-size:18px;margin:0 0 8px}} .action{{font-size:22px;font-weight:750;color:{accent};margin:0}}
.badge{{padding:5px 10px;border-radius:999px;border:1px solid {border};color:{accent};font-size:13px;font-weight:650;background:#fff9}}
.grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:18px}} .item{{background:#fff9;border:1px solid {border};border-radius:10px;padding:12px}}
.label{{font-size:12px;color:#6b7280;margin-bottom:5px}} .value{{font-size:17px;font-weight:700}} .foot{{font-size:12px;color:#6b7280;margin:14px 0 0;line-height:1.6}}
@media(max-width:680px){{.grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}.action{{font-size:19px}}}}
</style>
</head>
<body>
<section class="card">
  <div class="top">
    <div><h2 id="signal-title">VIX今日操作 · {esc(signal['signal_date'])}</h2><p class="action">{esc(signal['action_text'])}</p></div>
    <span class="badge">{esc(status_text)}</span>
  </div>
  <div class="grid">
    <div class="item"><div class="label">最新VIX</div><div class="value">{signal['vix']:.2f}</div></div>
    <div class="item"><div class="label">当前档位</div><div class="value">{esc(signal['tier'])}</div></div>
    <div class="item"><div class="label">当前档位金额</div><div class="value">{esc(reference)}</div></div>
    <div class="item"><div class="label">下次定投</div><div class="value">{esc(next_trade)}</div></div>
  </div>
  <p class="foot">VIX数据日：{esc(signal['vix_market_date'] or '未知')} · 来源：{esc(signal['vix_source'])}<br>{esc(signal['note'])}</p>
  <p class="foot" id="signal-freshness">提示生成日：{esc(signal['signal_date'])}（北京时间）</p>
</section>
<script>
const signalDate = {json.dumps(signal['signal_date'])};
function refreshDisplay() {{
  const parts = new Intl.DateTimeFormat('en-US', {{
    timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit'
  }}).formatToParts(new Date());
  const fields = Object.fromEntries(parts.map(part => [part.type, part.value]));
  const today = `${{fields.year}}-${{fields.month}}-${{fields.day}}`;
  if (today === signalDate) return;
  const weekend = [0, 6].includes(new Date(today + 'T00:00:00Z').getUTCDay());
  document.getElementById('signal-title').textContent = 'VIX今日操作 · ' + today;
  document.querySelector('.action').textContent = weekend
    ? '今日周末休市，无需操作'
    : '今日操作提示尚未更新，请等待更新后核对';
  document.querySelector('.badge').textContent = weekend ? '周末休市' : '提示待更新';
  document.getElementById('signal-freshness').textContent =
    '上次提示生成日：' + signalDate + '（北京时间）；以上行情与档位仅供历史参考。';
  document.querySelector('.action').style.color = '#c2410c';
}}
refreshDisplay();
setInterval(refreshDisplay, 60000);
document.addEventListener('visibilitychange', refreshDisplay);
</script>
</body>
</html>
"""


def save_outputs(signal):
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    SIGNAL_FILE.write_text(json.dumps(signal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    SIGNAL_HTML_FILE.write_text(render_html(signal), encoding="utf-8", newline="\n")
    shutil.copy2(SIGNAL_FILE, PUBLIC_DIR / SIGNAL_FILE.name)
    shutil.copy2(SIGNAL_HTML_FILE, PUBLIC_DIR / SIGNAL_HTML_FILE.name)


def main():
    parser = argparse.ArgumentParser(description="生成VIX早盘操作提示")
    parser.add_argument("--date", help="信号日期 YYYY-MM-DD，默认今天")
    parser.add_argument("--vix", type=float, help="手动指定VIX")
    parser.add_argument("--vix-date", help="手动指定VIX对应的市场日期")
    parser.add_argument("--source", default="manual", help="手动数据来源标签")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    signal_date = date.fromisoformat(args.date) if args.date else datetime.now(BEIJING_TZ).date()
    if args.vix is not None:
        snapshot = {
            "value": args.vix,
            "market_date": args.vix_date or signal_date.isoformat(),
            "source": args.source,
            "fallback": False,
        }
    else:
        snapshot = fetch_vix_snapshot()

    signal = build_signal(
        signal_date,
        snapshot,
        load_json(STATE_FILE),
        load_json(CONFIG_FILE),
    )
    print(json.dumps(signal, ensure_ascii=False, indent=2))
    if not args.dry_run:
        save_outputs(signal)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
