#!/usr/bin/env python3
"""Apply only manually verified legal-entity name relationships to annual candidates."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from expand_leading_firm_years import EXPANSION


ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "outputs" / "龙头企业_人工名称关系核实规则_v1.csv"
REVIEW = ROOT / "outputs" / "龙头企业_名称关系待人工复核_v1.csv"
EVENT_OUT = ROOT / "outputs" / "龙头企业_人工名称关系已核实事件_v1.csv"
EXACT_YEARS = ROOT / "outputs" / "龙头企业公司年份_当前法人精确匹配候选_v1.csv"
MASTER = ROOT / "outputs" / "上市公司法人全称主表_交易所当前信息_v1.csv"
YEAR_OUT = ROOT / "outputs" / "龙头企业公司年份_身份关系已核实候选_v2.csv"
PRELIST_OUT = ROOT / "outputs" / "龙头企业公司年份_人工关系上市前排除_v1.csv"


def join_unique(values) -> str:
    return " | ".join(dict.fromkeys(str(v) for v in values if pd.notna(v) and str(v)))


def main() -> None:
    rules = pd.read_csv(RULES, dtype=str)
    review = pd.read_csv(REVIEW, dtype=str)
    verified = review.merge(
        rules,
        on=["stock_code", "listed_legal_full_name", "official_list_name"],
        how="inner",
        validate="many_to_one",
    )
    verified["leading_firm_direct_match"] = verified["identity_decision"].map(
        {"direct_same_legal_entity": "1"}
    ).fillna("0")
    verified.to_csv(EVENT_OUT, index=False, encoding="utf-8-sig")

    direct = verified[verified["identity_decision"] == "direct_same_legal_entity"].copy()
    annual = []
    for row in direct.to_dict("records"):
        for year in EXPANSION.get((row["list_year"], row["event_type"]), []):
            annual.append({
                "stock_code": row["stock_code"],
                "year": str(year),
                "listed_legal_full_name": row["listed_legal_full_name"],
                "official_name_evidence": row["official_list_name"],
                "evidence_event_year": row["list_year"],
                "evidence_event_type": row["event_type"],
                "moa_source_url": row["moa_source_url"],
                "identity_source_url": row["primary_source_url"],
                "identity_basis": row["decision_reason"],
            })
    annual = pd.DataFrame(annual)
    master = pd.read_csv(MASTER, dtype=str)[
        ["stock_code", "exchange", "short_name", "list_date", "source_url"]
    ].drop_duplicates("stock_code")
    annual = annual.merge(master, on="stock_code", how="left", validate="many_to_one")
    list_year = pd.to_numeric(annual["list_date"].str.slice(0, 4), errors="coerce")
    panel_year = pd.to_numeric(annual["year"], errors="coerce")
    annual["listed_by_year_end"] = (list_year <= panel_year).map({True: "1", False: "0"})
    annual.loc[list_year.isna(), "listed_by_year_end"] = "待核实"
    group_columns = ["stock_code", "year", "listed_legal_full_name", "exchange", "short_name", "list_date"]
    value_columns = [
        "official_name_evidence", "evidence_event_year", "evidence_event_type",
        "moa_source_url", "identity_source_url", "identity_basis", "source_url",
        "listed_by_year_end",
    ]
    annual = annual.groupby(group_columns, as_index=False).agg({column: join_unique for column in value_columns})
    annual[annual["listed_by_year_end"] == "1"].to_csv(
        PRELIST_OUT.with_name("龙头企业公司年份_人工关系可用候选_v1.csv"),
        index=False, encoding="utf-8-sig"
    )
    annual[annual["listed_by_year_end"] != "1"].to_csv(
        PRELIST_OUT, index=False, encoding="utf-8-sig"
    )

    exact = pd.read_csv(EXACT_YEARS, dtype=str).rename(
        columns={"legal_full_name": "listed_legal_full_name"}
    )
    exact_base = exact[[
        "stock_code", "year", "listed_legal_full_name", "exchange", "short_name", "list_date",
        "official_name_normalized", "evidence_event_year", "evidence_event_type",
        "evidence_source_url", "source_url",
    ]].rename(columns={
        "official_name_normalized": "official_name_evidence",
        "evidence_source_url": "moa_source_url",
    })
    exact_base["identity_source_url"] = exact_base["source_url"]
    exact_base["identity_basis"] = "当前交易所法人全称与官方名单标准化后完全一致"
    exact_base["listed_by_year_end"] = "1"
    manual_usable = annual[annual["listed_by_year_end"] == "1"][exact_base.columns]
    combined = pd.concat([exact_base, manual_usable], ignore_index=True)
    combined = combined.groupby(
        ["stock_code", "year", "listed_legal_full_name", "exchange", "short_name", "list_date"],
        as_index=False,
    ).agg({column: join_unique for column in [
        "official_name_evidence", "evidence_event_year", "evidence_event_type",
        "moa_source_url", "source_url", "identity_source_url", "identity_basis",
        "listed_by_year_end",
    ]})
    combined["leading_firm_it_candidate"] = "1"
    combined["final_status"] = "身份关系已核实候选；ST、退市时点及资格缺口仍待处理"
    combined.sort_values(["stock_code", "year"]).to_csv(YEAR_OUT, index=False, encoding="utf-8-sig")
    print("verified_event_rows", len(verified))
    print("verified_direct_event_rows", len(direct))
    print("manual_usable_company_years", len(manual_usable))
    print("combined_company_year_candidates", len(combined))
    print("combined_unique_codes", combined["stock_code"].nunique())


if __name__ == "__main__":
    main()
