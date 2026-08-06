#!/usr/bin/env python3
"""Screen issuer-name-change timing against the earliest exact MOA name event."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
ANN = ROOT / "outputs" / "龙头企业候选_巨潮公司名称变更公告索引_v1.csv"
SEARCH = ROOT / "outputs" / "龙头企业候选_公司名称变更检索状态_v1.csv"
EXACT = ROOT / "outputs" / "龙头企业_上市公司法人精确匹配_v1.csv"
OUT = ROOT / "outputs" / "龙头企业候选_法人名称变更风险筛查_v1.csv"

RELATED_TERMS = (
    "子公司", "孙公司", "控股股东", "公司股东", "股东名称", "审计机构",
    "会计师事务所", "担保人", "募投", "项目名称", "债券", "合资公司",
    "金圣方", "中国水产(集团)总公司", "白杨酒厂",
)
PROPOSAL_TERMS = ("拟变更", "董事会审议")


def classify(title: str) -> str:
    if any(term in title for term in RELATED_TERMS):
        return "非上市公司本体名称变更"
    if "英文名称" in title:
        return "仅英文名称事项"
    if any(term in title for term in PROPOSAL_TERMS):
        return "上市公司本体_提案或审议阶段"
    return "上市公司本体_完成或进展公告"


def join_unique(values) -> str:
    return " | ".join(dict.fromkeys(str(v) for v in values if pd.notna(v) and str(v)))


def main() -> None:
    ann = pd.read_csv(ANN, dtype=str)
    ann["metadata_class"] = ann["announcement_title"].map(classify)
    issuer = ann[ann["metadata_class"].str.startswith("上市公司本体")].copy()
    complete = issuer[issuer["metadata_class"] == "上市公司本体_完成或进展公告"]

    status = pd.read_csv(SEARCH, dtype=str)
    exact = pd.read_csv(EXACT, dtype=str)
    earliest = exact.groupby("stock_code", as_index=False).agg(
        earliest_exact_event_date=("document_date", "min"),
        exact_event_years=("list_year", join_unique),
        exact_event_types=("list_type", join_unique),
    )
    result = status.merge(earliest, on="stock_code", how="left", validate="one_to_one")

    issuer_counts = issuer.groupby("stock_code").size().rename("issuer_name_change_notice_count")
    complete_last = complete.groupby("stock_code")["announcement_date"].max().rename(
        "last_completion_or_progress_notice_date"
    )
    issuer_titles = issuer.groupby("stock_code")["announcement_title"].agg(join_unique).rename(
        "issuer_name_change_notice_titles"
    )
    issuer_urls = issuer.groupby("stock_code")["pdf_url"].agg(join_unique).rename(
        "issuer_name_change_notice_urls"
    )
    result = result.join(issuer_counts, on="stock_code").join(complete_last, on="stock_code")
    result = result.join(issuer_titles, on="stock_code").join(issuer_urls, on="stock_code")
    result["issuer_name_change_notice_count"] = result["issuer_name_change_notice_count"].fillna("0")

    def risk(row) -> str:
        if row["search_status"] != "检索完成":
            return "检索失败_待核实"
        if row["issuer_name_change_notice_count"] == "0":
            return "未检出上市公司本体名称变更公告_仍需年报抽查"
        last = row.get("last_completion_or_progress_notice_date")
        first = row.get("earliest_exact_event_date")
        if pd.notna(last) and pd.notna(first) and last > first:
            return "高风险_更名完成或进展公告晚于最早精确名单事件"
        if pd.notna(last):
            return "时点顺序通过_更名完成或进展公告不晚于最早精确名单事件"
        return "仅检出提案_最早精确名单事件已使用当前全称_仍需核实施行日"

    result["timing_screen_result"] = result.apply(risk, axis=1)
    result["scope_caution"] = (
        "当前完整批量结果检索截至2023-12-31；2024—2026仅对高可信人工候选定向补查"
    )
    columns = [
        "stock_code", "exchange", "short_name", "legal_full_name", "org_id",
        "search_status", "announcement_count", "issuer_name_change_notice_count",
        "earliest_exact_event_date", "exact_event_years", "exact_event_types",
        "last_completion_or_progress_notice_date", "timing_screen_result",
        "issuer_name_change_notice_titles", "issuer_name_change_notice_urls",
        "retrieved_date", "scope_caution",
    ]
    result[columns].sort_values("stock_code").to_csv(OUT, index=False, encoding="utf-8-sig")
    print(result["timing_screen_result"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
