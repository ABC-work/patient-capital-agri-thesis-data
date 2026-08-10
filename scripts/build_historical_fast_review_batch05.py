#!/usr/bin/env python3
"""Build batch 05: 神农科技 2013-2021, including transformation years."""
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v14_跨年快速复核第四批.csv"
OUTPUT = ROOT / "outputs" / "跨年快速复核第五批_神农科技9条_v1.csv"

# business, numerator used for threshold, consolidated revenue, strict, expanded,
# boundary, evidence page. In 2016-2017 numerator is the broader expanded-agri
# amount because the seed-only strict numerator is lower still.
VERIFIED = {
    2013: ("杂交水稻、玉米、棉花、蔬菜及其他种子", "398617600.00", "454365781.09", "是", "是", "否", "21"),
    2014: ("杂交水稻、玉米、棉花、蔬菜及其他种子", "266096600.00", "301602338.43", "是", "是", "否", "20|21"),
    2015: ("杂交水稻、玉米、棉花、蔬菜及其他种子", "239020007.32", "310509442.07", "是", "是", "否", "15"),
    2016: ("全部农业收入（含种子、农化及农业技术服务）", "337449168.11", "1151900610.96", "否", "否", "否", "22"),
    2017: ("种子、农化产品及农业技术服务", "218165990.18", "451438322.09", "否", "否", "是", "22"),
    2018: ("杂交水稻、玉米、棉花、蔬菜及其他种子", "124117508.61", "171895373.03", "是", "是", "否", "25|26"),
    2019: ("杂交水稻、玉米、蔬菜及其他种子", "92799774.17", "112458427.26", "是", "是", "否", "17|18"),
    2020: ("杂交水稻、玉米、蔬菜及其他种子", "118588052.60", "129368353.32", "是", "是", "否", "18|19"),
    2021: ("杂交水稻、玉米、蔬菜及其他种子", "129404840.72", "147833027.35", "是", "是", "否", "19|20"),
}


def share(n, d):
    return (Decimal(n) / Decimal(d)).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)


def main():
    src = pd.read_csv(SOURCE, dtype={"股票代码": str})
    selected = src[(src["股票代码"] == "300189") & src["年份"].isin(VERIFIED)].copy()
    assert len(selected) == 9 and not selected["复核状态"].str.startswith("已人工复核", na=False).any()
    rows = []
    for _, row in selected.sort_values("年份").iterrows():
        year = int(row["年份"])
        business, n, total, strict, expanded, boundary, page = VERIFIED[year]
        r = share(n, total)
        assert (strict == "是") == (r >= Decimal("0.50"))
        if boundary == "是":
            assert Decimal("0.30") <= r < Decimal("0.50")
        reason = (
            "明确种子产品收入已超过合并营业收入50%，未计农化、粮食、房屋、供应链等项目。"
            if strict == "是" else
            "业务转型期全部农业收入仅占29.29%，低于30%，不进入严格、扩展或边界样本。"
            if year == 2016 else
            "种子严格口径占45.32%；加入农化及农业技术服务后扩展口径占48.33%，列为边界样本。"
        )
        rows.append({
            "股票代码": "300189", "公司全称": row["公司全称"], "年份": year,
            "行业分类代码": row["行业分类代码"], "行业分类名称": row["行业分类名称"],
            "直接涉农业务_保守不重叠口径": business,
            "直接涉农业务营业收入_元": n, "公司营业收入_元": total,
            "直接涉农收入占比": f"{r:.8f}", "严格样本结论": strict,
            "扩展样本结论": expanded, "边界样本结论": boundary,
            "是否存在分部收入重叠": "否（同一分产品维度内求和）",
            "复核说明": reason, "年报主营业务证据PDF页序号": page,
            "公司营业收入证据PDF页序号": row["利润表PDF页序号"],
            "年报链接": row["年报链接"], "记录类型": "本次新增跨年快速复核",
            "复核日期": "2026-08-10",
        })
    out = pd.DataFrame(rows)
    assert len(out) == 9 and out["严格样本结论"].eq("是").sum() == 7
    out.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("batch05 rows=9; strict yes=7; boundary=1; excluded=1")


if __name__ == "__main__":
    main()
