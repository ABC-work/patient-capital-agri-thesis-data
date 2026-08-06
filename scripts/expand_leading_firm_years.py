#!/usr/bin/env python3
"""Expand verified MOA events into conservative year-end qualification sets.

The output is an official-name layer, not the final listed-company variable. Years
whose intervening official company-level monitoring result is missing are omitted.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
EVENTS = ROOT / "outputs" / "农业产业化国家重点龙头企业官方名单_结构化_v1.csv"
MASTER = ROOT / "outputs" / "上市公司法人全称主表_交易所当前信息_v1.csv"
OUT_NAMES = ROOT / "outputs" / "龙头企业资格年度展开_官方名称层_v1.csv"
OUT_EXACT = ROOT / "outputs" / "龙头企业公司年份_当前法人精确匹配候选_v1.csv"
OUT_PRELIST = ROOT / "outputs" / "龙头企业公司年份_上市前命中排除_v1.csv"


def normalize(text: str) -> str:
    return re.sub(r"[\s*]", "", str(text)).replace("(", "（").replace(")", "）")


# Each source list is carried only through years for which the event history is
# closed by an available company-level official result.
EXPANSION = {
    ("2014", "monitor_pass"): [2014, 2015],
    ("2018", "monitor_pass"): [2018, 2019],
    ("2019", "recognition"): [2019, 2020, 2021, 2022],
    ("2020", "monitor_pass"): [2020, 2021, 2022],
    ("2020", "replacement"): [2020, 2021, 2022],
    ("2021", "recognition"): [2021, 2022, 2023],
    ("2023", "monitor_pass"): [2023],
    ("2023", "replacement"): [2023],
}


def join_unique(values) -> str:
    return " | ".join(dict.fromkeys(str(v) for v in values if pd.notna(v) and str(v)))


def main() -> None:
    events = pd.read_csv(EVENTS, dtype=str)
    expanded = []
    for row in events.to_dict("records"):
        years = EXPANSION.get((row["list_year"], row["event_type"]), [])
        for year in years:
            expanded.append({
                "year": str(year),
                "official_name_normalized": normalize(row["official_name_normalized"]),
                "evidence_event_year": row["list_year"],
                "evidence_event_type": row["event_type"],
                "evidence_list_type": row["list_type"],
                "evidence_document_number": row["document_number"],
                "evidence_document_date": row["document_date"],
                "evidence_source_url": row["source_url"],
            })
    frame = pd.DataFrame(expanded)
    grouped = (
        frame.groupby(["year", "official_name_normalized"], as_index=False, sort=True)
        .agg({column: join_unique for column in frame.columns if column not in {"year", "official_name_normalized"}})
    )
    grouped["name_level_qualification"] = "1"
    grouped["annual_timing_rule"] = "基准按年末已生效的正式文件；年末新认定另做下一完整年度起算稳健性"
    grouped["coverage_status"] = "官方事件集合可构建；尚未完成上市法人历史名称映射"
    grouped.to_csv(OUT_NAMES, index=False, encoding="utf-8-sig")

    master = pd.read_csv(MASTER, dtype=str).fillna("")
    master["official_name_normalized"] = master["legal_full_name"].map(normalize)
    exact = grouped.merge(master, on="official_name_normalized", how="inner", validate="many_to_many")
    list_year = pd.to_numeric(exact["list_date"].str.slice(0, 4), errors="coerce")
    panel_year = pd.to_numeric(exact["year"], errors="coerce")
    exact["listed_by_year_end"] = (list_year <= panel_year).map({True: "1", False: "0"})
    exact.loc[list_year.isna(), "listed_by_year_end"] = "待核实"
    exact["leading_firm_it_candidate"] = exact["listed_by_year_end"].map({"1": "1"}).fillna("0")
    exact["final_variable_status"] = "候选；须核对该年度法人名称、退市时点及主体关系"
    exact.loc[exact["listed_by_year_end"] == "0", "final_variable_status"] = "排除：该公司截至该年末尚未上市"
    exact.loc[exact["listed_by_year_end"] == "待核实", "final_variable_status"] = "待核实：交易所主表缺上市日期"
    columns = [
        "stock_code", "exchange", "short_name", "legal_full_name", "year",
        "official_name_normalized", "listed_by_year_end", "leading_firm_it_candidate", "final_variable_status",
        "evidence_event_year", "evidence_event_type", "evidence_list_type",
        "evidence_document_number", "evidence_document_date", "evidence_source_url",
        "annual_timing_rule", "coverage_status", "list_date", "source_url", "retrieved_date",
    ]
    eligible = exact[exact["listed_by_year_end"] == "1"]
    excluded = exact[exact["listed_by_year_end"] != "1"]
    eligible[columns].sort_values(["stock_code", "year"]).to_csv(
        OUT_EXACT, index=False, encoding="utf-8-sig"
    )
    excluded[columns].sort_values(["stock_code", "year"]).to_csv(
        OUT_PRELIST, index=False, encoding="utf-8-sig"
    )

    print("official_name_year_rows", len(grouped))
    print("years", grouped.groupby("year").size().to_dict())
    print("listed_current_legal_exact_candidate_rows", len(eligible))
    print("listed_current_legal_exact_unique_codes", eligible["stock_code"].nunique())
    print("pre_listing_or_unknown_rows_excluded", len(excluded))


if __name__ == "__main__":
    main()
