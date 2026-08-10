#!/usr/bin/env python3
"""Build historical fast-review batch 03 from annual-report revenue tables."""
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v12_跨年快速复核第二批.csv"
OUTPUT = ROOT / "outputs" / "跨年快速复核第三批_6家公司24条_v1.csv"

# business, conservative direct-agriculture revenue, consolidated revenue
VERIFIED = {
    "300511": {
        2016: ("食用菌种植", "985313102.69", "998677031.84"),
        2017: ("食用菌种植", "1317961606.28", "1330283904.69"),
        2018: ("食用菌种植", "1786449684.19", "1846625656.23"),
        2019: ("食用菌种植", "1945935776.25", "1964574723.12"),
        2020: ("食用菌种植", "2179627097.78", "2202185873.52"),
        2021: ("食用菌种植", "2026974350.39", "2062828781.84"),
    },
    "000798": {
        2013: ("远洋捕捞", "227913798.54", "296131021.96"),
        2014: ("远洋捕捞", "343870250.72", "378756392.67"),
        2015: ("远洋捕捞", "344229783.68", "521523302.38"),
        2016: ("远洋捕捞", "352892543.23", "534459692.46"),
        2017: ("远洋捕捞", "603260705.75", "748144656.79"),
        2018: ("远洋捕捞", "501718433.05", "626212925.18"),
        2019: ("远洋捕捞", "430206787.57", "578668995.10"),
        2020: ("远洋捕捞", "355857733.00", "445286551.21"),
        2021: ("远洋捕捞", "357713072.13", "462390686.83"),
    },
    "300967": {
        2021: ("蛋鸡养殖", "713917595.85", "714367715.43"),
    },
    "300970": {
        2021: ("食用菌种植", "578083609.15", "578088209.15"),
    },
    "001201": {
        2021: ("生猪养殖", "942113022.68", "1051843098.16"),
    },
    "002772": {
        2016: ("食用菌种植", "585018459.38", "585018459.38"),
        2017: ("食用菌种植", "739792782.58", "739792782.58"),
        2018: ("食用菌种植", "926432056.86", "926432056.86"),
        2019: ("食用菌种植", "1155832460.49", "1155832460.49"),
        2020: ("食用菌种植", "1483178491.71", "1483178491.71"),
        2021: ("食用菌种植", "1556146725.49", "1556146725.49"),
    },
}


def share(numerator: str, total: str) -> Decimal:
    return (Decimal(numerator) / Decimal(total)).quantize(
        Decimal("0.00000001"), rounding=ROUND_HALF_UP
    )


def main() -> None:
    source = pd.read_csv(SOURCE, dtype={"股票代码": str})
    keys = {(code, year) for code, years in VERIFIED.items() for year in years}
    assert len(keys) == 24
    selected = source[
        source.apply(lambda row: (row["股票代码"], int(row["年份"])) in keys, axis=1)
    ].copy()
    assert len(selected) == 24
    assert not selected["复核状态"].str.startswith("已人工复核", na=False).any()

    rows = []
    for _, row in selected.sort_values(["股票代码", "年份"]).iterrows():
        code, year = row["股票代码"], int(row["年份"])
        business, numerator, total = VERIFIED[code][year]
        ratio = share(numerator, total)
        assert ratio >= Decimal("0.50")
        pages = str(row["年报主营业务候选PDF页序号"])
        evidence_page = pages.split("|")[0] if pages != "nan" else str(
            row["年报主营业务表PDF页序号"]
        )
        rows.append({
            "股票代码": code, "公司全称": row["公司全称"], "年份": year,
            "行业分类代码": row["行业分类代码"], "行业分类名称": row["行业分类名称"],
            "直接涉农业务_保守不重叠口径": business,
            "直接涉农业务营业收入_元": numerator, "公司营业收入_元": total,
            "直接涉农收入占比": f"{ratio:.8f}", "严格样本结论": "是",
            "扩展样本结论": "是", "边界样本结论": "否",
            "是否存在分部收入重叠": "否（只使用一个分行业维度）",
            "复核说明": "当年官方年报分行业直接农业营业收入超过公司合并营业收入50%；未叠加分产品、地区或销售模式。",
            "年报主营业务证据PDF页序号": evidence_page,
            "公司营业收入证据PDF页序号": row["利润表PDF页序号"],
            "年报链接": row["年报链接"], "记录类型": "本次新增跨年快速复核",
            "复核日期": "2026-08-10",
        })
    result = pd.DataFrame(rows)
    assert len(result) == 24 and not result.duplicated(["股票代码", "年份"]).any()
    assert result["严格样本结论"].eq("是").all()
    result.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("batch03 rows=24; companies=6; strict yes=24; expanded yes=24")


if __name__ == "__main__":
    main()
