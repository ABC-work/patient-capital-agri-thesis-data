#!/usr/bin/env python3
"""Build the third manually verified 2023 annual-report business review batch."""

from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
WORKTABLE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v1.csv"
OUTPUT = ROOT / "outputs" / "2023年报主营业务人工复核_第三批10家_v1.csv"

RECORDS = [
    dict(code="002299", total="18486738694.46", strict_name="家禽养殖（与加工合并披露，无法可靠拆分）", strict=None,
         expanded_name="家禽饲养加工行业", expanded="10517359334.59", strict_yes="待核实", expanded_yes="是", boundary="否",
         overlap="合并披露风险：养殖与加工无法可靠拆分；未估算严格口径",
         reason="家禽饲养加工合并收入占56.89%，扩展口径达标；年报未可靠拆分养殖和初加工，严格口径保持待核实。"),
    dict(code="002321", total="3704949528.49", strict_name="鸭苗、种蛋", strict="33891463.43",
         expanded_name="鸭苗、种蛋、冻鸭、鸭毛、饲料、羽绒", expanded="3076209534.81", strict_yes="否", expanded_yes="是", boundary="否",
         overlap="否（采用分产品不重叠口径）",
         reason="鸭苗与种蛋严格口径0.91%；加入鸭产品初加工、农业投入品及羽绒初加工后扩展口径83.03%。熟食、租赁等未计入；2023年曾ST。"),
    dict(code="300189", total="166725377.15", strict_name="杂交水稻、玉米、油菜及其他种子", strict="155069173.68",
         expanded_name="杂交水稻、玉米、油菜及其他种子", expanded="155069173.68", strict_yes="是", expanded_yes="是", boundary="否",
         overlap="否（采用分产品不重叠口径）", reason="四类种子收入合计占93.01%，已达到严格样本门槛。"),
    dict(code="300313", total="137499875.86", strict_name="畜牧业", strict="110513387.01",
         expanded_name="畜牧业", expanded="110513387.01", strict_yes="是", expanded_yes="是", boundary="否",
         overlap="否（采用分行业口径）", reason="畜牧业收入占80.37%，达到严格门槛；2023年曾ST，最终回归剔除。"),
    dict(code="300498", total="89902322387.76", strict_name="养殖行业", strict="87844706272.81",
         expanded_name="养殖行业", expanded="87844706272.81", strict_yes="是", expanded_yes="是", boundary="否",
         overlap="否（采用分行业口径）", reason="养殖行业收入占营业收入97.71%，达到严格样本门槛；分母采用营业收入而非含利息收入的营业总收入。"),
    dict(code="300511", total="2565144194.86", strict_name="食用菌种植", strict="2534307562.89",
         expanded_name="食用菌种植", expanded="2534307562.89", strict_yes="是", expanded_yes="是", boundary="否",
         overlap="否（采用分行业口径）", reason="食用菌行业收入占98.80%，达到严格样本门槛。"),
    dict(code="300761", total="15354096858.27", strict_name="鸡、猪、鹅养殖", strict="15267697502.53",
         expanded_name="鸡、猪、鹅养殖", expanded="15267697502.53", strict_yes="是", expanded_yes="是", boundary="否",
         overlap="否（采用分产品不重叠口径）", reason="鸡、猪、鹅三类养殖收入合计占99.44%，达到严格样本门槛；未计无法拆分的其他收入。"),
    dict(code="300967", total="830815831.80", strict_name="养殖行业", strict="830359022.41",
         expanded_name="养殖行业", expanded="830359022.41", strict_yes="是", expanded_yes="是", boundary="否",
         overlap="否（采用分行业口径）", reason="养殖行业收入占99.95%，达到严格样本门槛。"),
    dict(code="300970", total="996221375.81", strict_name="食用菌种植", strict="996221375.81",
         expanded_name="食用菌种植", expanded="996221375.81", strict_yes="是", expanded_yes="是", boundary="否",
         overlap="否（采用分行业口径）", reason="食用菌收入占100%，达到严格样本门槛。"),
    dict(code="300972", total="9293739531.63", strict_name="食用菌种植", strict="534714751.23",
         expanded_name="食用菌种植", expanded="534714751.23", strict_yes="否", expanded_yes="否", boundary="否",
         overlap="否（采用分行业口径）", reason="食用菌仅占5.75%，量贩零食占94.25%；量贩零食不属于农业生产、初加工、投入品或生产性服务，故该公司—年份剔除。"),
]


def ratio(value: str, total: str) -> Decimal:
    return (Decimal(value) / Decimal(total)).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)


def main() -> None:
    source = pd.read_csv(WORKTABLE, dtype={"股票代码": str})
    source = source[(source["年份"] == 2023) & source["股票代码"].isin([r["code"] for r in RECORDS])].set_index("股票代码")
    assert len(source) == 10
    rows = []
    for record in RECORDS:
        src = source.loc[record["code"]]
        strict_ratio = ratio(record["strict"], record["total"]) if record["strict"] is not None else None
        expanded_ratio = ratio(record["expanded"], record["total"])
        if strict_ratio is not None:
            assert Decimal(record["strict"]) <= Decimal(record["expanded"])
            assert (strict_ratio >= Decimal("0.5")) == (record["strict_yes"] == "是")
        else:
            assert record["strict_yes"] == "待核实"
        assert Decimal(record["expanded"]) <= Decimal(record["total"])
        assert (expanded_ratio >= Decimal("0.5")) == (record["expanded_yes"] == "是")
        assert ((Decimal("0.3") <= expanded_ratio < Decimal("0.5")) == (record["boundary"] == "是"))
        st_any = "是" if src["当年曾ST_已核实"] == "是" else "否"
        if st_any == "是":
            eligibility = "否（ST剔除）"
        elif record["strict_yes"] == "是":
            eligibility = "是（严格样本）"
        elif record["expanded_yes"] == "是":
            eligibility = "是（扩展样本；严格口径待核实）" if record["strict_yes"] == "待核实" else "是（扩展样本）"
        else:
            eligibility = "否（涉农收入低于30%）"
        rows.append({
            "股票代码": record["code"], "公司全称": src["公司全称"], "年份": 2023,
            "公司营业收入_元": record["total"], "严格口径涉农业务": record["strict_name"],
            "严格口径涉农收入_元": record["strict"] or "", "严格口径涉农收入占比": "" if strict_ratio is None else f"{strict_ratio:.8f}",
            "扩展口径涉农业务": record["expanded_name"], "扩展口径涉农收入_元": record["expanded"],
            "扩展口径涉农收入占比": f"{expanded_ratio:.8f}", "是否存在分部收入重叠": record["overlap"],
            "严格样本结论": record["strict_yes"], "扩展样本结论": record["expanded_yes"], "边界样本结论": record["boundary"],
            "当年曾ST_已核实": st_any, "最终回归样本资格_当前规则": eligibility, "纳入或剔除理由": record["reason"],
            "主营业务证据PDF页序号": int(src["年报主营业务表PDF页序号"]),
            "营业收入证据PDF页序号": int(src["利润表PDF页序号"]), "年报链接": src["年报链接"],
            "复核状态": "已人工复核（第三批）", "复核日期": "2026-08-06",
        })
    output = pd.DataFrame(rows)
    assert not output.duplicated(["股票代码", "年份"]).any()
    output.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print(f"Wrote {len(output)} verified rows to {OUTPUT}")
    print(output[["股票代码", "严格口径涉农收入占比", "扩展口径涉农收入占比", "严格样本结论", "扩展样本结论", "最终回归样本资格_当前规则"]].to_string(index=False))


if __name__ == "__main__":
    main()
