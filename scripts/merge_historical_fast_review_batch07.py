#!/usr/bin/env python3
"""Merge batch 07 into v16 while protecting every existing verified row."""
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v16_跨年快速复核第六批.csv"
BATCH = ROOT / "outputs" / "跨年快速复核第七批_3家公司22条_v1.csv"
OUTPUT = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v17_跨年快速复核第七批.csv"


def main() -> None:
    source = pd.read_csv(SOURCE, dtype={"股票代码": str})
    batch = pd.read_csv(BATCH, dtype={"股票代码": str})
    assert len(source) == 958 and len(batch) == 22
    assert not source.duplicated(["股票代码", "年份"]).any()
    assert not batch.duplicated(["股票代码", "年份"]).any()

    merged = source.copy()
    verified_before = source["复核状态"].str.startswith("已人工复核", na=False)
    assert verified_before.sum() == 259
    protected = source.loc[verified_before].reset_index(drop=True).copy()
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
        merged.at[index, "涉农业务名称"] = update["涉农业务_保守不重叠口径"]
        merged.at[index, "涉农业务营业收入"] = update["工作表采用涉农业务营业收入_元"]
        merged.at[index, "公司营业收入"] = update["公司营业收入_元"]
        merged.at[index, "涉农收入占比"] = update["工作表采用涉农收入占比"]
        merged.at[index, "是否存在分部收入重叠"] = update["是否存在分部收入重叠"]
        merged.at[index, "严格样本结论"] = update["严格样本结论"]
        merged.at[index, "扩展样本结论"] = update["扩展样本结论"]
        merged.at[index, "边界样本结论"] = update["边界样本结论"]
        merged.at[index, "纳入或剔除理由"] = update["复核说明"]
        merged.at[index, "复核状态"] = "已人工复核（跨年快速核对第七批）"
        merged.at[index, "口径提示"] = (
            "逐年核对当年官方年报；严格口径为直接养殖，扩展口径可加入同一披露维度的初加工；"
            "不跨行业、产品、地区维度相加。"
        )
        updated += 1

    assert updated == 22
    assert len(merged) == 958
    assert not merged.duplicated(["股票代码", "年份"]).any()
    assert merged["复核状态"].str.startswith("已人工复核", na=False).sum() == 281

    protected_after = merged.loc[verified_before].reset_index(drop=True)
    pd.testing.assert_frame_equal(protected, protected_after, check_dtype=False)
    changed = (source.fillna("<NA>") != merged.fillna("<NA>")).any(axis=1)
    changed_keys = set(map(tuple, merged.loc[changed, ["股票代码", "年份"]].values.tolist()))
    batch_keys = set(map(tuple, batch[["股票代码", "年份"]].values.tolist()))
    assert changed_keys == batch_keys

    pd.testing.assert_frame_equal(
        source[source["年份"].eq(2023)].reset_index(drop=True),
        merged[merged["年份"].eq(2023)].reset_index(drop=True),
        check_dtype=False,
    )

    merged.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("v17 rows=958; new reviews=22; cumulative reviewed=281; protected rows unchanged")


if __name__ == "__main__":
    main()
