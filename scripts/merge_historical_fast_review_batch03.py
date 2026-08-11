#!/usr/bin/env python3
"""Merge historical fast-review batch 03 while preserving all prior reviews."""
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v12_跨年快速复核第二批.csv"
BATCH = ROOT / "outputs" / "跨年快速复核第三批_6家公司24条_v1.csv"
OUTPUT = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v13_跨年快速复核第三批.csv"


def main() -> None:
    source = pd.read_csv(SOURCE, dtype={"股票代码": str})
    batch = pd.read_csv(BATCH, dtype={"股票代码": str})
    assert len(source) == 958 and len(batch) == 24
    assert not source.duplicated(["股票代码", "年份"]).any()
    assert not batch.duplicated(["股票代码", "年份"]).any()
    before_2023 = source[source["年份"].eq(2023)].reset_index(drop=True).copy()

    merged = source.copy()
    editable = [
        "涉农业务名称", "涉农业务营业收入", "公司营业收入", "涉农收入占比",
        "是否存在分部收入重叠", "严格样本结论", "扩展样本结论", "边界样本结论",
        "纳入或剔除理由", "复核状态", "口径提示",
    ]
    merged[editable] = merged[editable].astype("object")
    updates = batch.set_index(["股票代码", "年份"])
    updated = 0
    for index, row in merged.iterrows():
        key = (row["股票代码"], int(row["年份"]))
        if key not in updates.index:
            continue
        assert not str(row["复核状态"]).startswith("已人工复核")
        update = updates.loc[key]
        mapping = {
            "涉农业务名称": "直接涉农业务_保守不重叠口径",
            "涉农业务营业收入": "直接涉农业务营业收入_元",
            "公司营业收入": "公司营业收入_元",
            "涉农收入占比": "直接涉农收入占比",
            "是否存在分部收入重叠": "是否存在分部收入重叠",
            "严格样本结论": "严格样本结论", "扩展样本结论": "扩展样本结论",
            "边界样本结论": "边界样本结论", "纳入或剔除理由": "复核说明",
        }
        for target, origin in mapping.items():
            merged.at[index, target] = update[origin]
        merged.at[index, "复核状态"] = "已人工复核（跨年快速核对第三批）"
        merged.at[index, "口径提示"] = "逐年核对当年官方年报营业收入构成表与合并利润表；未复制相邻年份数值。"
        updated += 1

    assert updated == 24 and len(merged) == 958
    assert not merged.duplicated(["股票代码", "年份"]).any()
    assert merged["复核状态"].str.startswith("已人工复核", na=False).sum() == 214
    pd.testing.assert_frame_equal(
        before_2023, merged[merged["年份"].eq(2023)].reset_index(drop=True), check_dtype=False
    )
    changed = (source.fillna("<NA>") != merged.fillna("<NA>")).any(axis=1)
    assert set(map(tuple, merged.loc[changed, ["股票代码", "年份"]].values.tolist())) == set(
        map(tuple, batch[["股票代码", "年份"]].values.tolist())
    )
    merged.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("v13 rows=958; new reviews=24; cumulative reviewed=214; 2023 unchanged")


if __name__ == "__main__":
    main()
