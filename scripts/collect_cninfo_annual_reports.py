#!/usr/bin/env python3
"""Collect and select statutory annual reports for all entry-pool company-years."""

from __future__ import annotations

import html
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
INPUT = OUT / "涉农样本入口候选池_行业与龙头并集_v1.csv"
RAW = OUT / "涉农入口公司_巨潮年度报告原始索引_v1.csv"
SELECTED = OUT / "涉农入口公司年份_年度报告链接主表_v1.csv"
QUERY_STATUS = OUT / "涉农入口公司_年度报告检索状态_v1.csv"
RETRIEVED = "2026-08-06"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (academic source audit)",
    "Referer": "https://www.cninfo.com.cn/",
    "X-Requested-With": "XMLHttpRequest",
}


def request_json(method: str, url: str, *, params=None, data=None, attempts: int = 6):
    error = None
    for attempt in range(attempts):
        try:
            response = requests.request(
                method, url, params=params, data=data, headers=HEADERS, timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            error = exc
            time.sleep(1.2 * (attempt + 1))
    raise RuntimeError(str(error))


def clean_title(value: str) -> str:
    return re.sub(r"<[^>]+>", "", html.unescape(value or "")).strip()


def extract_report_year(title: str) -> str:
    """Handle CNINFO variants such as 2023年度报告、2022年年报、2020年_年度报告."""
    match = re.search(r"(20\d{2})\s*年?\s*[_－—-]?\s*(?:年度报告|年报)", title)
    return match.group(1) if match else ""


def query_company(company: dict[str, str]):
    code = company["stock_code"]
    search = request_json(
        "POST",
        "https://www.cninfo.com.cn/new/information/topSearch/query",
        params={"keyWord": code, "maxNum": "10"},
    )
    exact = [item for item in search if item.get("code") == code]
    if not exact:
        return [], {**company, "query_status": "未取得证券组织代码"}
    org_id = exact[0].get("orgId", "")
    column = "sse" if company["exchange"] == "上海证券交易所" else "szse"
    payload = {
        "pageNum": "1",
        "pageSize": "30",
        "column": column,
        "tabName": "fulltext",
        "stock": f"{code},{org_id}",
        "category": "category_ndbg_szsh;",
        "seDate": "2014-01-01~2024-12-31",
        "isHLtitle": "false",
    }
    first = request_json(
        "POST", "https://www.cninfo.com.cn/new/hisAnnouncement/query", data=payload
    )
    items = list(first.get("announcements") or [])
    total = int(first.get("totalAnnouncement") or len(items))
    page_number = 2
    while len(items) < total:
        payload["pageNum"] = str(page_number)
        page = request_json(
            "POST", "https://www.cninfo.com.cn/new/hisAnnouncement/query", data=payload
        )
        page_items = list(page.get("announcements") or [])
        if not page_items:
            break
        items.extend(page_items)
        page_number += 1
    rows = []
    for item in items:
        title = clean_title(item.get("announcementTitle") or "")
        adjunct = item.get("adjunctUrl") or ""
        rows.append(
            {
                "stock_code": code,
                "exchange": company["exchange"],
                "current_short_name": company["current_short_name"],
                "org_id": org_id,
                "announcement_id": item.get("announcementId") or "",
                "announcement_title": title,
                "announcement_sec_name": item.get("secName") or "",
                "publication_date": time.strftime(
                    "%Y-%m-%d", time.gmtime((item.get("announcementTime") or 0) / 1000)
                ),
                "pdf_url": f"https://static.cninfo.com.cn/{adjunct}" if adjunct else "",
                "report_year_extracted": extract_report_year(title),
                "adjunct_size": item.get("adjunctSize") or "",
                "retrieved_date": RETRIEVED,
            }
        )
    return rows, {
        **company,
        "org_id": org_id,
        "query_status": "检索完成",
        "api_reported_total": str(total),
        "rows_retrieved": str(len(rows)),
        "pages_retrieved": str(page_number - 1),
        "retrieved_date": RETRIEVED,
    }


def main() -> None:
    entries = pd.read_csv(INPUT, dtype=str).fillna("")
    companies = (
        entries[["stock_code", "exchange_final", "current_short_name"]]
        .drop_duplicates("stock_code")
        .rename(columns={"exchange_final": "exchange"})
        .sort_values("stock_code")
    )
    rows, statuses = [], []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(query_company, company): company
            for company in companies.to_dict("records")
        }
        for future in as_completed(futures):
            company = futures[future]
            try:
                company_rows, status = future.result()
            except Exception as exc:
                company_rows = []
                status = {**company, "query_status": f"请求失败：{exc}"}
            rows.extend(company_rows)
            statuses.append(status)

    raw = pd.DataFrame(rows)
    if not raw.empty:
        raw = raw.drop_duplicates(["stock_code", "announcement_id"]).sort_values(
            ["stock_code", "publication_date", "announcement_id"]
        )
    raw.to_csv(RAW, index=False, encoding="utf-8-sig")
    pd.DataFrame(statuses).sort_values("stock_code").to_csv(
        QUERY_STATUS, index=False, encoding="utf-8-sig"
    )

    full = raw[
        raw["report_year_extracted"].between("2013", "2023")
        & raw["announcement_title"].str.contains(
            r"20\d{2}\s*年?\s*[_－—-]?\s*(?:年度报告|年报)", regex=True
        )
        & ~raw["announcement_title"].str.contains(
            "摘要|英文|已取消|取消|关于|公告|问询|审核意见|审计报告|社会责任|内部控制",
            regex=True,
        )
    ].copy()
    full["announcement_id_numeric"] = pd.to_numeric(
        full["announcement_id"], errors="coerce"
    ).fillna(0)
    full = full.sort_values(
        ["stock_code", "report_year_extracted", "publication_date", "announcement_id_numeric"]
    )
    chosen = full.drop_duplicates(
        ["stock_code", "report_year_extracted"], keep="last"
    ).rename(columns={"report_year_extracted": "year"})
    chosen = chosen[
        [
            "stock_code", "year", "announcement_id", "announcement_title",
            "announcement_sec_name", "publication_date", "pdf_url", "adjunct_size",
            "retrieved_date",
        ]
    ]

    panel = entries[
        ["stock_code", "year", "current_legal_full_name", "current_short_name", "entry_basis"]
    ].merge(chosen, on=["stock_code", "year"], how="left")
    panel["annual_report_status"] = "已取得法定年度报告链接"
    panel.loc[panel["pdf_url"].isna(), "annual_report_status"] = "年度报告链接待核实"
    panel = panel.sort_values(["year", "stock_code"])
    panel.to_csv(SELECTED, index=False, encoding="utf-8-sig")

    print("companies", len(companies))
    print("successful", sum(item.get("query_status") == "检索完成" for item in statuses))
    print("failed", sum(item.get("query_status") != "检索完成" for item in statuses))
    print("raw_rows", len(raw))
    print("full_report_candidates", len(full))
    print("entry_company_years", len(panel))
    print("annual_report_links_found", panel["pdf_url"].notna().sum())
    print("annual_report_links_missing", panel["pdf_url"].isna().sum())


if __name__ == "__main__":
    main()
