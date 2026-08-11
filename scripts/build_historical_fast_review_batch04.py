#!/usr/bin/env python3
"""Build batch 04: conservative seed-revenue review for 荃银高科, 2013-2021."""
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v13_跨年快速复核第三批.csv"
OUTPUT = ROOT / "outputs" / "跨年快速复核第四批_荃银高科9条_v1.csv"

# Only explicitly disclosed seed-product revenue is summed. Order grain, green
# fodder, agricultural market/property, machinery, agrochemicals, services and
# vaguely labelled "other" are excluded even where the annual report classifies
# them under agriculture.
VERIFIED = {
    2013: ("水稻、小麦、玉米、瓜菜、棉花、油菜种子", "427793892.36", "466066716.75", "19"),
    2014: ("水稻、小麦、玉米、瓜菜、棉花、油菜种子", "440352967.23", "469022777.13", "17"),
    2015: ("水稻、小麦种子（仅取年报明确列示项）", "457385237.40", "607448026.24", "13|14"),
    2016: ("水稻、玉米、小麦种子（仅取年报明确列示项）", "637545643.22", "757218222.05", "19|20"),
    2017: ("水稻、小麦、玉米、瓜菜、棉花、其他作物、油菜种子", "765060848.01", "947465898.19", "19|20"),
    2018: ("水稻、玉米种子（仅取年报明确列示项）", "722236209.33", "910315372.50", "20|21"),
    2019: ("水稻种子（仅取单项即可达到门槛）", "687053171.51", "1153661613.91", "20|21"),
    2020: ("水稻种子（仅取单项即可达到门槛）", "868001184.83", "1601709079.85", "21|22"),
    2021: ("水稻、玉米、小麦、瓜菜、其他作物种子", "1620619581.57", "2520772778.56", "18|19"),
}


def ratio(n, d):
    return (Decimal(n) / Decimal(d)).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)


def main():
    src = pd.read_csv(SOURCE, dtype={"股票代码": str})
    selected = src[(src["股票代码"] == "300087") & src["年份"].isin(VERIFIED)].copy()
    assert len(selected) == 9
    assert not selected["复核状态"].str.startswith("已人工复核", na=False).any()
    rows = []
    for _, row in selected.sort_values("年份").iterrows():
        year = int(row["年份"])
        business, numerator, total, page = VERIFIED[year]
        share = ratio(numerator, total)
        assert share >= Decimal("0.50")
        rows.append({
            "股票代码": "300087", "公司全称": row["公司全称"], "年份": year,
            "行业分类代码": row["行业分类代码"], "行业分类名称": row["行业分类名称"],
            "直接涉农业务_保守不重叠口径": business,
            "直接涉农业务营业收入_元": numerator, "公司营业收入_元": total,
            "直接涉农收入占比": f"{share:.8f}", "严格样本结论": "是",
            "扩展样本结论": "是", "边界样本结论": "否",
            "是否存在分部收入重叠": "否（同一分产品维度内求和）",
            "复核说明": "仅合计当年年报明确列示的种子产品收入，已超过合并营业收入50%；未计订单粮食、青贮、农批市场、农机农化、服务及含义不清的其他项。",
            "年报主营业务证据PDF页序号": page,
            "公司营业收入证据PDF页序号": row["利润表PDF页序号"],
            "年报链接": row["年报链接"], "记录类型": "本次新增跨年快速复核",
            "复核日期": "2026-08-10",
        })
    out = pd.DataFrame(rows)
    assert len(out) == 9 and not out.duplicated(["股票代码", "年份"]).any()
    out.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("batch04 rows=9; companies=1; strict yes=9; conservative seed-only ratios")


if __name__ == "__main__":
    main()
