#!/usr/bin/env python3
"""Collect CNINFO risk-warning announcement metadata for the entry-pool issuers."""

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
ANNOUNCEMENTS = OUT / "涉农入口公司_巨潮风险警示公告索引_v1.csv"
STATUS = OUT / "涉农入口公司_风险警示公告检索状态_v1.csv"
RETRIEVED = "2026-08-06"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (academic source audit)",
    "Referer": "https://www.cninfo.com.cn/",
    "X-Requested-With": "XMLHttpRequest",
}


def request_json(method: str, url: str, *, params=None, data=None, attempts: int = 6):
    last_error = None
    for attempt in range(attempts):
        try:
            response = requests.request(
                method, url, params=params, data=data, headers=HEADERS, timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            last_error = exc
            time.sleep(1.2 * (attempt + 1))
    raise RuntimeError(str(last_error))


def clean_title(value: str) -> str:
    return re.sub(r"<[^>]+>", "", html.unescape(value or "")).strip()


def query_company(company: dict[str, str]):
    code = company["stock_code"]
    search = request_json(
        "POST",
        "https://www.cninfo.com.cn/new/information/topSearch/query",
        params={"keyWord": code, "maxNum": "10"},
    )
    exact = [item for item in search if item.get("code") == code]
    if not exact:
        return [], {**company, "org_id": "", "query_status": "未取得证券组织代码"}
    org_id = exact[0].get("orgId", "")
    column = "sse" if company["exchange"] == "上海证券交易所" else "szse"
    payload = {
        "pageNum": "1",
        # CNINFO currently caps this endpoint at 30 rows even if a larger value is sent.
        "pageSize": "30",
        "column": column,
        "tabName": "fulltext",
        "stock": f"{code},{org_id}",
        "searchkey": "风险警示",
        "seDate": "2013-01-01~2023-12-31",
        "isHLtitle": "true",
    }
    result = request_json(
        "POST", "https://www.cninfo.com.cn/new/hisAnnouncement/query", data=payload
    )
    items = list(result.get("announcements") or [])
    total = int(result.get("totalAnnouncement") or len(items))
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
                "org_id": org_id,
                "announcement_id": item.get("announcementId") or "",
                "announcement_title": clean_title(item.get("announcementTitle") or ""),
                "announcement_sec_name": item.get("secName") or "",
                "announcement_date": time.strftime(
                    "%Y-%m-%d", time.gmtime((item.get("announcementTime") or 0) / 1000)
                ),
                "pdf_url": f"https://static.cninfo.com.cn/{adjunct}" if adjunct else "",
                "query_keyword": "风险警示",
                "query_period": "2013-01-01~2023-12-31",
                "retrieved_date": RETRIEVED,
                "review_status": "待解析实施或撤销日期",
            }
        )
    return rows, {
        **company,
        "org_id": org_id,
        "query_status": "检索完成",
        "announcement_count": str(len(rows)),
        "api_reported_total": str(total),
        "pages_retrieved": str(page_number - 1),
        "retrieved_date": RETRIEVED,
    }


def main() -> None:
    entries = pd.read_csv(INPUT, dtype=str)
    companies = (
        entries[["stock_code", "exchange_final", "current_short_name"]]
        .drop_duplicates("stock_code")
        .rename(columns={"exchange_final": "exchange"})
        .sort_values("stock_code")
    )
    companies["exchange"] = companies.apply(
        lambda row: row["exchange"]
        if pd.notna(row["exchange"])
        else ("上海证券交易所" if row["stock_code"].startswith("6") else "深圳证券交易所"),
        axis=1,
    )

    announcement_rows = []
    status_rows = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(query_company, company): company
            for company in companies.to_dict("records")
        }
        for future in as_completed(futures):
            company = futures[future]
            try:
                rows, status = future.result()
            except Exception as exc:
                rows = []
                status = {
                    **company,
                    "org_id": "",
                    "query_status": f"请求失败：{exc}",
                    "announcement_count": "",
                    "retrieved_date": RETRIEVED,
                }
            announcement_rows.extend(rows)
            status_rows.append(status)

    columns = [
        "stock_code", "exchange", "current_short_name", "org_id",
        "announcement_id", "announcement_title", "announcement_sec_name",
        "announcement_date", "pdf_url", "query_keyword", "query_period",
        "retrieved_date", "review_status",
    ]
    announcements = pd.DataFrame(announcement_rows, columns=columns)
    if not announcements.empty:
        announcements = announcements.drop_duplicates(
            ["stock_code", "announcement_id"]
        ).sort_values(["stock_code", "announcement_date", "announcement_id"])
    announcements.to_csv(ANNOUNCEMENTS, index=False, encoding="utf-8-sig")
    statuses = pd.DataFrame(status_rows).sort_values("stock_code")
    statuses.to_csv(STATUS, index=False, encoding="utf-8-sig")
    print("companies", len(companies))
    print("successful", statuses["query_status"].eq("检索完成").sum())
    print("failed", (~statuses["query_status"].eq("检索完成")).sum())
    print("announcement_rows", len(announcements))
    print("codes_with_announcements", announcements["stock_code"].nunique())


if __name__ == "__main__":
    main()
