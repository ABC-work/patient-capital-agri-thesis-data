#!/usr/bin/env python3
"""Build the traceable annual-report business/revenue manual-review worktable."""

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
LOCATIONS = OUT / "年报主营业务与收入页定位_2013_2023_v1.csv"
ENTRIES = OUT / "涉农样本入口候选池_行业与龙头并集_v1.csv"
RESULT = OUT / "涉农候选公司年份_年报主营业务复核工作表_v1.csv"


def main() -> None:
    locations = pd.read_csv(LOCATIONS, dtype=str).fillna("")
    entries = pd.read_csv(ENTRIES, dtype=str).fillna("")
    entry_fields = entries[
        [
            "stock_code", "year", "industry_code", "industry_name",
            "industry_entry_candidate", "leading_identity_verified_candidate",
            "st_any_time_in_year_verified", "st_at_year_end_verified",
            "delisting_arrangement_in_year_verified",
        ]
    ]
    result = locations.merge(entry_fields, on=["stock_code", "year"], how="left")
    result = result.rename(
        columns={
            "stock_code": "股票代码",
            "year": "年份",
            "current_legal_full_name": "公司全称",
            "pdf_url": "年报链接",
            "business_section_primary_pdf_page": "年报主营业务表PDF页序号",
            "business_section_pdf_pages": "年报主营业务候选PDF页序号",
            "income_statement_pdf_pages": "利润表PDF页序号",
            "business_section_evidence_excerpt": "主营业务表原文摘录",
            "income_statement_evidence_excerpt": "利润表原文摘录",
            "industry_code": "行业分类代码",
            "industry_name": "行业分类名称",
            "entry_basis": "入口依据",
            "industry_entry_candidate": "行业入口候选",
            "leading_identity_verified_candidate": "龙头身份关系已核实候选",
            "st_any_time_in_year_verified": "当年曾ST_已核实",
            "st_at_year_end_verified": "年末ST_已核实",
            "delisting_arrangement_in_year_verified": "当年退市整理期_已核实",
        }
    )
    # These fields must remain blank until the cited report pages are manually reviewed.
    for column in [
        "年报印刷页码",
        "涉农业务名称",
        "涉农业务营业收入",
        "公司营业收入",
        "涉农收入占比",
        "是否存在分部收入重叠",
        "严格样本结论",
        "扩展样本结论",
        "边界样本结论",
        "纳入或剔除理由",
    ]:
        result[column] = ""
    result["复核状态"] = "年报及业务表已定位；收入、重叠和样本结论待人工复核"
    result["口径提示"] = (
        "不得机械相加分行业与分产品；优先使用不重叠口径，无法拆分则保持待核实"
    )

    keep = [
        "股票代码", "公司全称", "年份", "行业分类代码", "行业分类名称", "入口依据",
        "行业入口候选", "龙头身份关系已核实候选", "年报链接",
        "年报主营业务表PDF页序号", "年报主营业务候选PDF页序号", "年报印刷页码",
        "利润表PDF页序号", "涉农业务名称", "涉农业务营业收入", "公司营业收入",
        "涉农收入占比", "是否存在分部收入重叠", "严格样本结论", "扩展样本结论",
        "边界样本结论", "纳入或剔除理由", "当年曾ST_已核实", "年末ST_已核实",
        "当年退市整理期_已核实", "复核状态", "口径提示", "主营业务表原文摘录",
        "利润表原文摘录", "announcement_id", "announcement_title", "publication_date",
        "pdf_parse_status", "pdf_page_count", "text_character_count",
    ]
    result = result[keep].sort_values(["年份", "股票代码"])
    assert len(result) == 958
    assert not result.duplicated(["股票代码", "年份"]).any()
    assert result["年报链接"].ne("").all()
    assert result["年报主营业务表PDF页序号"].ne("").all()
    assert result["利润表PDF页序号"].ne("").all()
    result.to_csv(RESULT, index=False, encoding="utf-8-sig")
    print("rows", len(result))
    print("unique_codes", result["股票代码"].nunique())
    print("annual_report_links_missing", result["年报链接"].eq("").sum())
    print("business_page_missing", result["年报主营业务表PDF页序号"].eq("").sum())
    print("income_statement_page_missing", result["利润表PDF页序号"].eq("").sum())
    print("manual_review_pending", result["复核状态"].str.contains("待人工复核").sum())


if __name__ == "__main__":
    main()
