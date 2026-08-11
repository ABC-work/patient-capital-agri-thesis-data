#!/usr/bin/env python3
"""Merge historical fast-review batch 02 without touching prior reviews."""
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v11_跨年快速复核试验.csv"
BATCH = ROOT / "outputs" / "跨年快速复核第二批_4家公司30条_v1.csv"
OUTPUT = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v12_跨年快速复核第二批.csv"


def main() -> None:
    source = pd.read_csv(SOURCE, dtype={"股票代码": str})
    batch = pd.read_csv(BATCH, dtype={"股票代码": str})
    assert len(source) == 958 and len(batch) == 30
    assert not source.duplicated(["股票代码", "年份"]).any()
    assert not batch.duplicated(["股票代码", "年份"]).any()

    # Preserve the entire pre-existing 2023 block byte-for-value at the dataframe
    # level. The batch contains historical years only.
    before_2023 = source[source["年份"].eq(2023)].reset_index(drop=True).copy()
    assert batch["年份"].between(2013, 2021).all()

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
        merged.at[index, "涉农业务名称"] = update["直接涉农业务_保守不重叠口径"]
        merged.at[index, "涉农业务营业收入"] = update["直接涉农业务营业收入_元"]
        merged.at[index, "公司营业收入"] = update["公司营业收入_元"]
        merged.at[index, "涉农收入占比"] = update["直接涉农收入占比"]
        merged.at[index, "是否存在分部收入重叠"] = update["是否存在分部收入重叠"]
        merged.at[index, "严格样本结论"] = update["严格样本结论"]
        merged.at[index, "扩展样本结论"] = update["扩展样本结论"]
        merged.at[index, "边界样本结论"] = update["边界样本结论"]
        merged.at[index, "纳入或剔除理由"] = update["复核说明"]
        merged.at[index, "复核状态"] = "已人工复核（跨年快速核对第二批）"
        merged.at[index, "口径提示"] = (
            "按公司跨年比较后逐年核对当年官方年报业务表与合并利润表；"
            "未复制、插值或外推相邻年份数值。"
        )
        updated += 1

    assert updated == 30
    assert len(merged) == 958
    assert not merged.duplicated(["股票代码", "年份"]).any()
    assert merged["复核状态"].str.startswith("已人工复核", na=False).sum() == 190

    after_2023 = merged[merged["年份"].eq(2023)].reset_index(drop=True)
    pd.testing.assert_frame_equal(before_2023, after_2023, check_dtype=False)

    # Only the intended 30 historical rows may differ from v11.
    changed = (source.fillna("<NA>") != merged.fillna("<NA>")).any(axis=1)
    changed_keys = set(map(tuple, merged.loc[changed, ["股票代码", "年份"]].values.tolist()))
    batch_keys = set(map(tuple, batch[["股票代码", "年份"]].values.tolist()))
    assert changed_keys == batch_keys

    merged.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("merged rows=958; new reviews=30; cumulative reviewed=190; 2023 unchanged")


if __name__ == "__main__":
    main()
