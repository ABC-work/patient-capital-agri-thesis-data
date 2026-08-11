#!/usr/bin/env python3
"""Build historical fast-review batch 06 from the v15 worktable.

The batch reviews 27 company-years for 亚盛集团、好当家和北大荒.
Every value comes from the same year's official annual-report revenue table and
consolidated income statement. Industry/product dimensions are never added to
each other when they may overlap.
"""
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v15_跨年快速复核第五批.csv"
OUTPUT = ROOT / "outputs" / "跨年快速复核第六批_3家公司27条_v1.csv"

# business, stored numerator, strict numerator, expanded numerator, total,
# strict, expanded, boundary, evidence page.
VERIFIED = {
    "600108": {
        2013: ("农业种植", "2027826879.30", "2027826879.30", "2027826879.30", "2336837177.69", "是", "是", "否", "11"),
        2014: ("农业种植", "1788063222.47", "1788063222.47", "1788063222.47", "2244848820.55", "是", "是", "否", "9"),
        2015: ("农业种植", "1621364594.68", "1621364594.68", "1621364594.68", "2191117593.57", "是", "是", "否", "11"),
        2016: ("农业种植", "1596645360.48", "1596645360.48", "1596645360.48", "2068975051.65", "是", "是", "否", "11"),
        2017: ("农业种植", "1804769314.05", "1804769314.05", "1804769314.05", "2066341677.84", "是", "是", "否", "12"),
        2018: ("农业种植", "2122314619.49", "2122314619.49", "2122314619.49", "2507509619.55", "是", "是", "否", "10"),
        2019: ("农业种植", "2123311566.29", "2123311566.29", "2123311566.29", "2731512697.38", "是", "是", "否", "9"),
        2020: ("农业种植", "2522375461.89", "2522375461.89", "2522375461.89", "3132066911.75", "是", "是", "否", "10"),
        2021: ("农业种植", "2706171466.63", "2706171466.63", "2706171466.63", "3332692529.72", "是", "是", "否", "10"),
    },
    "600467": {
        2013: ("水产养殖、捕捞", "574305220.57", "574305220.57", "574305220.57", "969331768.19", "是", "是", "否", "13"),
        2014: ("水产养殖、捕捞", "580822837.78", "580822837.78", "580822837.78", "881254604.83", "是", "是", "否", "15"),
        2015: ("水产养殖、捕捞", "553486037.40", "553486037.40", "553486037.40", "986967423.93", "是", "是", "否", "10"),
        2016: ("水产养殖、捕捞及水产品初加工（扩展口径）", "1050245257.99", "505922353.67", "1050245257.99", "1059827102.15", "否", "是", "否", "12"),
        2017: ("水产养殖、捕捞及水产品初加工（扩展口径）", "1201221433.66", "563071077.96", "1201221433.66", "1207911835.31", "否", "是", "否", "12"),
        2018: ("水产养殖、捕捞", "673484572.30", "673484572.30", "673484572.30", "1149831070.21", "是", "是", "否", "12"),
        2019: ("水产养殖、捕捞", "679168146.47", "679168146.47", "679168146.47", "1226123062.59", "是", "是", "否", "12"),
        2020: ("水产养殖、捕捞", "705422086.32", "705422086.32", "705422086.32", "1230137523.72", "是", "是", "否", "12"),
        2021: ("水产养殖、捕捞", "680380539.53", "680380539.53", "680380539.53", "1253664442.81", "是", "是", "否", "12"),
    },
    "600598": {
        2013: ("农业行业（土地承包及农产品经营）", "3339524134.16", "3339524134.16", "3339524134.16", "9409513052.16", "否", "否", "是", "12"),
        2014: ("农业行业（土地承包及农产品经营）", "2771568795.49", "2771568795.49", "2771568795.49", "5113819813.61", "是", "是", "否", "9"),
        2015: ("农业行业（土地承包及农产品经营）", "2637577960.46", "2637577960.46", "2637577960.46", "3654397734.62", "是", "是", "否", "10"),
        2016: ("农业行业（土地承包及农产品经营）", "2563091960.64", "2563091960.64", "2563091960.64", "3094778574.28", "是", "是", "否", "10"),
        2017: ("农业行业（土地承包及农产品经营）", "2628324089.73", "2628324089.73", "2628324089.73", "2992414562.19", "是", "是", "否", "11"),
        2018: ("农业行业（土地承包及农产品经营）", "2697131614.70", "2697131614.70", "2697131614.70", "3264778781.25", "是", "是", "否", "11"),
        2019: ("农业行业（土地承包费）", "2675129872.46", "2675129872.46", "2675129872.46", "3111306139.60", "是", "是", "否", "12"),
        2020: ("农业行业（土地承包及农产品经营）", "2716126145.12", "2716126145.12", "2716126145.12", "3240890962.86", "是", "是", "否", "12"),
        2021: ("农业行业（土地承包及农产品经营）", "2842007878.60", "2842007878.60", "2842007878.60", "3629374113.40", "是", "是", "否", "14"),
    },
}


def ratio(numerator: str, denominator: str) -> Decimal:
    return (Decimal(numerator) / Decimal(denominator)).quantize(
        Decimal("0.00000001"), rounding=ROUND_HALF_UP
    )


def main() -> None:
    source = pd.read_csv(SOURCE, dtype={"股票代码": str})
    keys = {(code, year) for code, years in VERIFIED.items() for year in years}
    assert len(keys) == 27
    selected = source[
        source.apply(lambda row: (row["股票代码"], int(row["年份"])) in keys, axis=1)
    ].copy()
    assert len(selected) == 27
    assert not selected.duplicated(["股票代码", "年份"]).any()
    assert not selected["复核状态"].str.startswith("已人工复核", na=False).any()

    rows = []
    for _, source_row in selected.sort_values(["股票代码", "年份"]).iterrows():
        code, year = source_row["股票代码"], int(source_row["年份"])
        business, stored, strict_n, expanded_n, total, strict, expanded, boundary, page = VERIFIED[code][year]
        strict_share = ratio(strict_n, total)
        expanded_share = ratio(expanded_n, total)
        stored_share = ratio(stored, total)

        if strict == "是":
            assert strict_share >= Decimal("0.50")
        else:
            assert strict_share < Decimal("0.50")
        if expanded == "是":
            assert expanded_share >= Decimal("0.50")
        else:
            assert expanded_share < Decimal("0.50")
        if boundary == "是":
            assert Decimal("0.30") <= expanded_share < Decimal("0.50")

        if code == "600467" and year in (2016, 2017):
            reason = (
                f"养殖与捕捞严格口径占{strict_share * 100:.2f}%，未达50%；"
                "在同一分行业维度加入水产品初加工后扩展口径超过50%，未与产品维度重复相加。"
            )
        elif code == "600598" and year == 2013:
            reason = (
                f"农业行业收入占{expanded_share * 100:.2f}%，处于30%—50%；"
                "未将工业、商品流通或不同产品维度重复计入，列为边界样本。"
            )
        else:
            reason = "同一分行业维度的直接农业收入超过合并营业收入50%；未叠加产品、地区或销售模式。"

        rows.append({
            "股票代码": code,
            "公司全称": source_row["公司全称"],
            "年份": year,
            "行业分类代码": source_row["行业分类代码"],
            "行业分类名称": source_row["行业分类名称"],
            "涉农业务_保守不重叠口径": business,
            "工作表采用涉农业务营业收入_元": stored,
            "严格口径营业收入_元": strict_n,
            "扩展口径营业收入_元": expanded_n,
            "公司营业收入_元": total,
            "工作表采用涉农收入占比": f"{stored_share:.8f}",
            "严格口径收入占比": f"{strict_share:.8f}",
            "扩展口径收入占比": f"{expanded_share:.8f}",
            "严格样本结论": strict,
            "扩展样本结论": expanded,
            "边界样本结论": boundary,
            "是否存在分部收入重叠": "否（仅使用同一分行业维度）",
            "复核说明": reason,
            "年报主营业务证据PDF页序号": page,
            "公司营业收入证据PDF页序号": source_row["利润表PDF页序号"],
            "年报链接": source_row["年报链接"],
            "记录类型": "本次新增跨年快速复核",
            "复核日期": "2026-08-11",
        })

    output = pd.DataFrame(rows)
    assert len(output) == 27
    assert not output.duplicated(["股票代码", "年份"]).any()
    assert output["严格样本结论"].value_counts().to_dict() == {"是": 24, "否": 3}
    assert output["扩展样本结论"].value_counts().to_dict() == {"是": 26, "否": 1}
    assert output["边界样本结论"].value_counts().to_dict() == {"否": 26, "是": 1}
    output.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("batch06 rows=27; strict yes=24; expanded yes=26; boundary=1")


if __name__ == "__main__":
    main()
