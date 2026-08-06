#!/usr/bin/env python3
"""Build a traceable union of industry and verified-identity leading-firm entries."""

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
INDUSTRY = OUT / "证监会农林牧渔业年度候选面板_已核实年份.csv"
LEADING = OUT / "龙头企业公司年份_身份关系已核实候选_v2.csv"
LEGAL = OUT / "上市公司法人全称主表_交易所当前信息_v1.csv"
HISTORICAL = OUT / "历史退市证券法人名称核实_v1.csv"
ST_INTERVALS = OUT / "ST风险警示区间核实_v1.csv"
DELISTING_INTERVALS = OUT / "退市整理期区间核实_v1.csv"
RESULT = OUT / "涉农样本入口候选池_行业与龙头并集_v1.csv"
STATUS = OUT / "涉农样本入口候选池_年度状态_v1.csv"


def main() -> None:
    industry = pd.read_csv(INDUSTRY, dtype=str).rename(
        columns={
            "年份": "year",
            "股票代码": "stock_code",
            "证券简称_当期": "industry_period_short_name",
            "来源期次": "industry_source_period",
            "行业大类代码": "industry_code",
            "行业大类名称": "industry_name",
            "ST标记_当期": "industry_period_st_flag",
            "来源机构": "industry_source_agency",
            "分类标准": "industry_classification_standard",
            "本地原始文件": "industry_local_source_file",
            "样本状态": "industry_sample_status",
        }
    )
    industry["industry_entry_candidate"] = "1"

    leading = pd.read_csv(LEADING, dtype=str).rename(
        columns={
            "leading_firm_it_candidate": "leading_identity_verified_candidate",
            "final_status": "leading_candidate_status",
        }
    )
    leading_columns = [
        "stock_code", "year", "listed_legal_full_name", "exchange", "short_name",
        "list_date", "official_name_evidence", "evidence_event_year",
        "evidence_event_type", "moa_source_url", "source_url",
        "identity_source_url", "identity_basis", "listed_by_year_end",
        "leading_identity_verified_candidate", "leading_candidate_status",
    ]
    leading = leading[leading_columns]

    merged = industry.merge(leading, on=["stock_code", "year"], how="outer")
    for column in ["industry_entry_candidate", "leading_identity_verified_candidate"]:
        merged[column] = merged[column].fillna("0")

    legal = pd.read_csv(LEGAL, dtype=str)[
        ["stock_code", "legal_full_name", "short_name", "exchange", "list_date"]
    ].drop_duplicates("stock_code")
    legal = legal.rename(
        columns={
            "legal_full_name": "master_current_legal_full_name",
            "short_name": "master_current_short_name",
            "exchange": "master_exchange",
            "list_date": "master_list_date",
        }
    )
    merged = merged.merge(legal, on="stock_code", how="left")

    historical = pd.read_csv(HISTORICAL, dtype=str)
    merged = merged.merge(historical, on=["stock_code", "year"], how="left")

    merged["current_legal_full_name"] = (
        merged["listed_legal_full_name"]
        .fillna(merged["master_current_legal_full_name"])
        .fillna(merged["historical_legal_full_name"])
    )
    merged["current_short_name"] = merged["short_name"].fillna(
        merged["master_current_short_name"]
    )
    merged["exchange_final"] = merged["exchange"].fillna(merged["master_exchange"])
    merged["list_date_final"] = merged["list_date"].fillna(merged["master_list_date"])
    merged["legal_name_review_status"] = "交易所当前法人主表已覆盖"
    historical_filled = merged["historical_legal_full_name"].notna()
    merged.loc[historical_filled, "legal_name_review_status"] = "当年法人全称已由历史法定披露核实"
    missing_legal = merged["current_legal_full_name"].isna()
    merged.loc[missing_legal, "legal_name_review_status"] = (
        "当前交易所法人主表未覆盖；须从当年年报核实历史法人全称及退市时点"
    )

    both = (merged["industry_entry_candidate"] == "1") & (
        merged["leading_identity_verified_candidate"] == "1"
    )
    industry_only = (merged["industry_entry_candidate"] == "1") & ~both
    merged["entry_basis"] = "龙头企业身份核实候选"
    merged.loc[industry_only, "entry_basis"] = "行业分类候选"
    merged.loc[both, "entry_basis"] = "行业分类候选+龙头企业身份核实候选"

    merged["st_review_status"] = "待从公司年度证券状态来源核实"
    has_industry_st = merged["industry_period_st_flag"].notna()
    merged.loc[has_industry_st, "st_review_status"] = (
        "已由当期行业分类证券简称标记：" + merged.loc[has_industry_st, "industry_period_st_flag"]
    )
    merged["entry_pool_status"] = (
        "入口候选，非最终样本；仍须复核主营业务、涉农收入占比、ST/退市状态及核心变量缺失"
    )

    intervals = pd.read_csv(ST_INTERVALS, dtype=str)
    merged["st_any_time_in_year_verified"] = ""
    merged["st_at_year_end_verified"] = ""
    merged["st_interval_source_url"] = ""
    merged["st_interval_end_source_url"] = ""
    merged["st_interval_status"] = ""
    for interval in intervals.to_dict("records"):
        start = pd.Timestamp(interval["start_date"])
        end = (
            pd.Timestamp(interval["end_date"])
            if pd.notna(interval["end_date"]) and interval["end_date"]
            else pd.Timestamp("2099-12-31")
        )
        code_rows = merged["stock_code"].eq(interval["stock_code"])
        years = merged["year"].astype(int)
        year_start = pd.to_datetime(years.astype(str) + "-01-01")
        year_end = pd.to_datetime(years.astype(str) + "-12-31")
        # end_date is the first effective date without the warning (half-open interval).
        overlaps = code_rows & (start <= year_end) & (end > year_start)
        at_year_end = code_rows & (start <= year_end) & (end > year_end)
        merged.loc[overlaps, "st_any_time_in_year_verified"] = "是"
        merged.loc[at_year_end, "st_at_year_end_verified"] = "是"
        ended_before_year_end = overlaps & ~at_year_end & pd.notna(interval["end_date"])
        merged.loc[ended_before_year_end, "st_at_year_end_verified"] = "否"
        merged.loc[overlaps, "st_interval_source_url"] = interval["start_source_url"]
        merged.loc[overlaps, "st_interval_end_source_url"] = (
            interval["end_source_url"] if pd.notna(interval["end_source_url"]) else ""
        )
        merged.loc[overlaps, "st_interval_status"] = interval["interval_status"]

    merged["st_audit_status"] = "年度ST区间待核实"
    has_verified_overlap = merged["st_any_time_in_year_verified"].eq("是")
    merged.loc[has_verified_overlap, "st_audit_status"] = "已由法定公告核实本年存在ST风险警示"
    industry_snapshot_is_st = merged["industry_period_st_flag"].eq("是")
    merged.loc[industry_snapshot_is_st & ~has_verified_overlap, "st_audit_status"] = (
        "已有行业分类时点ST状态；完整年度区间仍待核实"
    )

    delisting_intervals = pd.read_csv(DELISTING_INTERVALS, dtype=str)
    merged["delisting_arrangement_in_year_verified"] = ""
    merged["delisting_arrangement_source_url"] = ""
    years = merged["year"].astype(int)
    year_start = pd.to_datetime(years.astype(str) + "-01-01")
    year_end = pd.to_datetime(years.astype(str) + "-12-31")
    for interval in delisting_intervals.to_dict("records"):
        start = pd.Timestamp(interval["delisting_arrangement_start_date"])
        end = pd.Timestamp(interval["delisting_arrangement_end_date"])
        overlaps = (
            merged["stock_code"].eq(interval["stock_code"])
            & (start <= year_end)
            & (end >= year_start)
        )
        merged.loc[overlaps, "delisting_arrangement_in_year_verified"] = "是"
        merged.loc[overlaps, "delisting_arrangement_source_url"] = interval[
            "arrangement_source_url"
        ]

    keep = [
        "stock_code", "year", "current_legal_full_name", "current_short_name",
        "exchange_final", "list_date_final", "legal_name_review_status", "entry_basis",
        "name_source_url", "name_effective_basis", "delisting_date",
        "delisting_source_url",
        "industry_entry_candidate", "industry_period_short_name",
        "industry_source_period", "industry_code", "industry_name",
        "industry_period_st_flag", "industry_source_agency",
        "industry_classification_standard", "industry_local_source_file",
        "industry_sample_status", "leading_identity_verified_candidate",
        "official_name_evidence", "evidence_event_year", "evidence_event_type",
        "moa_source_url", "identity_source_url", "identity_basis",
        "leading_candidate_status", "st_review_status", "entry_pool_status",
        "st_any_time_in_year_verified", "st_at_year_end_verified",
        "st_interval_source_url", "st_interval_end_source_url",
        "st_interval_status", "st_audit_status",
        "delisting_arrangement_in_year_verified",
        "delisting_arrangement_source_url",
    ]
    merged = merged[keep].sort_values(["year", "stock_code"])
    assert not merged.duplicated(["stock_code", "year"]).any()
    merged.to_csv(RESULT, index=False, encoding="utf-8-sig")

    status = (
        merged.groupby("year", as_index=False)
        .agg(
            union_rows=("stock_code", "size"),
            unique_codes=("stock_code", "nunique"),
            industry_entries=("industry_entry_candidate", lambda x: (x == "1").sum()),
            leading_entries=(
                "leading_identity_verified_candidate", lambda x: (x == "1").sum()
            ),
            st_marked_from_industry=("industry_period_st_flag", lambda x: (x == "是").sum()),
            st_any_time_verified=("st_any_time_in_year_verified", lambda x: (x == "是").sum()),
            st_at_year_end_verified=("st_at_year_end_verified", lambda x: (x == "是").sum()),
            delisting_arrangement_verified=("delisting_arrangement_in_year_verified", lambda x: (x == "是").sum()),
            legal_name_pending=("legal_name_review_status", lambda x: x.str.startswith("当前交易所法人主表未覆盖").sum()),
        )
    )
    status["industry_classification_status"] = status["year"].map(
        lambda year: "逐公司行业分类待核实，未插值" if year == "2022" else "使用已核实来源"
    )
    status["leading_qualification_status"] = status["year"].map(
        lambda year: (
            "企业级官方资格基准缺失，未推算"
            if year in {"2013", "2016", "2017"}
            else "身份关系已核实候选，资格取消事件及证券状态仍待审计"
        )
    )
    status.to_csv(STATUS, index=False, encoding="utf-8-sig")
    print("union_rows", len(merged))
    print("unique_codes", merged["stock_code"].nunique())
    print("duplicate_code_year", merged.duplicated(["stock_code", "year"]).sum())
    print(status.to_string(index=False))


if __name__ == "__main__":
    main()
