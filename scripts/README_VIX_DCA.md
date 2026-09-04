# VIX定投策略自动更新系统 V2.1

## 概述

本系统自动获取VIX恐慌指数和纳指100 ETF（513110）的价格数据，每日更新VIX定投策略的收益情况。

**核心逻辑**：
- 使用**昨日美股收盘后的VIX数据**，指导今日A股ETF的定投操作
- 每日A股收盘后自动更新ETF收盘价和持仓收益
- 定投日（每双周周二）直接按VIX档位买入，不根据VIX卖出

**策略版本**：V2.1（简化定投版，2026-09-08起生效）

---

## 策略规则速查

### 买入规则

| 步骤 | 规则 | 说明 |
|:---|:---|:---|
| 1. 固定档位 | VIX<15:4000 / 15-20:5000 / 20-25:6000 / 25-30:8000 / ≥30:10000 | 每期都买，VIX越高买得越多 |

### 卖出规则

V2.1不依据VIX主动卖出。

趋势修正、极端恐慌减仓、低VIX减仓、资金回流和盘中应急补仓均已停用。

---

## 文件说明

| 文件 | 说明 |
|------|------|
| `scripts/auto_update_vix_dca.py` | 自动更新脚本 V2.1 |
| `scripts/generate_vix_morning_signal.py` | 生成VIX数值与“今日怎么操作”卡片 |
| `.github/workflows/vix_dca_morning_signal.yml` | 工作日08:30生成早盘提示，08:45失败补跑 |
| `.github/workflows/vix_dca_daily_update.yml` | 下午更新ETF价格、持仓与收益 |
| `decision-tracking/vix_dca_strategy/strategy_config.json` | 策略配置（档位、修正、风控参数） |
| `decision-tracking/vix_dca_strategy/state.json` | 策略状态数据 |
| `decision-tracking/vix_dca_strategy/today_signal.json` | 今日操作的机器可读数据 |
| `public/vix_strategy/today_signal.html` | 策略页嵌入的今日操作卡片 |
| `decision-tracking/vix_dca_strategy/dashboard_data.json` | 仪表板数据 |
| `decision-tracking/vix_dca_strategy/daily_snapshot.csv` | 每日快照记录 |
| `decision-tracking/vix_dca_strategy/trades.csv` | 交易记录 |
| `portfolio/VIX定投策略.md` | 网页展示文档 |
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
python scripts/auto_update_vix_dca.py --date 2026-05-05 --vix 22.50 --price 2.20

# 试运行（不保存）
python scripts/auto_update_vix_dca.py --dry-run

# 强制更新（即使今天已更新）
python scripts/auto_update_vix_dca.py --force
```

---

## GitHub Actions 定时执行

### 执行时间

- **北京时间**: 每天 15:30 ~ 15:40（A股收盘后）
- **UTC时间**: 每天 07:30 ~ 07:40
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

1. 获取今日VIX
2. 获取今日ETF收盘价
3. 计算持仓市值和收益
4. 更新 `state.json`
5. 更新 `dashboard_data.json`
6. 记录每日快照到 `daily_snapshot.csv`
7. 更新 `VIX定投策略.md` 文档
8. 同步到 `public/vix_strategy/`

### 定投日额外操作

如果今天是定投日（每双周周二），按以下顺序执行：

```
1. 读取美国上一交易日VIX收盘值
2. 根据固定档位确定买入金额
3. 执行买入并记录本期VIX
4. 滚动到下一个双周定投日
```

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

| 日期 | 状态 | 说明 |
|------|------|------|
| 2026-03-24 | ✅ 已执行 | 初始建仓（标准定投，VIX=21.0） |
| 2026-04-07 | ✅ 已执行 | 标准定投（VIX=19.5） |
| 2026-05-05 | ⏳ 待定 | 下次定投日 |
| 2026-05-19 | ⏳ 待定 | 双周定投 |
| 2026-06-02 | ⏳ 待定 | 双周定投 |

---

## 注意事项

1. **VIX数据时效性**：使用昨日美股收盘后的VIX数据
2. **ETF价格**：使用今日A股收盘后513110价格
3. **交易日**：定投日如遇节假日顺延
4. **数据备份**：Git历史自动备份所有数据变化
5. **策略状态**：state.json 中 `strategy_state` 字段跟踪VIX历史、减仓比例、回流状态等，请勿手动修改

---

**版本**: V2.1（简化定投版）
**最后更新**: 2026-04-29
