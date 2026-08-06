#!/usr/bin/env python3
"""Locate business-segment and revenue evidence pages in CNINFO annual-report PDFs.

The output is an evidence index, not a revenue classification. Page numbers are the
1-based PDF page sequence so every hit can be reproduced before manual table review.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
INPUT = OUT / "涉农入口公司年份_年度报告链接主表_v1.csv"
HEADERS = {"User-Agent": "Mozilla/5.0 (academic source audit)"}
BUSINESS_PATTERNS = [
    r"分行业.{0,10}分产品.{0,10}分地区",
    r"主营业务分行业",
    r"主营业务（?分行业）?",
    r"主营业务收入分行业",
    r"主营业务构成情况",
    r"主营业务分部报告",
    r"营业收入构成",
    r"占公司营业收入或营业利润.{0,8}10%",
    r"公司主营业务数据统计口径",
]
AGRI_TERMS = [
    "农业", "种植", "养殖", "种子", "饲料", "兽药", "农药", "化肥", "农业机械",
    "畜牧", "渔业", "水产", "生猪", "肉鸡", "肉牛", "乳制品", "粮食", "农产品",
    "棉花", "林业", "农垦", "屠宰", "农副产品", "食用菌",
]
WRITE_LOCK = threading.Lock()


def clean_page(text: str) -> str:
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def page_list(indices: list[int]) -> str:
    return "|".join(str(index + 1) for index in sorted(set(indices)))


def relevant_excerpt(pages: list[str], indices: list[int], limit: int = 16000) -> str:
    chosen = []
    for index in sorted(set(indices))[:4]:
        for adjacent in [index, index + 1]:
            if adjacent < len(pages):
                chosen.append(f"[PDF页{adjacent + 1}]\n{clean_page(pages[adjacent])}")
    return "\n\n".join(dict.fromkeys(chosen))[:limit]


def fetch_text(url: str) -> tuple[str, int]:
    error = None
    for attempt in range(4):
        try:
            response = requests.get(url, headers=HEADERS, timeout=90)
            response.raise_for_status()
            if not response.content.startswith(b"%PDF"):
                raise RuntimeError("response is not a PDF")
            with tempfile.NamedTemporaryFile(suffix=".pdf") as handle:
                handle.write(response.content)
                handle.flush()
                result = subprocess.run(
                    ["pdftotext", "-layout", handle.name, "-"],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
            return result.stdout, len(response.content)
        except Exception as exc:
            error = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(str(error))


def process(row: dict[str, str]) -> dict[str, str]:
    result = dict(row)
    try:
        text, byte_count = fetch_text(row["pdf_url"])
        pages = text.split("\f")
        if pages and not pages[-1].strip():
            pages.pop()
        normalized = [re.sub(r"\s+", "", page) for page in pages]
        business_hits = []
        business_scores = []
        for index, page in enumerate(normalized):
            score = sum(bool(re.search(pattern, page)) for pattern in BUSINESS_PATTERNS)
            if score:
                business_hits.append(index)
                business_scores.append((score, index))
        agriculture_hits = [
            index for index, page in enumerate(normalized)
            if sum(term in page for term in AGRI_TERMS) >= 3
        ]
        income_statement_hits = []
        for index, page in enumerate(normalized):
            if "利润表" not in page and "损益表" not in page:
                continue
            page_and_next = page + (normalized[index + 1] if index + 1 < len(normalized) else "")
            if "一、营业收入" in page_and_next or "一、营业总收入" in page_and_next:
                income_statement_hits.append(index)
        primary = max(business_scores, default=(0, -1))[1]
        result.update(
            {
                "pdf_parse_status": "PDF文本提取成功",
                "pdf_bytes_downloaded": str(byte_count),
                "pdf_page_count": str(len(pages)),
                "text_character_count": str(len(text)),
                "business_section_pdf_pages": page_list(business_hits),
                "business_section_primary_pdf_page": str(primary + 1) if primary >= 0 else "",
                "business_section_evidence_excerpt": relevant_excerpt(pages, [primary]) if primary >= 0 else "",
                "agriculture_keyword_pdf_pages": page_list(agriculture_hits),
                "income_statement_pdf_pages": page_list(income_statement_hits),
                "income_statement_evidence_excerpt": relevant_excerpt(
                    pages, income_statement_hits[:1], limit=6000
                ),
                "manual_review_status": "待人工读取业务表并判定收入重叠",
            }
        )
    except Exception as exc:
        result.update(
            {
                "pdf_parse_status": f"PDF文本提取失败：{exc}",
                "pdf_bytes_downloaded": "",
                "pdf_page_count": "",
                "text_character_count": "",
                "business_section_pdf_pages": "",
                "business_section_primary_pdf_page": "",
                "business_section_evidence_excerpt": "",
                "agriculture_keyword_pdf_pages": "",
                "income_statement_pdf_pages": "",
                "income_statement_evidence_excerpt": "",
                "manual_review_status": "PDF待重新获取或OCR",
            }
        )
    return result


def write_checkpoint(rows: list[dict[str, str]], path: Path) -> None:
    with WRITE_LOCK:
        pd.DataFrame(rows).sort_values(["year", "stock_code"]).to_csv(
            path, index=False, encoding="utf-8-sig"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", required=True)
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    output = OUT / f"年报主营业务与收入页定位_{args.year}_v1.csv"
    source = pd.read_csv(INPUT, dtype=str).fillna("")
    source = source[source["year"].eq(str(args.year))].copy()
    existing_rows = []
    if output.exists():
        existing = pd.read_csv(output, dtype=str).fillna("")
        existing_rows = existing.to_dict("records")
        current_keys = set(zip(source["stock_code"], source["year"], source["pdf_url"]))
        successful = (
            existing["pdf_parse_status"].eq("PDF文本提取成功")
            & existing["business_section_primary_pdf_page"].ne("")
            & existing["income_statement_pdf_pages"].ne("")
        )
        done = set(
            zip(
                existing.loc[successful, "stock_code"],
                existing.loc[successful, "year"],
                existing.loc[successful, "pdf_url"],
            )
        )
        source = source[
            ~source.apply(
                lambda row: (row["stock_code"], row["year"], row["pdf_url"]) in done,
                axis=1,
            )
        ]
        existing_rows = [
            row for row in existing_rows
            if (row["stock_code"], row["year"], row["pdf_url"]) in done
            and (row["stock_code"], row["year"], row["pdf_url"]) in current_keys
        ]
    rows = list(existing_rows)
    completed_since_write = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(process, row) for row in source.to_dict("records")]
        for future in as_completed(futures):
            rows.append(future.result())
            completed_since_write += 1
            if completed_since_write >= 10:
                write_checkpoint(rows, output)
                completed_since_write = 0
    write_checkpoint(rows, output)
    result = pd.DataFrame(rows)
    print("year", args.year)
    print("rows", len(result))
    print("pdf_success", result.pdf_parse_status.eq("PDF文本提取成功").sum())
    print("pdf_failed", (~result.pdf_parse_status.eq("PDF文本提取成功")).sum())
    print("business_section_found", result.business_section_primary_pdf_page.ne("").sum())
    print("income_statement_found", result.income_statement_pdf_pages.ne("").sum())


if __name__ == "__main__":
    main()
