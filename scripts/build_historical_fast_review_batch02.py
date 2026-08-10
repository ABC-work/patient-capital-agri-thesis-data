#!/usr/bin/env python3
"""Build the second cross-year fast-review batch (30 historical rows).

Every numerator and denominator below is transcribed from the corresponding
year's official annual-report business table and consolidated income statement.
No adjacent-year value is copied or used as a substitute.
"""
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v11_跨年快速复核试验.csv"
OUTPUT = ROOT / "outputs" / "跨年快速复核第二批_4家公司30条_v1.csv"


# (business name, conservative numerator, total revenue, strict, expanded,
#  rationale). Numerators use one non-overlapping product/industry dimension.
VERIFIED = {
    "002746": {
        2015: ("肉鸡养殖及屠宰加工", "1755788002.76", "1755788002.76", "否", "是"),
        2016: ("肉鸡养殖及屠宰加工", "2095018758.69", "2095018758.69", "否", "是"),
        2017: ("肉鸡养殖及屠宰加工", "2164000029.75", "2164000029.75", "否", "是"),
        2018: ("肉鸡养殖及屠宰加工", "2577797691.84", "2577797691.84", "否", "是"),
        2019: ("肉鸡养殖及屠宰加工", "3533387137.43", "3533387137.43", "否", "是"),
        2020: ("肉鸡养殖及屠宰加工", "3188320694.09", "3188320694.09", "否", "是"),
        2021: ("肉鸡养殖及屠宰加工", "3311775720.74", "3311775720.74", "否", "是"),
    },
    "002679": {
        2013: ("木材、种苗及林业经济作物（主营业务合计）", "165084179.62", "174263656.50", "是", "是"),
        2014: ("木材、种苗及林业经济作物（主营业务合计）", "176193042.60", "190206399.58", "是", "是"),
        2015: ("林业", "150873376.60", "198786732.91", "是", "是"),
        2016: ("林业", "113484097.38", "137628739.26", "是", "是"),
        2017: ("林业", "134301043.21", "174898144.88", "是", "是"),
        2018: ("林业（不含林业技术服务）", "148704712.08", "168492923.19", "是", "是"),
        2019: ("林业", "122658320.60", "128552232.82", "是", "是"),
        2020: ("林业", "141538235.09", "148031923.45", "是", "是"),
        2021: ("林业（原木等直接林业业务）", "189886506.97", "189886506.97", "是", "是"),
    },
    "000998": {
        2013: ("水稻、蔬菜瓜果、玉米、小麦及棉花油菜种子", "1390256633.54", "1884716266.51", "是", "是"),
        2014: ("水稻、蔬菜瓜果、玉米、小麦及棉花油菜种子", "1511241361.14", "1815424946.98", "是", "是"),
        2015: ("水稻、蔬菜瓜果、玉米及小麦种子", "1734837842.56", "2025824711.54", "是", "是"),
        2016: ("农业（水稻种子、玉米种子）", "1507451747.12", "2299410170.79", "是", "是"),
        2017: ("农业（水稻种子、玉米种子）", "2291490702.79", "3190019342.23", "是", "是"),
        2018: ("农业（水稻种子、玉米种子）", "2727716676.14", "3579717393.27", "是", "是"),
        2019: ("农业（水稻种子、玉米种子）", "2034581175.61", "3129540711.87", "是", "是"),
        2020: ("农业（水稻种子、玉米种子）", "2377886132.98", "3290527650.55", "是", "是"),
        2021: ("农业（水稻种子、玉米种子）", "2318915089.54", "3503442453.93", "是", "是"),
    },
    "002458": {
        2013: ("鸡、猪、牛奶", "495697042.08", "502875826.03", "是", "是"),
        2014: ("鸡、猪、牛奶", "833339825.23", "841921368.35", "是", "是"),
        2015: ("鸡、猪、牛奶", "592871066.56", "604290341.75", "是", "是"),
        2018: ("鸡、猪、牛奶", "1453310378.71", "1473118954.89", "是", "是"),
        2020: ("鸡、猪、牛奶", "1574681582.79", "1751036372.39", "是", "是"),
    },
}


def ratio(numerator: str, total: str) -> Decimal:
    return (Decimal(numerator) / Decimal(total)).quantize(
        Decimal("0.00000001"), rounding=ROUND_HALF_UP
    )


def main() -> None:
    source = pd.read_csv(SOURCE, dtype={"股票代码": str})
    keys = {(code, year) for code, years in VERIFIED.items() for year in years}
    assert len(keys) == 30
    selected = source[
        source.apply(lambda row: (row["股票代码"], int(row["年份"])) in keys, axis=1)
    ].copy()
    assert len(selected) == 30
    assert not selected.duplicated(["股票代码", "年份"]).any()
    assert not selected["复核状态"].str.startswith("已人工复核", na=False).any()

    rows = []
    for _, row in selected.sort_values(["股票代码", "年份"]).iterrows():
        code, year = row["股票代码"], int(row["年份"])
        business, numerator, total, strict, expanded = VERIFIED[code][year]
        share = ratio(numerator, total)
        assert share >= Decimal("0.50")
        if code == "002746":
            reason = (
                "肉鸡养殖与屠宰加工合并行业收入达到50%；该合并口径含屠宰初加工，"
                "不能据此证明直接养殖收入达到50%，故仅纳入扩展样本。"
            )
        elif code == "002458":
            reason = (
                "仅合计同一分行业维度的鸡、猪和牛奶收入，排除其他及农牧设备；"
                "直接畜牧业务保守占比超过50%。"
            )
        elif code == "002679":
            reason = "直接林业收入保守占比超过50%；未叠加其他披露维度。"
        else:
            reason = "种子等直接农业业务的保守收入占比超过50%；未叠加地区或销售模式维度。"

        pages = str(row["年报主营业务候选PDF页序号"])
        evidence_page = pages.split("|")[0] if pages != "nan" else str(
            row["年报主营业务表PDF页序号"]
        )
        rows.append({
            "股票代码": code,
            "公司全称": row["公司全称"],
            "年份": year,
            "行业分类代码": row["行业分类代码"],
            "行业分类名称": row["行业分类名称"],
            "直接涉农业务_保守不重叠口径": business,
            "直接涉农业务营业收入_元": numerator,
            "公司营业收入_元": total,
            "直接涉农收入占比": f"{share:.8f}",
            "严格样本结论": strict,
            "扩展样本结论": expanded,
            "边界样本结论": "否",
            "是否存在分部收入重叠": "否（仅取同一分行业或分产品维度；采用保守分子）",
            "复核说明": reason,
            "年报主营业务证据PDF页序号": evidence_page,
            "公司营业收入证据PDF页序号": row["利润表PDF页序号"],
            "年报链接": row["年报链接"],
            "记录类型": "本次新增跨年快速复核",
            "复核日期": "2026-08-10",
        })

    result = pd.DataFrame(rows)
    assert len(result) == 30
    assert not result.duplicated(["股票代码", "年份"]).any()
    assert (result["直接涉农收入占比"].astype(float) >= 0.50).all()
    assert result["严格样本结论"].value_counts().to_dict() == {"是": 23, "否": 7}
    assert result["扩展样本结论"].eq("是").all()
    result.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("batch rows=30; companies=4; strict yes=23; expanded yes=30")


if __name__ == "__main__":
    main()
