#!/usr/bin/env python3
"""Export the completed 2023 entry review into decision-oriented tables."""
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v10_2023入口复核完成.csv"
OUT = ROOT / "outputs"

CORE_COLUMNS = [
    "股票代码", "公司全称", "年份", "行业分类代码", "行业分类名称", "入口依据",
    "行业入口候选", "龙头身份关系已核实候选", "涉农业务名称", "涉农业务营业收入",
    "公司营业收入", "涉农收入占比", "是否存在分部收入重叠", "严格样本结论",
    "扩展样本结论", "边界样本结论", "纳入或剔除理由", "当年曾ST_已核实",
    "年末ST_已核实", "当年退市整理期_已核实", "年报链接", "年报主营业务表PDF页序号",
    "利润表PDF页序号", "复核状态", "口径提示",
]


def write(df: pd.DataFrame, filename: str) -> None:
    df[CORE_COLUMNS].sort_values(["年份", "股票代码"]).to_csv(
        OUT / filename, index=False, encoding="utf-8-sig"
    )


def main() -> None:
    data = pd.read_csv(SOURCE, dtype={"股票代码": str})
    year = data[data["年份"] == 2023].copy()

    assert len(year) == 134
    assert not year.duplicated(["股票代码", "年份"]).any()
    assert year["复核状态"].str.startswith("已人工复核", na=False).all()

    strict = year[year["严格样本结论"] == "是"]
    expanded = year[year["扩展样本结论"] == "是"]
    boundary = year[year["边界样本结论"] == "是"]
    pending = year[
        year[["严格样本结论", "扩展样本结论", "边界样本结论"]]
        .eq("待核实").any(axis=1)
    ]
    excluded = year[
        year["严格样本结论"].eq("否")
        & year["扩展样本结论"].eq("否")
        & year["边界样本结论"].eq("否")
    ]
    baseline = expanded[
        expanded["当年曾ST_已核实"].ne("是")
        & expanded["当年退市整理期_已核实"].ne("是")
    ]
    st_excluded = expanded[expanded["当年曾ST_已核实"].eq("是")]

    expected = {
        "strict": (strict, 27), "expanded": (expanded, 64),
        "boundary": (boundary, 5), "pending": (pending, 10),
        "excluded": (excluded, 56), "baseline": (baseline, 60),
        "st_excluded": (st_excluded, 4),
    }
    for name, (frame, count) in expected.items():
        assert len(frame) == count, f"{name}: expected {count}, got {len(frame)}"

    write(strict, "2023严格样本公司年份表_v1.csv")
    write(expanded, "2023扩展样本公司年份表_v1.csv")
    write(boundary, "2023边界企业表_v1.csv")
    write(pending, "2023待核实企业表_v1.csv")
    write(excluded, "2023剔除企业表_v1.csv")
    write(baseline, "2023基准样本候选_剔除ST后_v1.csv")
    write(st_excluded, "2023因ST剔除的已达收入门槛企业表_v1.csv")

    print("2023 review exports complete:")
    for name, (frame, _) in expected.items():
        print(f"  {name}={len(frame)}")


if __name__ == "__main__":
    main()
