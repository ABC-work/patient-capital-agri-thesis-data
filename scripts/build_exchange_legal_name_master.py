#!/usr/bin/env python3
"""Build a traceable exchange-sourced legal-name master and exact MOA matches."""

from __future__ import annotations

import csv
import difflib
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
OUT_MASTER = ROOT / "outputs" / "上市公司法人全称主表_交易所当前信息_v1.csv"
OUT_EXACT = ROOT / "outputs" / "龙头企业_上市公司法人精确匹配_v1.csv"
OUT_REVIEW = ROOT / "outputs" / "龙头企业_名称关系待人工复核_v1.csv"
MOA_CSV = ROOT / "outputs" / "农业产业化国家重点龙头企业官方名单_结构化_v1.csv"
INDUSTRY_CSV = ROOT / "outputs" / "证监会农林牧渔业年度候选面板_已核实年份.csv"
RETRIEVED = "2026-08-06"

HEADERS = {"User-Agent": "Mozilla/5.0 (research; source-audit)", "Referer": "https://www.szse.cn/"}


def normalize_name(text: str) -> str:
    return re.sub(r"[\s*]", "", text).replace("(", "（").replace(")", "）")


def short_core(text: str) -> str:
    text = re.sub(r"^(?:N|C|U|W|V|退市|退|\*?ST)", "", text, flags=re.I)
    text = re.sub(r"(?:退|A|B)$", "", text)
    return text.strip()


def name_skeleton(text: str) -> str:
    text = normalize_name(text)
    for token in ("有限责任公司", "股份有限公司", "集团有限公司", "有限公司", "股份公司", "集团", "公司"):
        text = text.replace(token, "")
    return re.sub(r"[（）·—-]", "", text)


def get_json(url: str, *, params=None, headers=None, attempts=5):
    last = None
    for attempt in range(attempts):
        try:
            response = requests.get(url, params=params, headers=headers or HEADERS, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            last = exc
            time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(f"GET failed after {attempts} attempts: {url}: {last}")


def sse_rows(stock_type: str) -> list[dict[str, str]]:
    url = "https://query.sse.com.cn/commonQuery.do"
    params = {
        "sqlId": "COMMON_SSE_CP_GPJCTPZ_GPLB_GP_L",
        "STOCK_TYPE": stock_type,
        "REG_PROVINCE": "",
        "CSRC_CODE": "",
        "STOCK_CODE": "",
        "COMPANY_STATUS": "2,4,5,7,8",
        "type": "inParams",
        "isPagination": "true",
        "pageHelp.cacheSize": "1",
        "pageHelp.pageSize": "5000",
        "pageHelp.pageNo": "1",
        "pageHelp.beginPage": "1",
    }
    data = get_json(url, params=params, headers={**HEADERS, "Referer": "https://www.sse.com.cn/"})
    records = data.get("pageHelp", {}).get("data") or []
    return [{
        "exchange": "上海证券交易所",
        "stock_code": item.get("A_STOCK_CODE") or item.get("COMPANY_CODE") or "",
        "short_name": item.get("COMPANY_ABBR") or "",
        "legal_full_name": item.get("FULL_NAME") or "",
        "list_date": item.get("LIST_DATE") or "",
        "current_industry": item.get("CSRC_CODE_DESC") or "",
        "exchange_status_code": item.get("STATE_CODE") or "",
        "coverage_scope": "上交所接口所列A股/科创板及指定状态",
        "source_url": "https://query.sse.com.cn/commonQuery.do?sqlId=COMMON_SSE_CP_GPJCTPZ_GPLB_GP_L",
        "retrieved_date": RETRIEVED,
    } for item in records]


def szse_page(page: int) -> list[dict[str, str]]:
    url = "https://www.szse.cn/api/report/ShowReport/data"
    data = get_json(url, params={
        "SHOWTYPE": "JSON", "CATALOGID": "1110", "TABKEY": "tab1", "PAGENO": str(page),
    })
    if not data:
        return []
    return data[0].get("data") or []


def szse_profile(code: str) -> dict[str, str]:
    url = "https://www.szse.cn/api/report/index/companyGeneralization"
    payload = get_json(url, params={"secCode": code})
    if payload.get("code") != "0" or not payload.get("data"):
        raise RuntimeError(f"No SZSE profile for {code}: {payload}")
    data = payload["data"]
    return {
        "exchange": "深圳证券交易所",
        "stock_code": data.get("agdm") or code,
        "short_name": data.get("agjc") or "",
        "legal_full_name": data.get("gsqc") or "",
        "list_date": data.get("agssrq") or "",
        "current_industry": data.get("sshymc") or "",
        "exchange_status_code": payload.get("plate") or "",
        "coverage_scope": "深交所龙头名称候选及既有行业候选代码（非全市场法人表）",
        "source_url": f"https://www.szse.cn/api/report/index/companyGeneralization?secCode={code}",
        "retrieved_date": RETRIEVED,
    }


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    moa = read_csv(MOA_CSV)
    official_names = sorted({normalize_name(row["official_name_normalized"]) for row in moa})
    industry_codes = {row["股票代码"] for row in read_csv(INDUSTRY_CSV)}

    reuse_master = "--reuse-master" in sys.argv and OUT_MASTER.exists()
    if reuse_master:
        master = read_csv(OUT_MASTER)
        code_short = {row["stock_code"]: row["short_name"] for row in master if row["exchange"] == "深圳证券交易所"}
        sse_codes = {row["stock_code"] for row in master if row["exchange"] == "上海证券交易所"}
    else:
        master = sse_rows("1") + sse_rows("8")
        sse_codes = {row["stock_code"] for row in master}

        first = get_json("https://www.szse.cn/api/report/ShowReport/data", params={
            "SHOWTYPE": "JSON", "CATALOGID": "1110", "TABKEY": "tab1", "PAGENO": "1",
        })
        page_count = int(first[0]["metadata"]["pagecount"])
        szse_items = list(first[0].get("data") or [])
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {pool.submit(szse_page, page): page for page in range(2, page_count + 1)}
            for future in as_completed(futures):
                szse_items.extend(future.result())

        code_short = {}
        for item in szse_items:
            code = item.get("agdm") or ""
            short = re.sub(r"<[^>]+>", "", item.get("agjc") or "")
            if code:
                code_short[code] = short

        profile_codes = set(code for code in industry_codes if code in code_short)
        for code, short in code_short.items():
            core = short_core(short)
            if len(core) >= 2 and any(core in name for name in official_names):
                profile_codes.add(code)

        failures = []
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {pool.submit(szse_profile, code): code for code in sorted(profile_codes)}
            for future in as_completed(futures):
                code = futures[future]
                try:
                    master.append(future.result())
                except Exception as exc:
                    failures.append((code, str(exc)))
        if failures:
            raise RuntimeError(f"SZSE profile failures: {failures[:10]} (total {len(failures)})")

    dedup = {}
    for row in master:
        if row["stock_code"] and row["legal_full_name"]:
            dedup[(row["exchange"], row["stock_code"])] = row
    master = sorted(dedup.values(), key=lambda row: (row["exchange"], row["stock_code"]))
    write_csv(OUT_MASTER, master, list(master[0]))

    legal_index = {}
    for company in master:
        legal_index.setdefault(normalize_name(company["legal_full_name"]), []).append(company)

    exact = []
    for event in moa:
        key = normalize_name(event["official_name_normalized"])
        for company in legal_index.get(key, []):
            exact.append({
                "stock_code": company["stock_code"],
                "exchange": company["exchange"],
                "listed_legal_full_name": company["legal_full_name"],
                "official_list_name": event["official_name_normalized"],
                "list_year": event["list_year"],
                "event_type": event["event_type"],
                "list_type": event["list_type"],
                "document_date": event["document_date"],
                "match_method": "上市公司当前法人全称与官方名单标准化后完全一致",
                "leading_firm_direct_match": "1",
                "temporal_caution": "当前交易所法人全称；历史年度仍须核对更名生效日",
                "exchange_source_url": company["source_url"],
                "moa_source_url": event["source_url"],
            })
    exact.sort(key=lambda row: (row["stock_code"], row["document_date"], row["list_type"]))
    if exact:
        write_csv(OUT_EXACT, exact, list(exact[0]))

    review = []
    seen = set()
    generic_cores = {"发展", "农业", "食品", "科技", "集团", "股份", "中国", "生态", "实业", "国际", "产业"}
    for company in master:
        core = short_core(company["short_name"])
        legal_norm = normalize_name(company["legal_full_name"])
        legal_skeleton = name_skeleton(company["legal_full_name"])
        fuzzy_threshold = 0.55 if company["stock_code"] in industry_codes else 0.72
        fuzzy = []
        for event in moa:
            official = normalize_name(event["official_name_normalized"])
            if official == legal_norm:
                continue
            official_skeleton = name_skeleton(event["official_name_normalized"])
            score = difflib.SequenceMatcher(None, legal_skeleton, official_skeleton).ratio()
            substring_hit = len(core) >= 2 and core not in generic_cores and core in official
            if not substring_hit and score < fuzzy_threshold:
                continue
            fuzzy.append((score, substring_hit, event))
        fuzzy.sort(key=lambda item: (item[1], item[0]), reverse=True)
        for score, substring_hit, event in fuzzy[:8]:
            key = (company["stock_code"], event["list_type"], event["official_name_normalized"])
            if key in seen:
                continue
            seen.add(key)
            review.append({
                "stock_code": company["stock_code"],
                "short_name": company["short_name"],
                "listed_legal_full_name": company["legal_full_name"],
                "official_list_name": event["official_name_normalized"],
                "list_year": event["list_year"],
                "event_type": event["event_type"],
                "candidate_basis": (
                    "证券简称核心词出现在官方名单名称中" if substring_hit
                    else f"剔除常见公司后缀后的名称相似度={score:.3f}"
                ) + "，但当前法人全称不一致",
                "review_status": "待人工核实母集团/子公司/更名/无关同名；不得直接赋值",
                "leading_firm_direct_match": "0",
                "exchange_source_url": company["source_url"],
                "moa_source_url": event["source_url"],
            })
    review.sort(key=lambda row: (row["stock_code"], row["list_year"], row["official_list_name"]))
    if review:
        write_csv(OUT_REVIEW, review, list(review[0]))

    print(json.dumps({
        "sse_master_rows": sum(row["exchange"] == "上海证券交易所" for row in master),
        "szse_profile_rows": sum(row["exchange"] == "深圳证券交易所" for row in master),
        "szse_codes_in_scope": len(code_short),
        "reused_existing_master": reuse_master,
        "exact_event_matches": len(exact),
        "exact_unique_stock_codes": len({row["stock_code"] for row in exact}),
        "manual_review_pairs": len(review),
        "sse_duplicate_codes_removed": len(sse_codes) - sum(row["exchange"] == "上海证券交易所" for row in master),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
