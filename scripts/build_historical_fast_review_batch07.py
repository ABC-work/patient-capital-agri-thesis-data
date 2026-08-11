#!/usr/bin/env python3
"""Build historical fast-review batch 07 from the v16 worktable.

The batch reviews 22 company-years for 罗牛山、民和股份 and 益生股份.
Values come from the same year's official annual-report revenue table. Strict
and expanded numerators use one disclosure dimension per row, so industry and
product figures are never added together.
"""
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v16_跨年快速复核第六批.csv"
OUTPUT = ROOT / "outputs" / "跨年快速复核第七批_3家公司22条_v1.csv"

# business, stored numerator, strict numerator, expanded numerator, total,
# strict, expanded, boundary, evidence page, dimension note.
VERIFIED = {
    "000735": {
        2013: ("生猪养殖及屠宰加工（扩展口径）", "737117983.89", "569234258.77", "737117983.89", "1719531920.81", "否", "否", "是", "15", "同一分行业维度"),
        2014: ("生猪养殖及屠宰加工（扩展口径）", "488907275.72", "332408135.12", "488907275.72", "1005817243.57", "否", "否", "是", "17", "同一分行业维度"),
        2015: ("生猪养殖及屠宰加工（扩展口径）", "461277640.83", "237011917.38", "461277640.83", "729998909.71", "否", "是", "否", "11", "同一分行业维度"),
        2016: ("畜牧业及屠宰加工业（扩展口径）", "480527756.39", "296935560.74", "480527756.39", "891077257.45", "否", "是", "否", "12", "同一分行业维度"),
        2017: ("畜牧业及屠宰加工业（扩展口径）", "466211498.34", "279865882.83", "466211498.34", "1298149934.33", "否", "否", "是", "15-16", "同一分行业维度"),
        2018: ("生猪及肉制品（扩展口径）", "441904186.09", "318590680.26", "441904186.09", "1121254823.29", "否", "否", "是", "13", "同一分产品维度"),
        2019: ("生猪及肉制品（扩展口径）", "687810105.82", "266716072.57", "687810105.82", "1164257304.12", "否", "是", "否", "13-14", "同一分产品维度"),
        2020: ("生猪及肉制品（扩展口径）", "1925373745.47", "551137045.37", "1925373745.47", "2333326709.68", "否", "是", "否", "13-14", "同一分产品维度"),
        2021: ("生猪及肉制品（扩展口径）", "1432660810.63", "711095770.86", "1432660810.63", "1871731105.96", "否", "是", "否", "16", "同一分产品维度"),
    },
    "002234": {
        2013: ("雏鸡、淘汰鸡及鸡肉制品（扩展口径）", "930893902.82", "362484125.90", "930893902.82", "996313767.09", "否", "是", "否", "13", "同一分产品维度"),
        2014: ("雏鸡、淘汰鸡及鸡肉制品（扩展口径）", "1075195638.77", "523597123.50", "1075195638.77", "1186417366.13", "否", "是", "否", "13", "同一分产品维度"),
        2015: ("雏鸡、淘汰鸡及鸡肉制品（扩展口径）", "830477098.91", "330711297.41", "830477098.91", "900799701.79", "否", "是", "否", "9-10", "同一分产品维度"),
        2016: ("雏鸡及淘汰鸡", "801958311.20", "801958311.20", "1361051099.24", "1408702921.15", "是", "是", "否", "15-16", "同一分产品维度"),
        2017: ("雏鸡、淘汰鸡及鸡肉制品（扩展口径）", "1009123926.57", "428782903.18", "1009123926.57", "1067502353.94", "否", "是", "否", "15-16", "同一分产品维度"),
        2018: ("雏鸡及淘汰鸡", "1019590553.10", "1019590553.10", "1737290799.75", "1817711386.36", "是", "是", "否", "15-16", "同一分产品维度"),
        2019: ("雏鸡及淘汰鸡", "2351883895.77", "2351883895.77", "3202945064.62", "3276052000.43", "是", "是", "否", "15-16", "同一分产品维度"),
        2020: ("雏鸡及淘汰鸡", "924777610.80", "924777610.80", "1589098958.61", "1681883981.38", "是", "是", "否", "17", "同一分产品维度"),
        2021: ("雏鸡及淘汰鸡", "997973934.12", "997973934.12", "1666596638.90", "1775432179.30", "是", "是", "否", "17-18", "同一分产品维度"),
    },
    "002458": {
        2016: ("鸡、猪、牛奶", "1586466270.15", "1586466270.15", "1586466270.15", "1611132544.74", "是", "是", "否", "13-14", "同一分行业维度"),
        2017: ("鸡、猪、牛奶", "635130404.29", "635130404.29", "635130404.29", "656404863.44", "是", "是", "否", "15", "同一分行业维度"),
        2019: ("鸡、猪、牛奶", "3454297955.82", "3454297955.82", "3454297955.82", "3583534105.26", "是", "是", "否", "15", "同一分行业维度"),
        2021: ("鸡、猪、牛奶", "1985303867.17", "1985303867.17", "1985303867.17", "2089921928.63", "是", "是", "否", "18-19", "同一分行业维度"),
    },
}


def ratio(numerator: str, denominator: str) -> Decimal:
    return (Decimal(numerator) / Decimal(denominator)).quantize(
        Decimal("0.00000001"), rounding=ROUND_HALF_UP
    )


def main() -> None:
    source = pd.read_csv(SOURCE, dtype={"股票代码": str})
    keys = {(code, year) for code, years in VERIFIED.items() for year in years}
    assert len(keys) == 22
    selected = source[
        source.apply(lambda row: (row["股票代码"], int(row["年份"])) in keys, axis=1)
    ].copy()
    assert len(selected) == 22
    assert not selected.duplicated(["股票代码", "年份"]).any()
    assert not selected["复核状态"].str.startswith("已人工复核", na=False).any()

    rows = []
    for _, source_row in selected.sort_values(["股票代码", "年份"]).iterrows():
        code, year = source_row["股票代码"], int(source_row["年份"])
        business, stored, strict_n, expanded_n, total, strict, expanded, boundary, page, dimension = VERIFIED[code][year]
        strict_share = ratio(strict_n, total)
        expanded_share = ratio(expanded_n, total)
        stored_share = ratio(stored, total)

        assert (strict_share >= Decimal("0.50")) == (strict == "是")
        assert (expanded_share >= Decimal("0.50")) == (expanded == "是")
        assert (Decimal("0.30") <= expanded_share < Decimal("0.50")) == (boundary == "是")

        if boundary == "是":
            reason = (
                f"直接农业收入占{strict_share * 100:.2f}%，加入同一披露维度的初加工收入后占"
                f"{expanded_share * 100:.2f}%，仍处于30%—50%，列为边界样本。"
            )
        elif strict == "是":
            reason = (
                f"直接畜牧养殖收入占{strict_share * 100:.2f}%，超过合并营业收入50%；"
                "未叠加行业、产品或地区等交叉披露维度。"
            )
        else:
            reason = (
                f"直接畜牧养殖收入占{strict_share * 100:.2f}%，未达50%；"
                f"加入{dimension}的农产品初加工收入后占{expanded_share * 100:.2f}%，纳入扩展样本。"
            )

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
            "是否存在分部收入重叠": f"否（仅使用{dimension}）",
            "复核说明": reason,
            "年报主营业务证据PDF页序号": page,
            "公司营业收入证据PDF页序号": source_row["利润表PDF页序号"],
            "年报链接": source_row["年报链接"],
            "记录类型": "本次新增跨年快速复核",
            "复核日期": "2026-08-11",
        })

    output = pd.DataFrame(rows)
    assert len(output) == 22
    assert not output.duplicated(["股票代码", "年份"]).any()
    assert output["严格样本结论"].value_counts().to_dict() == {"否": 13, "是": 9}
    assert output["扩展样本结论"].value_counts().to_dict() == {"是": 18, "否": 4}
    assert output["边界样本结论"].value_counts().to_dict() == {"否": 18, "是": 4}
    output.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("batch07 rows=22; strict yes=9; expanded yes=18; boundary=4")


if __name__ == "__main__":
    main()
