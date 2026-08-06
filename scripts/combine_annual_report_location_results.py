#!/usr/bin/env python3
"""Combine year-specific annual-report evidence-location outputs and audit coverage."""

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
RESULT = OUT / "年报主营业务与收入页定位_2013_2023_v1.csv"
GAPS = OUT / "年报主营业务与收入页定位_待人工补核_v1.csv"


def main() -> None:
    frames = []
    for year in range(2013, 2024):
        path = OUT / f"年报主营业务与收入页定位_{year}_v1.csv"
        frames.append(pd.read_csv(path, dtype=str).fillna(""))
    result = pd.concat(frames, ignore_index=True).sort_values(["year", "stock_code"])
    assert len(result) == 958
    assert not result.duplicated(["stock_code", "year"]).any()
    result.to_csv(RESULT, index=False, encoding="utf-8-sig")

    gaps = result[
        result["business_section_primary_pdf_page"].eq("")
        | result["income_statement_pdf_pages"].eq("")
    ].copy()
    gaps["gap_type"] = ""
    no_business = gaps["business_section_primary_pdf_page"].eq("")
    no_income = gaps["income_statement_pdf_pages"].eq("")
    gaps.loc[no_business & ~no_income, "gap_type"] = "主营业务收入表页待补定位"
    gaps.loc[~no_business & no_income, "gap_type"] = "合并利润表页待补定位"
    gaps.loc[no_business & no_income, "gap_type"] = "主营业务收入表及合并利润表页均待补定位"
    gaps.to_csv(GAPS, index=False, encoding="utf-8-sig")

    print("rows", len(result))
    print("unique_company_years", result.drop_duplicates(["stock_code", "year"]).shape[0])
    print("pdf_success", result.pdf_parse_status.eq("PDF文本提取成功").sum())
    print("business_section_found", result.business_section_primary_pdf_page.ne("").sum())
    print("income_statement_found", result.income_statement_pdf_pages.ne("").sum())
    print("gap_rows", len(gaps))
    print(gaps.groupby(["year", "gap_type"]).size().to_string())


if __name__ == "__main__":
    main()
