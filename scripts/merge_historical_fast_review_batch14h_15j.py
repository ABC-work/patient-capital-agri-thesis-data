#!/usr/bin/env python3
"""Merge audited batch-14 H and batch-15 J groups into v24."""
from pathlib import Path
from decimal import Decimal

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v24_跨年快速复核第十四批第一组.csv"
BATCHES = {
    "H": ROOT / "outputs" / "跨年快速复核第十四批_H组_3家公司.csv",
    "J": ROOT / "outputs" / "跨年快速复核第十五批_J组_3家公司.csv",
}
OUTPUT = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v25_跨年快速复核第十五批第一组.csv"


def choose(row: pd.Series, *columns: str) -> str:
    for column in columns:
        if column in row.index and str(row[column]) != "":
            return str(row[column])
    return ""


def normalize(group: str, row: pd.Series) -> dict[str, str]:
    numerator = choose(row, "扩展口径正式涉农收入_元")
    ratio = ""
    if numerator:
        denominator = Decimal(choose(row, "公司营业收入_元"))
        ratio = f"{Decimal(numerator) / denominator:.8f}"
    extra = choose(
        row, "证据定位更正说明", "年报数值尾差说明", "2022行业字段处理", "待核实点"
    )
    return {
        "涉农业务名称": choose(row, "扩展口径涉农业务", "严格口径涉农业务"),
        "涉农业务营业收入": numerator,
        "公司营业收入": choose(row, "公司营业收入_元"),
        "涉农收入占比": ratio,
        "是否存在分部收入重叠": choose(row, "是否存在分部收入重叠"),
        "严格样本结论": choose(row, "严格样本结论"),
        "扩展样本结论": choose(row, "扩展样本结论"),
        "边界样本结论": choose(row, "边界样本结论"),
        "纳入或剔除理由": choose(row, "纳入或剔除理由"),
        "复核状态": f"已人工复核（跨年快速核对第十四/十五批{group}组）",
        "口径提示": (
            "逐年核对官方年报；农业投入品下界只加同层级明确产品；乳品混合初深加工时"
            "保留上下界，内部原奶不重复，能源、食品深加工和模糊其他收入不自动纳入。 " + extra
        ).strip(),
        "年报主营业务表PDF页序号": choose(
            row, "收入分项证据PDF页序号", "年报主营业务证据PDF页序号"
        ),
    }


def main() -> None:
    source = pd.read_csv(SOURCE, dtype={"股票代码": str}, keep_default_na=False)
    assert len(source) == 958
    verified_before = source["复核状态"].str.startswith("已人工复核", na=False)
    assert int(verified_before.sum()) == 562
    protected = source.loc[verified_before].reset_index(drop=True).copy()
    normalized: dict[tuple[str, int], dict[str, str]] = {}
    expected = {"H": 21, "J": 17}
    for group, path in BATCHES.items():
        batch = pd.read_csv(path, dtype={"股票代码": str}, keep_default_na=False)
        assert len(batch) == expected[group]
        assert not batch.duplicated(["股票代码", "年份"]).any()
        for _, row in batch.iterrows():
            key = (str(row["股票代码"]), int(row["年份"]))
            assert key not in normalized
            normalized[key] = normalize(group, row)

    merged = source.copy()
    editable = list(next(iter(normalized.values())).keys())
    merged[editable] = merged[editable].astype("object")
    for index, row in merged.iterrows():
        key = (str(row["股票代码"]), int(row["年份"]))
        if key not in normalized:
            continue
        assert not str(row["复核状态"]).startswith("已人工复核")
        for column, value in normalized[key].items():
            merged.at[index, column] = value

    assert len(merged) == 958
    assert not merged.duplicated(["股票代码", "年份"]).any()
    reviewed_after = merged["复核状态"].str.startswith("已人工复核", na=False)
    assert int(reviewed_after.sum()) == 600
    pd.testing.assert_frame_equal(
        protected, merged.loc[verified_before].reset_index(drop=True), check_dtype=False
    )
    changed = (source.fillna("<NA>") != merged.fillna("<NA>")).any(axis=1)
    changed_keys = set(map(tuple, merged.loc[changed, ["股票代码", "年份"]].values.tolist()))
    assert changed_keys == set(normalized)
    pd.testing.assert_frame_equal(
        source[source["年份"].eq(2023)].reset_index(drop=True),
        merged[merged["年份"].eq(2023)].reset_index(drop=True),
        check_dtype=False,
    )
    assert merged.loc[
        merged["年份"].eq(2022), ["行业分类代码", "行业分类名称"]
    ].eq("待核实").all().all()
    assert int((merged["严格样本结论"] == "是").sum()) == 185
    assert int((merged["扩展样本结论"] == "是").sum()) == 347
    assert int((merged["边界样本结论"] == "是").sum()) == 33

    merged.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("v25 rows=958; H+J=38; reviewed=600; strict=185; expanded=347; boundary=33")


if __name__ == "__main__":
    main()
