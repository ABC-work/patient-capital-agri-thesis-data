#!/usr/bin/env python3
"""Build the first manually verified 2023 annual-report business review batch.

All revenue figures below are transcribed from the official annual reports linked
in the existing review worktable.  The script recalculates every ratio and checks
the company name, report URL and ST flags against that worktable before writing.
"""

from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
WORKTABLE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v1.csv"
OUTPUT = ROOT / "outputs" / "2023年报主营业务人工复核_第一批10家_v1.csv"


RECORDS = [
    dict(code="000048", total="12417006232.40", strict_name="养殖业", strict="2887427838.54",
         expanded_name="养殖业、饲料生产", expanded="3810886277.93", overlap="否（采用分行业不重叠口径）",
         strict_yes="否", expanded_yes="否", boundary="是",
         reason="严格口径23.25%，扩展口径30.69%；达到30%但未达到50%，列为边界样本。"),
    dict(code="000713", total="3113679181.58", strict_name="种子类", strict="884274033.87",
         expanded_name="种子类、农化类", expanded="2812737488.63", overlap="否（采用分行业不重叠口径）",
         strict_yes="否", expanded_yes="是", boundary="否",
         reason="种子业务严格口径28.40%；加入农业投入品农化业务后扩展口径90.33%。"),
    dict(code="000735", total="4100302074.67", strict_name="畜牧业", strict="1022047230.61",
         expanded_name="畜牧业、农副产品加工业", expanded="2285869183.60", overlap="否（采用分行业不重叠口径）",
         strict_yes="否", expanded_yes="是", boundary="否",
         reason="畜牧业严格口径24.93%；加入农产品初加工后扩展口径55.75%。"),
    dict(code="000798", total="4041783287.50", strict_name="捕捞、渔业服务", strict="2926498175.17",
         expanded_name="捕捞、渔业服务", expanded="2926498175.17", overlap="否（采用分行业不重叠口径）",
         strict_yes="是", expanded_yes="是", boundary="否",
         reason="捕捞与渔业服务分别对应A04和A05，合计严格口径72.41%；未将一般零售、加工及贸易机械计入。"),
    dict(code="000998", total="9223216747.53", strict_name="农业（水稻种子、玉米种子）", strict="7807420305.76",
         expanded_name="农业（水稻种子、玉米种子）", expanded="7807420305.76", overlap="否（采用分行业不重叠口径）",
         strict_yes="是", expanded_yes="是", boundary="否",
         reason="农业分行业收入占84.65%，达到严格样本50%门槛。"),
    dict(code="001201", total="1037067905.17", strict_name="畜牧业（生猪）", strict="961270931.71",
         expanded_name="畜牧业（生猪）、饲料加工业", expanded="1010046413.19", overlap="否（采用分行业不重叠口径）",
         strict_yes="是", expanded_yes="是", boundary="否",
         reason="生猪收入严格口径92.69%；加入饲料后扩展口径97.39%。年报注明饲料主要供内部猪场使用，但表列收入未与生猪收入重叠。"),
    dict(code="002041", total="1551975042.78", strict_name="农业（种业）", strict="1551975042.78",
         expanded_name="农业（种业）", expanded="1551975042.78", overlap="否（采用营业收入构成总表）",
         strict_yes="是", expanded_yes="是", boundary="否",
         reason="营业收入构成表中农业收入占100%；未误用仅披露占比10%以上项目的1,531,128,505.10元。"),
    dict(code="002069", total="1677473644.98", strict_name="海水养殖、牡蛎苗种技术服务", strict="273786571.07",
         expanded_name="海水养殖、水产品加工、牡蛎苗种技术服务", expanded="923163617.64", overlap="否（采用分行业不重叠口径）",
         strict_yes="否", expanded_yes="是", boundary="否",
         reason="严格口径16.32%；加入水产品加工后扩展口径55.03%。技术服务经年报说明为牡蛎苗种业务。2023年曾ST，最终回归样本仍须剔除。"),
    dict(code="002086", total="437233445.62", strict_name="海水养殖", strict="88096305.46",
         expanded_name="海水养殖、水产品加工", expanded="217376397.83", overlap="否（采用分行业不重叠口径）",
         strict_yes="否", expanded_yes="否", boundary="是",
         reason="严格口径20.15%，扩展口径49.72%，未达到50%，列为边界样本；2023年为ST，最终回归样本须剔除。"),
    dict(code="002124", total="10231927988.44", strict_name="生猪养殖", strict="7310675390.02",
         expanded_name="生猪养殖、食品加工", expanded="9794235835.37", overlap="否（采用分行业不重叠口径）",
         strict_yes="是", expanded_yes="是", boundary="否",
         reason="生猪养殖收入严格口径71.45%；加入屠宰等食品加工后扩展口径95.72%。"),
]


def ratio(numerator: str, denominator: str) -> Decimal:
    return (Decimal(numerator) / Decimal(denominator)).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)


def main() -> None:
    source = pd.read_csv(WORKTABLE, dtype={"股票代码": str})
    source = source[(source["年份"] == 2023) & source["股票代码"].isin([r["code"] for r in RECORDS])]
    source = source.set_index("股票代码", drop=False)
    assert len(source) == len(RECORDS), "The source worktable is missing one or more batch records."

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
        final_eligible = "否（ST剔除）" if st_any == "是" else (
            "是（严格样本）" if record["strict_yes"] == "是" else
            "是（扩展样本）" if record["expanded_yes"] == "是" else
            "否（仅边界稳健性）" if record["boundary"] == "是" else "否"
        )
        rows.append({
            "股票代码": record["code"],
            "公司全称": src["公司全称"],
            "年份": 2023,
            "公司营业收入_元": record["total"],
            "严格口径涉农业务": record["strict_name"],
            "严格口径涉农收入_元": record["strict"],
            "严格口径涉农收入占比": f"{strict_ratio:.8f}",
            "扩展口径涉农业务": record["expanded_name"],
            "扩展口径涉农收入_元": record["expanded"],
            "扩展口径涉农收入占比": f"{expanded_ratio:.8f}",
            "是否存在分部收入重叠": record["overlap"],
            "严格样本结论": record["strict_yes"],
            "扩展样本结论": record["expanded_yes"],
            "边界样本结论": record["boundary"],
            "当年曾ST_已核实": st_any,
            "最终回归样本资格_当前规则": final_eligible,
            "纳入或剔除理由": record["reason"],
            "主营业务证据PDF页序号": int(src["年报主营业务表PDF页序号"]),
            "营业收入证据PDF页序号": int(src["利润表PDF页序号"]),
            "年报链接": src["年报链接"],
            "复核状态": "已人工复核（第一批）",
            "复核日期": "2026-08-06",
        })

    output = pd.DataFrame(rows)
    assert not output.duplicated(["股票代码", "年份"]).any()
    output.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print(f"Wrote {len(output)} verified rows to {OUTPUT}")
    print(output[["股票代码", "严格口径涉农收入占比", "扩展口径涉农收入占比", "严格样本结论", "扩展样本结论", "边界样本结论", "最终回归样本资格_当前规则"]].to_string(index=False))


if __name__ == "__main__":
    main()
