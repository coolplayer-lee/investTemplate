import tempfile
import unittest
from pathlib import Path

from scripts.validate_report_contract import audit_report


class ReportContractTests(unittest.TestCase):
    def write_report(self, text: str) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "示例_00000_投资分析报告.md"
        path.write_text(text, encoding="utf-8")
        return path

    def test_legacy_report_is_classified_without_current_contract_errors(self):
        path = self.write_report("# 示例\n\n模板版本：V5.5.23\n")
        audit = audit_report(path, "V5.5.24")
        self.assertFalse(audit.current)
        self.assertEqual([], audit.errors)

    def test_current_report_missing_fields_fails(self):
        path = self.write_report("# 示例\n\n**一句话结论**：测试\n\n模板版本：V5.5.24\n")
        audit = audit_report(path, "V5.5.24")
        self.assertTrue(audit.current)
        self.assertIn("缺少主框架", audit.errors)

    def test_current_report_minimum_contract_passes(self):
        path = self.write_report(
            """# 示例

**一句话结论**：状态、估值、操作

模板版本：V5.5.24

| 项目 | 内容 |
|---|---|
| 主框架 | 价值回归 |
| 上市板块 | 港股主板 |
| 流程状态 | 标准分析 |
| 股东关系 | 公司养股东 |
| 数据截止日 | 2026-06-30 |
| 股价基准日 | 2026-08-20 |
| 建议仓位上限 | 5% |
| 下次复核日 | 2026-09-30 |

## 证伪条件

| 指标 | 数值 |
|---|---:|
| 税前股息率 | 5% |
| FCF/市值 | 12% |
| 市值/FCF | 8.3倍 |
| 两年平均FCF | 10亿元 |
| 即时净现金/市值 | 50% |
| 广义净现金 | 12亿元 |
| 审慎即时净现金 | 8亿元 |

现金可立即动用，但不等于可自由分红。
"""
        )
        audit = audit_report(path, "V5.5.24")
        self.assertEqual([], audit.errors)


if __name__ == "__main__":
    unittest.main()
