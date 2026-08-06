#!/usr/bin/env python3
"""Collect CNINFO delisting/suspension announcement metadata for entry-pool issuers."""

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
OUTPUT = OUT / "涉农入口公司_巨潮退市及暂停上市公告索引_v1.csv"
STATUS = OUT / "涉农入口公司_退市公告检索状态_v1.csv"
KEYWORDS = ["退市整理期", "终止上市", "暂停上市", "恢复上市"]
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


def company_org(code: str) -> str:
    result = request_json(
        "POST",
        "https://www.cninfo.com.cn/new/information/topSearch/query",
        params={"keyWord": code, "maxNum": "10"},
    )
    exact = [item for item in result if item.get("code") == code]
    return exact[0].get("orgId", "") if exact else ""


def query_keyword(company: dict[str, str], org_id: str, keyword: str):
    code = company["stock_code"]
    column = "sse" if company["exchange"] == "上海证券交易所" else "szse"
    payload = {
        "pageNum": "1",
        "pageSize": "30",
        "column": column,
        "tabName": "fulltext",
        "stock": f"{code},{org_id}",
        "searchkey": keyword,
        "seDate": "2013-01-01~2023-12-31",
        "isHLtitle": "true",
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
        adjunct = item.get("adjunctUrl") or ""
        rows.append(
            {
                "stock_code": code,
                "exchange": company["exchange"],
                "current_short_name": company["current_short_name"],
                "announcement_id": item.get("announcementId") or "",
                "announcement_title": clean_title(item.get("announcementTitle") or ""),
                "announcement_sec_name": item.get("secName") or "",
                "announcement_date": time.strftime(
                    "%Y-%m-%d", time.gmtime((item.get("announcementTime") or 0) / 1000)
                ),
                "pdf_url": f"https://static.cninfo.com.cn/{adjunct}" if adjunct else "",
                "matched_keyword": keyword,
                "retrieved_date": RETRIEVED,
                "review_status": "待区分公司自身状态与一般风险披露",
            }
        )
    return rows, total, page_number - 1


def query_company(company: dict[str, str]):
    code = company["stock_code"]
    org_id = company_org(code)
    if not org_id:
        return [], [{**company, "keyword": "", "query_status": "未取得证券组织代码"}]
    rows, statuses = [], []
    for keyword in KEYWORDS:
        keyword_rows, total, pages = query_keyword(company, org_id, keyword)
        rows.extend(keyword_rows)
        statuses.append(
            {
                **company,
                "org_id": org_id,
                "keyword": keyword,
                "query_status": "检索完成",
                "api_reported_total": str(total),
                "pages_retrieved": str(pages),
                "retrieved_date": RETRIEVED,
            }
        )
    return rows, statuses


def main() -> None:
    entries = pd.read_csv(INPUT, dtype=str)
    companies = (
        entries[["stock_code", "exchange_final", "current_short_name"]]
        .drop_duplicates("stock_code")
        .rename(columns={"exchange_final": "exchange"})
        .sort_values("stock_code")
        .fillna("")
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
                company_rows, company_statuses = future.result()
            except Exception as exc:
                company_rows = []
                company_statuses = [
                    {**company, "keyword": "", "query_status": f"请求失败：{exc}"}
                ]
            rows.extend(company_rows)
            statuses.extend(company_statuses)

    result = pd.DataFrame(rows)
    if not result.empty:
        grouped = (
            result.groupby(["stock_code", "announcement_id"], as_index=False)
            .agg(
                exchange=("exchange", "first"),
                current_short_name=("current_short_name", "first"),
                announcement_title=("announcement_title", "first"),
                announcement_sec_name=("announcement_sec_name", "first"),
                announcement_date=("announcement_date", "first"),
                pdf_url=("pdf_url", "first"),
                matched_keywords=("matched_keyword", lambda x: "|".join(sorted(set(x)))),
                retrieved_date=("retrieved_date", "first"),
                review_status=("review_status", "first"),
            )
            .sort_values(["stock_code", "announcement_date", "announcement_id"])
        )
    else:
        grouped = result
    grouped.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    status = pd.DataFrame(statuses).sort_values(["stock_code", "keyword"])
    status.to_csv(STATUS, index=False, encoding="utf-8-sig")
    print("companies", len(companies))
    print("keyword_queries_expected", len(companies) * len(KEYWORDS))
    print("keyword_queries_success", status.query_status.eq("检索完成").sum())
    print("failed_company_tasks", status.query_status.str.startswith("请求失败").sum())
    print("deduplicated_announcements", len(grouped))
    print("codes_with_announcements", grouped.stock_code.nunique() if len(grouped) else 0)


if __name__ == "__main__":
    main()
