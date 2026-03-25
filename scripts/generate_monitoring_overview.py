# -*- coding: utf-8 -*-
"""
生成每日监控概览

功能：
1. 扫描 07-分析输出/*_投资分析报告.md
2. 提取目标买点、一句话结论
3. 抓取当前股价（A股+港股）
4. 生成监控概览报告
"""

import re
import akshare as ak
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "07-分析输出"
OUTPUT_FILE = ROOT / "07-分析输出" / "监控概览.md"

def extract_stock_info(report_path):
    """从报告中提取关键信息"""
    content = report_path.read_text(encoding='utf-8')
    
    # 提取股票代码和名称
    filename = report_path.stem
    match = re.match(r'(.+)_(\d+)_.*', filename)
    if not match:
        return None
    
    name = match.group(1)
    code = match.group(2)
    
    # 判断A股还是港股
    is_hk = len(code) == 5
    
    # 提取一句话结论
    one_liner = ""
    match = re.search(r'\*\*一句话结论\*\*[:：](.+?)(?:\n|>|$)', content)
    if match:
        one_liner = match.group(1).strip()
    
    # 提取买点
    buy_points = []
    for line in content.split('\n'):
        if '买点' in line and ('元' in line or '港元' in line):
            # 提取价格
            price_match = re.search(r'(\d+\.?\d*)\s*[元港]', line)
            if price_match:
                buy_points.append({
                    'type': '理想买点' if '理想' in line else '合理买点' if '合理' in line else '买点',
                    'price': float(price_match.group(1))
                })
    
    # 提取当前状态
    status = "未知"
    if '🟢' in content[:5000] and ('可建仓' in content[:5000] or '买入' in content[:5000]):
        status = "可买入"
    elif '🟡' in content[:5000] or '观望' in content[:5000]:
        status = "观望"
    elif '🔴' in content[:5000] or '回避' in content[:5000]:
        status = "回避"
    
    return {
        'name': name,
        'code': code,
        'is_hk': is_hk,
        'full_code': f"{code}.HK" if is_hk else f"{code}.{'SH' if code.startswith('6') else 'SZ'}",
        'one_liner': one_liner,
        'buy_points': buy_points,
        'status': status
    }

def get_current_price(stock_info):
    """获取当前股价"""
    try:
        code = stock_info['code']
        
        if stock_info['is_hk']:
            # 港股使用 akshare
            df = ak.stock_hk_ggt_components_em()
            row = df[df['代码'] == code]
            if not row.empty:
                return {
                    'price': float(row.iloc[0]['最新价']),
                    'change': float(row.iloc[0]['涨跌幅'])
                }
        else:
            # A股使用 akshare
            df = ak.stock_zh_a_spot_em()
            row = df[df['代码'] == code]
            if not row.empty:
                return {
                    'price': float(row.iloc[0]['最新价']),
                    'change': float(row.iloc[0]['涨跌幅'])
                }
    except Exception as e:
        print(f"获取 {stock_info['name']} 股价失败: {e}")
    
    return None

def calculate_distance(current, target):
    """计算距离买点的幅度"""
    if not current or not target:
        return None
    return (current - target) / target * 100

def generate_overview():
    """生成监控概览"""
    # 扫描所有报告
    reports = list(REPORT_DIR.glob("*_投资分析报告.md"))
    
    all_stocks = []
    for report in reports:
        info = extract_stock_info(report)
        if info:
            # 获取当前股价
            price_info = get_current_price(info)
            if price_info:
                info['current_price'] = price_info['price']
                info['change_pct'] = price_info['change']
                
                # 计算距离最近买点的幅度
                if info['buy_points']:
                    min_price = min(bp['price'] for bp in info['buy_points'])
                    info['distance'] = calculate_distance(price_info['price'], min_price)
                    info['target_price'] = min_price
                else:
                    info['distance'] = None
                    info['target_price'] = None
                
                all_stocks.append(info)
    
    # 按距离买点排序（距离最近的排前面）
    all_stocks.sort(key=lambda x: x['distance'] if x['distance'] is not None else 999)
    
    # 分类
    close_to_buy = [s for s in all_stocks if s['distance'] is not None and s['distance'] <= 5]  # 5%以内
    normal = [s for s in all_stocks if s['distance'] is None or s['distance'] > 5]
    
    # 生成报告
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    lines = [
        "# 📊 每日监控概览",
        "",
        f"> **更新时间**: {now}",
        f"> **监控标的**: {len(all_stocks)} 只",
        "> **说明**: 本概览每日自动生成，结合最新股价与报告中的目标买点，帮助快速定位交易机会。",
        "",
        "---",
        "",
    ]
    
    # 接近买点的标的
    if close_to_buy:
        lines.extend([
            "## 🔥 接近买点（5%以内）",
            "",
            "| 标的 | 代码 | 当前价 | 目标买点 | 距离 | 涨跌幅 | 一句话结论 |",
            "|------|------|--------|----------|------|--------|------------|",
        ])
        for s in close_to_buy:
            distance_str = f"+{s['distance']:.1f}%" if s['distance'] > 0 else f"{s['distance']:.1f}%"
            change_str = f"+{s['change_pct']:.2f}%" if s['change_pct'] > 0 else f"{s['change_pct']:.2f}%"
            lines.append(
                f"| **{s['name']}** | {s['full_code']} | {s['current_price']:.2f} | {s['target_price']:.2f} | "
                f"{distance_str} | {change_str} | {s['one_liner'][:50]}{'...' if len(s['one_liner']) > 50 else ''} |"
            )
        lines.append("")
    
    # 所有标的总览
    lines.extend([
        "## 📋 全部标的监控",
        "",
        "| 标的 | 代码 | 当前价 | 目标买点 | 距离买点 | 状态 | 一句话结论 |",
        "|------|------|--------|----------|----------|------|------------|",
    ])
    
    for s in all_stocks:
        if s['distance'] is not None:
            distance_str = f"+{s['distance']:.1f}%" if s['distance'] > 0 else f"{s['distance']:.1f}%"
        else:
            distance_str = "-"
        
        change_str = f"+{s['change_pct']:.2f}%" if s['change_pct'] > 0 else f"{s['change_pct']:.2f}%"
        target_str = f"{s['target_price']:.2f}" if s['target_price'] else "-"
        
        lines.append(
            f"| {s['name']} | {s['full_code']} | {s['current_price']:.2f} | {target_str} | "
            f"{distance_str} | {s['status']} | {s['one_liner'][:40]}{'...' if len(s['one_liner']) > 40 else ''} |"
        )
    
    lines.extend([
        "",
        "---",
        "",
        "## 📌 使用说明",
        "",
        "1. **距离买点**: 正值表示高于买点（需等待），负值表示低于买点（可买入）",
        "2. **一句话结论**: 来自原报告的核心观点，帮助快速回忆标的质量",
        "3. **状态**: 可买入/观望/回避，来自原报告的综合判断",
        "4. **更新频率**: 每日收盘后自动更新",
        "",
        "> 💡 **提示**: 点击标的名称可查看完整投资分析报告",
    ])
    
    # 写入文件
    OUTPUT_FILE.write_text('\n'.join(lines), encoding='utf-8')
    print(f"[OK] 监控概览已生成: {OUTPUT_FILE}")
    return len(all_stocks)

if __name__ == '__main__':
    count = generate_overview()
    print(f"共监控 {count} 只标的")
