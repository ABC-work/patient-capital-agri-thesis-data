#!/usr/bin/env python3
"""Merge audited batch-19 U/V/W groups into v31."""
from decimal import Decimal
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v30_跨年快速复核第十八批.csv"
BATCHES = {
    "U": ROOT / "outputs" / "跨年快速复核第十九批_U组_4家公司.csv",
    "V": ROOT / "outputs" / "跨年快速复核第十九批_V组_4家公司.csv",
    "W": ROOT / "outputs" / "跨年快速复核第十九批_W组_4家公司.csv",
}
OUTPUT = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v31_跨年快速复核第十九批.csv"


def choose(row: pd.Series, *columns: str) -> str:
    for column in columns:
        if column in row.index and str(row[column]) != "":
            return str(row[column])
    return ""


def normalize(group: str, row: pd.Series) -> dict[str, str]:
    numerator = choose(row, "扩展口径正式涉农收入_元")
    ratio = ""
    if numerator:
        ratio = f"{Decimal(numerator) / Decimal(choose(row, '公司营业收入_元')):.8f}"
    notes = []
    for column in ["补充证据说明", "2022行业字段处理", "待核实点"]:
        value = choose(row, column)
        if value and value not in notes:
            notes.append(value)
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
        "复核状态": f"已人工复核（跨年快速核对第十九批{group}组）",
        "口径提示": (
            "逐年核对官方年报；无法可靠拆分的混合业务只保留上下界，正式分子留空；"
            "普通食品、饮料、酒类、零售和药品深加工不因原料涉农而纳入。 "
            + " ".join(notes)
        ).strip(),
        "年报主营业务表PDF页序号": choose(row, "年报主营业务证据PDF页序号"),
    }


def main() -> None:
    source = pd.read_csv(SOURCE, dtype={"股票代码": str}, keep_default_na=False)
    assert len(source) == 958
    reviewed_before = source["复核状态"].str.startswith("已人工复核", na=False)
    assert int(reviewed_before.sum()) == 787
    protected = source.loc[reviewed_before].reset_index(drop=True).copy()

    expected = {"U": 22, "V": 20, "W": 20}
    normalized: dict[tuple[str, int], dict[str, str]] = {}
    for group, path in BATCHES.items():
        batch = pd.read_csv(path, dtype={"股票代码": str}, keep_default_na=False)
        assert len(batch) == expected[group]
        assert not batch.duplicated(["股票代码", "年份"]).any()
        for _, row in batch.iterrows():
            key = (str(row["股票代码"]), int(row["年份"]))
            assert key not in normalized
            normalized[key] = normalize(group, row)

    assert len(normalized) == 62
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
    assert int(reviewed_after.sum()) == 849
    pd.testing.assert_frame_equal(
        protected, merged.loc[reviewed_before].reset_index(drop=True), check_dtype=False
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
    assert int((merged["严格样本结论"] == "是").sum()) == 192
    assert int((merged["扩展样本结论"] == "是").sum()) == 367
    assert int((merged["边界样本结论"] == "是").sum()) == 50
    merged.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    pending = merged.loc[~reviewed_after]
    print(
        "v31 rows=958; UVW=62; reviewed=849; pending="
        f"{len(pending)}; pending_companies={pending['股票代码'].nunique()}; "
        "strict=192; expanded=367; boundary=50"
    )


if __name__ == "__main__":
    main()
