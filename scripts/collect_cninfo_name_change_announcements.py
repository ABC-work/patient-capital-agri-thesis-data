#!/usr/bin/env python3
"""Collect CNINFO name-change announcement metadata for leading-firm candidates."""

from __future__ import annotations

import html
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "outputs" / "龙头企业公司年份_当前法人精确匹配候选_v1.csv"
OUT = ROOT / "outputs" / "龙头企业候选_巨潮公司名称变更公告索引_v1.csv"
STATUS_OUT = ROOT / "outputs" / "龙头企业候选_公司名称变更检索状态_v1.csv"
RETRIEVED = "2026-08-06"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (research; source-audit)",
    "Referer": "https://www.cninfo.com.cn/",
    "X-Requested-With": "XMLHttpRequest",
}


def request(method: str, url: str, *, params=None, data=None, attempts: int = 5):
    last = None
    for attempt in range(attempts):
        try:
            response = requests.request(
                method, url, params=params, data=data, headers=HEADERS, timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            last = exc
            time.sleep(0.8 * (attempt + 1))
    raise RuntimeError(f"request failed: {url}: {last}")


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", html.unescape(text or ""))


def query_company(company: dict[str, str]) -> tuple[list[dict[str, str]], dict[str, str]]:
    code = company["stock_code"]
    search = request(
        "POST",
        "https://www.cninfo.com.cn/new/information/topSearch/query",
        params={"keyWord": code, "maxNum": "10"},
    )
    exact = [item for item in search if item.get("code") == code]
    if not exact:
        return [], {**company, "search_status": "未取得证券组织代码", "announcement_count": ""}
    org_id = exact[0].get("orgId", "")
    column = "sse" if company["exchange"] == "上海证券交易所" else "szse"
    payload = {
        "pageNum": "1",
        "pageSize": "100",
        "column": column,
        "tabName": "fulltext",
        "stock": f"{code},{org_id}",
        "searchkey": "变更公司名称",
        # The legal-name master is current as of retrieval, so post-sample name
        # changes are needed to connect a 2013-2023 historical name to that master.
        "seDate": "1990-01-01~2026-08-06",
        "isHLtitle": "true",
    }
    result = request(
        "POST", "https://www.cninfo.com.cn/new/hisAnnouncement/query", data=payload
    )
    announcements = []
    for item in result.get("announcements") or []:
        adjunct = item.get("adjunctUrl") or ""
        announcements.append({
            "stock_code": code,
            "exchange": company["exchange"],
            "current_short_name": company["short_name"],
            "current_legal_full_name": company["legal_full_name"],
            "org_id": org_id,
            "announcement_id": item.get("announcementId") or "",
            "announcement_title": strip_html(item.get("announcementTitle") or ""),
            "announcement_sec_name": item.get("secName") or "",
            "announcement_date": time.strftime(
                "%Y-%m-%d", time.gmtime((item.get("announcementTime") or 0) / 1000)
            ),
            "pdf_url": f"https://static.cninfo.com.cn/{adjunct}" if adjunct else "",
            "query_keyword": "变更公司名称",
            "retrieved_date": RETRIEVED,
            "review_status": "待读取公告正文并提取变更前后法人全称及生效日",
        })
    status = {
        **company,
        "org_id": org_id,
        "search_status": "检索完成",
        "announcement_count": str(len(announcements)),
        "retrieved_date": RETRIEVED,
    }
    return announcements, status


def main() -> None:
    candidates = pd.read_csv(INPUT, dtype=str)
    companies = (
        candidates[["stock_code", "exchange", "short_name", "legal_full_name"]]
        .drop_duplicates("stock_code")
        .sort_values("stock_code")
        .to_dict("records")
    )
    announcements: list[dict[str, str]] = []
    statuses: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(query_company, company): company for company in companies}
        for future in as_completed(futures):
            company = futures[future]
            try:
                rows, status = future.result()
            except Exception as exc:
                rows = []
                status = {
                    **company,
                    "org_id": "",
                    "search_status": f"请求失败：{exc}",
                    "announcement_count": "",
                    "retrieved_date": RETRIEVED,
                }
            announcements.extend(rows)
            statuses.append(status)

    announcement_columns = [
        "stock_code", "exchange", "current_short_name", "current_legal_full_name",
        "org_id", "announcement_id", "announcement_title", "announcement_sec_name",
        "announcement_date", "pdf_url", "query_keyword", "retrieved_date", "review_status",
    ]
    pd.DataFrame(announcements, columns=announcement_columns).drop_duplicates(
        ["stock_code", "announcement_id"]
    ).sort_values(["stock_code", "announcement_date"]).to_csv(
        OUT, index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(statuses).sort_values("stock_code").to_csv(
        STATUS_OUT, index=False, encoding="utf-8-sig"
    )
    print("companies", len(companies))
    print("successful", sum(row["search_status"] == "检索完成" for row in statuses))
    print("announcement_rows", len(announcements))
    print("codes_with_announcements", len({row["stock_code"] for row in announcements}))


if __name__ == "__main__":
    main()
