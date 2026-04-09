# VIX定投策略自动更新系统

## 概述

本系统自动获取VIX恐慌指数和纳指100 ETF（513110）的价格数据，每日更新VIX定投策略的收益情况。

**核心逻辑**：
- 使用**昨日美股收盘后的VIX数据**，指导今日A股ETF的定投操作
- 每日A股收盘后自动更新ETF收盘价和持仓收益
- 定投日（每两周周二）根据VIX档位执行买入

---

## 文件说明

| 文件 | 说明 |
|------|------|
| `scripts/auto_update_vix_dca.py` | 自动更新脚本 |
| `.github/workflows/vix_dca_daily_update.yml` | GitHub Actions工作流 |
| `08-决策追踪/vix_dca_strategy/state.json` | 策略状态数据 |
| `08-决策追踪/vix_dca_strategy/dashboard_data.json` | 仪表板数据 |
| `08-决策追踪/vix_dca_strategy/daily_snapshot.csv` | 每日快照记录 |
| `08-决策追踪/vix_dca_strategy/trades.csv` | 交易记录 |
| `模拟持仓/VIX定投策略.md` | 网页展示文档 |
| `public/vix_strategy/dashboard_data.json` | 网页数据源 |

---

## 本地使用

### 基本用法（自动获取数据）

```bash
python scripts/auto_update_vix_dca.py
```

### 手动指定数据

```bash
# 指定今日数据
python scripts/auto_update_vix_dca.py --date 2026-04-09 --vix 29.50 --price 2.35

# 试运行（不保存）
python scripts/auto_update_vix_dca.py --dry-run

# 强制更新（即使今天已更新）
python scripts/auto_update_vix_dca.py --force
```

---

## GitHub Actions 定时执行

### 执行时间

- **北京时间**: 每天 15:30 和 15:40（A股收盘后）
- **UTC时间**: 每天 07:30 和 07:40
- **执行日**: 周一到周五（工作日）

### 手动触发

在 GitHub 仓库页面：
1. 进入 Actions 标签
2. 选择 "VIX定投策略每日更新"
3. 点击 "Run workflow"
4. 可选：指定日期、VIX值、价格，或强制更新

---

## 数据源

| 数据 | 来源 | 说明 |
|------|------|------|
| VIX指数 | Yahoo Finance (^VIX) | 美股波动率指数 |
| ETF价格 | akshare (东方财富) | 纳指100 ETF (513110) |

---

## 更新逻辑

### 每日更新（无论是否定投日）

1. 获取今日VIX值
2. 获取今日ETF收盘价
3. 计算持仓市值和收益
4. 更新 `state.json`
5. 更新 `dashboard_data.json`
6. 记录每日快照到 `daily_snapshot.csv`
7. 更新 `VIX定投策略.md` 文档
8. 同步到 `public/vix_strategy/`

### 定投日额外操作

如果今天是定投日（每两周周二）：

| VIX档位 | 买入金额 | 操作标签 |
|---------|----------|----------|
| ≥ 30 | 6,000元 | 加倍定投 |
| 25-30 | 4,500元 | 加大定投 |
| 20-25 | 3,000元 | 标准定投 |
| < 20 | 0元 | 暂停定投 |

---

## 故障排查

### 问题：自动获取数据失败

**解决方案**：手动指定数据

```bash
python scripts/auto_update_vix_dca.py --vix 29.50 --price 2.35
```

### 问题：今天已更新，但需要重新更新

**解决方案**：使用 `--force` 参数

```bash
python scripts/auto_update_vix_dca.py --force
```

### 问题：GitHub Actions 执行失败

检查步骤：
1. 查看 Actions 日志
2. 确认依赖安装成功
3. 检查数据源是否可用
4. 尝试手动触发并指定参数

---

## 定投日历（2026年）

| 日期 | 状态 |
|------|------|
| 2026-03-26 | ✅ 已执行（标准定投） |
| 2026-04-07 | ✅ 已执行（加倍定投） |
| 2026-04-21 | ⏳ 下次定投日 |
| 2026-05-05 | ⏳ 待定 |
| 2026-05-19 | ⏳ 待定 |

---

## 注意事项

1. **VIX数据时效性**：使用昨日美股收盘后的VIX数据
2. **ETF价格**：使用今日A股收盘后的513110价格
3. **交易日**：定投日如遇节假日顺延
4. **数据备份**：Git历史自动备份所有数据变更
