#!/usr/bin/env python3
"""Extract reviewable evidence from definitive CNINFO risk-warning announcements.

This script does not decide final ST intervals. It removes obvious warning/application/
progress notices, downloads the remaining official PDFs, and preserves date-bearing lines
for human verification.
"""

from __future__ import annotations

import re
import subprocess
import tempfile
import time
from pathlib import Path

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
INPUT = OUT / "涉农入口公司_巨潮风险警示公告索引_v1.csv"
OUTPUT = OUT / "涉农入口公司_风险警示事件证据候选_v1.csv"
HEADERS = {"User-Agent": "Mozilla/5.0 (academic source audit)"}


def candidate_kind(title: str) -> str:
    if re.search(r"可能|存在被实施|申请|进展|专项|独立董事|法律意见|关注公告", title):
        return ""
    if "继续" in title and not re.search(r"撤销.+继续", title):
        return ""
    if "撤销" in title:
        return "撤销或风险类型转换"
    if re.search(r"实施|实行", title):
        return "实施或叠加"
    return ""


def pdf_text(url: str) -> str:
    error = None
    for attempt in range(4):
        try:
            response = requests.get(url, headers=HEADERS, timeout=45)
            response.raise_for_status()
            with tempfile.NamedTemporaryFile(suffix=".pdf") as handle:
                handle.write(response.content)
                handle.flush()
                result = subprocess.run(
                    ["pdftotext", "-layout", handle.name, "-"],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=45,
                )
            return result.stdout
        except Exception as exc:
            error = exc
            time.sleep(1.2 * (attempt + 1))
    raise RuntimeError(str(error))


def evidence_lines(text: str) -> str:
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    selected = []
    for index, line in enumerate(lines):
        if not line or not re.search(r"实施|实行|撤销|复牌|起始日|更名|简称", line):
            continue
        context = " ".join(item for item in lines[max(0, index - 1):index + 2] if item)
        if re.search(r"20\d{2}\s*年|20\d{2}[-./]", context):
            selected.append(context)
    # Deduplicate without losing document order, then cap oversized legal boilerplate.
    return " || ".join(dict.fromkeys(selected))[:6000]


def main() -> None:
    announcements = pd.read_csv(INPUT, dtype=str).fillna("")
    announcements["event_candidate_type"] = announcements["announcement_title"].map(candidate_kind)
    candidates = announcements[announcements["event_candidate_type"].ne("")].copy()
    rows = []
    for row in candidates.sort_values(["stock_code", "announcement_date"]).to_dict("records"):
        try:
            text = pdf_text(row["pdf_url"])
            row["pdf_parse_status"] = "PDF文本提取成功"
            row["date_evidence_excerpt"] = evidence_lines(text)
        except Exception as exc:
            row["pdf_parse_status"] = f"PDF文本提取失败：{exc}"
            row["date_evidence_excerpt"] = ""
        row["manual_review_status"] = "待人工判定实际生效日及风险状态是否连续"
        rows.append(row)
    result = pd.DataFrame(rows)
    result.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("candidate_rows", len(result))
    print("codes", result["stock_code"].nunique())
    print("pdf_success", result["pdf_parse_status"].eq("PDF文本提取成功").sum())
    print("pdf_failed", (~result["pdf_parse_status"].eq("PDF文本提取成功")).sum())


if __name__ == "__main__":
    main()
