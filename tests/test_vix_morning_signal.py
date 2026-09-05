from datetime import date

import json
import re
import shutil
import subprocess

import pytest

from scripts.generate_vix_morning_signal import build_signal, render_html


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


@pytest.mark.parametrize("day", [5, 6])
def test_weekend_never_suggests_buy_even_with_matching_schedule(day):
    today = date(2026, 9, day)
    signal = build_signal(
        today, snapshot(26, "2026-09-04"), state_for(today.isoformat()), CONFIG
    )
    assert signal["action_code"] == "HOLD"
    assert signal["action_amount"] == 0
    assert not signal["scheduled_trade_day"]
    assert signal["action_text"] == "今日周末休市，无需操作"


def test_card_uses_beijing_date_and_rechecks_on_midnight_and_resume():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is needed to execute the card's browser script")
    signal = build_signal(
        date(2026, 9, 4), snapshot(26, "2026-09-03"), state_for("2026-09-04"), CONFIG
    )
    script = re.search(r"<script>(.*?)</script>", render_html(signal), re.S).group(1)
    harness = r"""
const vm = require('node:vm');
const assert = require('node:assert/strict');
const nodes = {};
const element = key => nodes[key] ||= {textContent: '', style: {}};
element('.action').textContent = 'original buy';
let now = '2026-09-04T15:59:00Z';
let timer, resume;
class Clock extends Date { constructor(...args) { super(...(args.length ? args : [now])); } }
const context = { Date: Clock, Intl,
  document: {getElementById: element, querySelector: element,
    addEventListener: (event, callback) => { resume = callback; }},
  setInterval: callback => { timer = callback; }
};
vm.runInNewContext(SCRIPT, context);
assert.equal(element('.action').textContent, 'original buy');
now = '2026-09-04T16:01:00Z';
timer();
assert.equal(element('signal-title').textContent, 'VIX今日操作 · 2026-09-05');
assert.equal(element('.action').textContent, '今日周末休市，无需操作');
now = '2026-09-06T16:01:00Z';
resume();
assert.equal(element('signal-title').textContent, 'VIX今日操作 · 2026-09-07');
assert.equal(element('.action').textContent, '今日操作提示尚未更新，请等待更新后核对');
assert.ok(element('signal-freshness').textContent.includes('2026-09-04'));
"""
    subprocess.run(
        [node, "-e", "const SCRIPT = " + json.dumps(script) + ";\n" + harness],
        check=True, capture_output=True, text=True,
    )
