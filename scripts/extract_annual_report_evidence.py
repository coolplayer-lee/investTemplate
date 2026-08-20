#!/usr/bin/env python3
"""Locate financial-statement evidence pages in annual-report PDFs.

This helper is intentionally read-only.  It prints page numbers and compact text
snippets for a fixed set of accounting terms so that report authors can verify
the original statement before copying a value into a validation YAML file.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from pypdf import PdfReader


TERM_GROUPS = {
    "cash": ("现金及现金等价物", "現金及現金等價物", "货币资金", "貨幣資金", "银行结余及现金", "銀行結餘及現金"),
    "debt": ("借款", "銀行貸款", "银行贷款", "租赁负债", "租賃負債", "计息借款", "計息借款"),
    "profit": ("归属于上市公司股东的净利润", "歸屬於本公司擁有人", "本公司擁有人應佔溢利", "归母净利润"),
    "ocf": ("经营活动产生的现金流量净额", "經營活動產生的現金淨額", "经营活动所得现金净额", "經營活動所得現金淨額"),
    "capex": ("购建固定资产", "購建固定資產", "购买物业、厂房及设备", "購買物業、廠房及設備", "购置物业、厂房及设备", "購置物業、廠房及設備"),
    "dividend": ("每股股息", "每股派息", "每10股派", "每股现金红利", "每股現金紅利"),
    "shares": ("已发行股份", "已發行股份", "总股本", "總股本", "普通股股数", "普通股股數"),
}


def compact(text: str) -> str:
    # CJK annual reports often encode every glyph as a separate text run; removing
    # whitespace keeps accounting labels searchable across those runs.
    return re.sub(r"\s+", "", text).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--group", choices=["all", *TERM_GROUPS], default="all")
    parser.add_argument("--max-pages", type=int, default=4)
    parser.add_argument("--context", type=int, default=220)
    args = parser.parse_args()

    reader = PdfReader(str(args.pdf))
    groups = TERM_GROUPS if args.group == "all" else {args.group: TERM_GROUPS[args.group]}
    print(f"PDF={args.pdf.name} pages={len(reader.pages)}")

    for group, terms in groups.items():
        matches: list[tuple[int, str, str]] = []
        for page_no, page in enumerate(reader.pages, 1):
            text = compact(page.extract_text() or "")
            for term in terms:
                index = text.find(term)
                if index >= 0:
                    start = max(0, index - args.context)
                    end = min(len(text), index + len(term) + args.context)
                    matches.append((page_no, term, text[start:end]))
                    break
            if len(matches) >= args.max_pages:
                break

        print(f"\n[{group}]")
        if not matches:
            print("NO_MATCH")
            continue
        for page_no, term, snippet in matches:
            print(f"page={page_no} term={term}: {snippet}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
