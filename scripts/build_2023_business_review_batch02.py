#!/usr/bin/env python3
"""Build the second manually verified 2023 annual-report business review batch."""

from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
WORKTABLE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v1.csv"
OUTPUT = ROOT / "outputs" / "2023年报主营业务人工复核_第二批8家_v1.csv"

RECORDS = [
    dict(code="002157", total="6991677730.61", strict_name="养殖", strict="4484299845.66",
         expanded_name="养殖、饲料", expanded="6891599874.51", strict_yes="是", expanded_yes="是", boundary="否",
         reason="养殖收入严格口径64.14%，达到50%；加入饲料后扩展口径98.57%。2023年曾ST，最终回归剔除。"),
    dict(code="002234", total="2074466255.83", strict_name="雏鸡", strict="748840081.40",
         expanded_name="雏鸡、鸡肉制品", expanded="1863839992.05", strict_yes="否", expanded_yes="是", boundary="否",
         reason="保守地仅将雏鸡计入严格口径，占36.10%；加入鸡肉制品初加工后扩展口径89.85%。未以年报笼统的‘畜牧业’整段收入替代严格口径。"),
    dict(code="002458", total="3224676928.89", strict_name="鸡、猪、乳品", strict="3094339371.59",
         expanded_name="鸡、猪、乳品、畜牧设备", expanded="3193656691.77", strict_yes="是", expanded_yes="是", boundary="否",
         reason="种畜禽及乳品收入严格口径95.96%；加入畜牧设备后扩展口径99.04%。"),
    dict(code="002679", total="147650078.15", strict_name="林业", strict="145501169.23",
         expanded_name="林业", expanded="145501169.23", strict_yes="是", expanded_yes="是", boundary="否",
         reason="林业分行业收入占98.54%，达到严格样本门槛。"),
    dict(code="002714", total="110860727714.40", strict_name="养殖业务（生猪）", strict="108224321673.98",
         expanded_name="养殖业务（生猪）", expanded="108224321673.98", strict_yes="是", expanded_yes="是", boundary="否",
         reason="养殖业务收入占97.62%，达到严格样本门槛。屠宰业务与养殖存在内部交易抵销，本次不重复相加。"),
    dict(code="002772", total="1931077659.25", strict_name="农业种植业（食用菌）", strict="1930925770.36",
         expanded_name="农业种植业（食用菌）", expanded="1930925770.36", strict_yes="是", expanded_yes="是", boundary="否",
         reason="农业种植业收入占99.99%，达到严格样本门槛；厂房租赁未计入。"),
    dict(code="002982", total="3890122738.57", strict_name="活禽、商品蛋", strict="1334862689.11",
         expanded_name="活禽、商品蛋、冰鲜产品", expanded="3564796386.99", strict_yes="否", expanded_yes="是", boundary="否",
         reason="活禽与商品蛋严格口径34.31%；加入冰鲜禽产品初加工后扩展口径91.64%。未把分行业‘养殖行业’100%机械视为直接养殖收入。"),
    dict(code="300087", total="4102895157.95", strict_name="水稻、玉米、小麦、棉花、瓜菜、大豆及其他作物种子", strict="2844711221.82",
         expanded_name="水稻、玉米、小麦、棉花、瓜菜、大豆及其他作物种子", expanded="2844711221.82", strict_yes="是", expanded_yes="是", boundary="否",
         reason="仅七类种子收入合计已占69.33%，达到严格样本门槛；未依赖边界业务扩大分子。"),
]


def ratio(numerator: str, denominator: str) -> Decimal:
    return (Decimal(numerator) / Decimal(denominator)).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)


def main() -> None:
    source = pd.read_csv(WORKTABLE, dtype={"股票代码": str})
    source = source[(source["年份"] == 2023) & source["股票代码"].isin([r["code"] for r in RECORDS])].set_index("股票代码")
    assert len(source) == len(RECORDS)
    rows = []
    for record in RECORDS:
        src = source.loc[record["code"]]
        strict_ratio = ratio(record["strict"], record["total"])
        expanded_ratio = ratio(record["expanded"], record["total"])
        assert Decimal(record["strict"]) <= Decimal(record["expanded"]) <= Decimal(record["total"])
        assert (strict_ratio >= Decimal("0.5")) == (record["strict_yes"] == "是")
        assert (expanded_ratio >= Decimal("0.5")) == (record["expanded_yes"] == "是")
        assert ((Decimal("0.3") <= expanded_ratio < Decimal("0.5")) == (record["boundary"] == "是"))
        st_any = "是" if src["当年曾ST_已核实"] == "是" else "否"
        eligibility = "否（ST剔除）" if st_any == "是" else ("是（严格样本）" if record["strict_yes"] == "是" else "是（扩展样本）")
        rows.append({
            "股票代码": record["code"], "公司全称": src["公司全称"], "年份": 2023,
            "公司营业收入_元": record["total"], "严格口径涉农业务": record["strict_name"],
            "严格口径涉农收入_元": record["strict"], "严格口径涉农收入占比": f"{strict_ratio:.8f}",
            "扩展口径涉农业务": record["expanded_name"], "扩展口径涉农收入_元": record["expanded"],
            "扩展口径涉农收入占比": f"{expanded_ratio:.8f}", "是否存在分部收入重叠": "否（采用同一拆分维度；已排除重复维度）",
            "严格样本结论": record["strict_yes"], "扩展样本结论": record["expanded_yes"], "边界样本结论": record["boundary"],
            "当年曾ST_已核实": st_any, "最终回归样本资格_当前规则": eligibility, "纳入或剔除理由": record["reason"],
            "主营业务证据PDF页序号": int(src["年报主营业务表PDF页序号"]),
            "营业收入证据PDF页序号": int(src["利润表PDF页序号"]), "年报链接": src["年报链接"],
            "复核状态": "已人工复核（第二批）", "复核日期": "2026-08-06",
        })
    output = pd.DataFrame(rows)
    assert not output.duplicated(["股票代码", "年份"]).any()
    output.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print(f"Wrote {len(output)} verified rows to {OUTPUT}")
    print(output[["股票代码", "严格口径涉农收入占比", "扩展口径涉农收入占比", "严格样本结论", "扩展样本结论", "最终回归样本资格_当前规则"]].to_string(index=False))


if __name__ == "__main__":
    main()
