#!/usr/bin/env python3
"""Build a manually verified 29-row pilot for the cross-year fast-review method."""
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v10_2023入口复核完成.csv"
PILOT = ROOT / "outputs" / "跨年快速复核试验_3家公司29条_v1.csv"
MERGED = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v11_跨年快速复核试验.csv"

# Numerators deliberately use a conservative, non-overlapping direct-agriculture
# product or industry line. Values are transcribed from the annual-report evidence
# page; total revenue is checked against the income statement for the same year.
VERIFIED = {
    "002714": {
        2014: ("畜牧养殖", "2602676476.34", "2604763390.34"),
        2015: ("畜牧业（生猪）", "3002995668.79", "3003474722.79"),
        2016: ("畜牧业", "5605907003.09", "5605907003.09"),
        2017: ("畜牧业", "10042415931.26", "10042415931.26"),
        2018: ("生猪（保守产品口径）", "13261601545.91", "13388157685.94"),
        2019: ("生猪（保守产品口径）", "19627036862.66", "20221332525.64"),
        2020: ("生猪（保守产品口径）", "55105001071.85", "56277065607.85"),
        2021: ("生猪（保守产品口径）", "75076114955.15", "78889870566.40"),
        2023: ("生猪（保守产品口径）", "108224321673.98", "110860727714.40"),
    },
    "002041": {
        2013: ("玉米种子（保守产品口径）", "1437157186.91", "1505375096.66"),
        2014: ("玉米种子（保守产品口径）", "1415061521.91", "1480081484.48"),
        2015: ("玉米种子（保守产品口径）", "1477794264.73", "1530773334.98"),
        2016: ("玉米种子（保守产品口径）", "1547236853.14", "1602630739.42"),
        2017: ("玉米种子（保守产品口径）", "747975359.62", "803820973.69"),
        2018: ("玉米种子（保守产品口径）", "675822056.26", "761065669.78"),
        2019: ("玉米种子（保守产品口径）", "721245911.03", "823176983.54"),
        2020: ("玉米种子（保守产品口径）", "784860934.35", "900743999.55"),
        2021: ("玉米种子（保守产品口径）", "978398114.37", "1100726996.19"),
        2023: ("玉米种子（保守产品口径）", "1353831383.12", "1551975042.78"),
    },
    "600371": {
        2013: ("种子行业", "385242040.47", "413015082.51"),
        2014: ("种子行业", "425540609.24", "438199300.97"),
        2015: ("种子行业", "364704423.31", "371715892.15"),
        2016: ("玉米种子（保守产品口径）", "307391243.06", "318502363.87"),
        2017: ("玉米种子（保守产品口径）", "245248710.63", "257773896.15"),
        2018: ("玉米种子（保守产品口径）", "256734575.24", "263890771.75"),
        2019: ("玉米种子（保守产品口径）", "263612607.33", "275377686.09"),
        2020: ("玉米种子（保守产品口径）", "233762236.90", "240058209.59"),
        2021: ("玉米种子（保守产品口径）", "214252051.10", "221697131.31"),
        2023: ("玉米种子（保守产品口径）", "300692394.38", "319298968.77"),
    },
}


def ratio(numerator: str, total: str) -> Decimal:
    return (Decimal(numerator) / Decimal(total)).quantize(
        Decimal("0.00000001"), rounding=ROUND_HALF_UP
    )


def main() -> None:
    data = pd.read_csv(SOURCE, dtype={"股票代码": str})
    keys = {(code, year) for code, years in VERIFIED.items() for year in years}
    selected = data[
        data.apply(lambda row: (row["股票代码"], int(row["年份"])) in keys, axis=1)
    ].copy()
    assert len(keys) == 29 and len(selected) == 29
    assert not selected.duplicated(["股票代码", "年份"]).any()

    rows = []
    for _, source in selected.sort_values(["股票代码", "年份"]).iterrows():
        code, year = source["股票代码"], int(source["年份"])
        business, numerator, total = VERIFIED[code][year]
        share = ratio(numerator, total)
        assert share >= Decimal("0.5")
        candidate_pages = str(source["年报主营业务候选PDF页序号"])
        evidence_page = candidate_pages.split("|")[0] if candidate_pages != "nan" else str(
            source["年报主营业务表PDF页序号"]
        )
        rows.append({
            "股票代码": code, "公司全称": source["公司全称"], "年份": year,
            "行业分类代码": source["行业分类代码"], "行业分类名称": source["行业分类名称"],
            "直接涉农业务_保守不重叠口径": business,
            "直接涉农业务营业收入_元": numerator, "公司营业收入_元": total,
            "直接涉农收入占比": f"{share:.8f}", "严格样本结论": "是",
            "扩展样本结论": "是", "边界样本结论": "否",
            "是否存在分部收入重叠": "否（只取一个分行业或分产品维度；采用保守分子）",
            "复核说明": "直接农业业务的保守收入分子已超过公司营业收入50%；未叠加其他可能符合口径的业务。",
            "年报主营业务证据PDF页序号": evidence_page,
            "公司营业收入证据PDF页序号": source["利润表PDF页序号"],
            "年报链接": source["年报链接"],
            "试验记录类型": "2023已核实锚点复验" if year == 2023 else "本次新增跨年快速复核",
            "复核日期": "2026-08-10",
        })
    pilot = pd.DataFrame(rows)
    assert (pilot["直接涉农收入占比"].astype(float) >= 0.5).all()
    pilot.to_csv(PILOT, index=False, encoding="utf-8-sig")

    # Merge only the 26 newly reviewed pre-2023 records. Existing 2023 conclusions
    # remain untouched, so previously verified results are never overwritten.
    merged = data.copy()
    editable_columns = [
        "涉农业务名称", "涉农业务营业收入", "公司营业收入", "涉农收入占比",
        "是否存在分部收入重叠", "严格样本结论", "扩展样本结论", "边界样本结论",
        "纳入或剔除理由", "复核状态", "口径提示",
    ]
    merged[editable_columns] = merged[editable_columns].astype("object")
    updates = pilot[pilot["年份"].ne(2023)].set_index(["股票代码", "年份"])
    count = 0
    for index, row in merged.iterrows():
        key = (row["股票代码"], int(row["年份"]))
        if key not in updates.index:
            continue
        update = updates.loc[key]
        merged.at[index, "涉农业务名称"] = update["直接涉农业务_保守不重叠口径"]
        merged.at[index, "涉农业务营业收入"] = update["直接涉农业务营业收入_元"]
        merged.at[index, "公司营业收入"] = update["公司营业收入_元"]
        merged.at[index, "涉农收入占比"] = update["直接涉农收入占比"]
        merged.at[index, "是否存在分部收入重叠"] = update["是否存在分部收入重叠"]
        merged.at[index, "严格样本结论"] = "是"
        merged.at[index, "扩展样本结论"] = "是"
        merged.at[index, "边界样本结论"] = "否"
        merged.at[index, "纳入或剔除理由"] = update["复核说明"]
        merged.at[index, "复核状态"] = "已人工复核（跨年快速核对试验）"
        merged.at[index, "口径提示"] = "按公司跨年比较后，逐年核对当年年报业务表与利润表；未复制相邻年份数值。"
        count += 1
    assert count == 26
    assert len(merged) == 958
    assert not merged.duplicated(["股票代码", "年份"]).any()
    assert merged["复核状态"].str.startswith("已人工复核", na=False).sum() == 160
    merged.to_csv(MERGED, index=False, encoding="utf-8-sig")
    print("pilot rows=29; new pre-2023 reviews=26; cumulative reviewed=160/958")


if __name__ == "__main__":
    main()
