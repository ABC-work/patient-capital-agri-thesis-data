#!/usr/bin/env python3
"""Merge audited batch 08 into v17 while protecting all prior reviews."""
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v17_跨年快速复核第七批.csv"
BATCH = ROOT / "outputs" / "跨年快速复核第八批_3家公司30条_v1.csv"
OUTPUT = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v18_跨年快速复核第八批.csv"


def value_or_na(value):
    return pd.NA if value == "" else value


def main() -> None:
    source = pd.read_csv(SOURCE, dtype={"股票代码": str})
    batch = pd.read_csv(BATCH, dtype={"股票代码": str}, keep_default_na=False)
    assert len(source) == 958 and len(batch) == 30
    assert not source.duplicated(["股票代码", "年份"]).any()
    assert not batch.duplicated(["股票代码", "年份"]).any()

    merged = source.copy()
    verified_before = source["复核状态"].str.startswith("已人工复核", na=False)
    protected = source.loc[verified_before].reset_index(drop=True).copy()
    editable = [
        "涉农业务名称", "涉农业务营业收入", "公司营业收入", "涉农收入占比",
        "是否存在分部收入重叠", "严格样本结论", "扩展样本结论", "边界样本结论",
        "纳入或剔除理由", "复核状态", "口径提示", "年报主营业务表PDF页序号",
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
        merged.at[index, "涉农业务营业收入"] = value_or_na(update["工作表采用涉农业务营业收入_元"])
        merged.at[index, "公司营业收入"] = update["公司营业收入_元"]
        merged.at[index, "涉农收入占比"] = value_or_na(update["工作表采用涉农收入占比"])
        merged.at[index, "是否存在分部收入重叠"] = update["是否存在分部收入重叠"]
        merged.at[index, "严格样本结论"] = update["严格样本结论"]
        merged.at[index, "扩展样本结论"] = update["扩展样本结论"]
        merged.at[index, "边界样本结论"] = update["边界样本结论"]
        merged.at[index, "纳入或剔除理由"] = update["复核说明"]
        merged.at[index, "复核状态"] = "已人工复核（跨年快速核对第八批）"
        merged.at[index, "口径提示"] = (
            "逐年核对官方年报；混合披露收入只作审计上界，不写入正式涉农分子；"
            "无法拆分初加工、深加工、贸易或自产/外购时明确标记待核实。"
        )
        merged.at[index, "年报主营业务表PDF页序号"] = update["年报主营业务证据PDF页序号"]
        updated += 1

    assert updated == 30
    assert len(merged) == 958
    assert not merged.duplicated(["股票代码", "年份"]).any()
    reviewed_after = merged["复核状态"].str.startswith("已人工复核", na=False)
    assert int(reviewed_after.sum()) == 311

    pd.testing.assert_frame_equal(
        protected, merged.loc[verified_before].reset_index(drop=True), check_dtype=False
    )
    changed = (source.fillna("<NA>") != merged.fillna("<NA>")).any(axis=1)
    changed_keys = set(map(tuple, merged.loc[changed, ["股票代码", "年份"]].values.tolist()))
    batch_keys = set(map(tuple, batch[["股票代码", "年份"]].values.tolist()))
    assert changed_keys == batch_keys
    pd.testing.assert_frame_equal(
        source[source["年份"].eq(2023)].reset_index(drop=True),
        merged[merged["年份"].eq(2023)].reset_index(drop=True),
        check_dtype=False,
    )

    # Unresolved rows must not acquire a formal numerator or ratio.
    unresolved = merged[merged["股票代码"].isin(["300094", "601118"]) & merged["年份"].between(2013, 2022)]
    assert len(unresolved) == 20
    assert unresolved["涉农业务营业收入"].isna().all()
    assert unresolved["涉农收入占比"].isna().all()

    merged.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("v18 rows=958; batch08=30; cumulative reviewed=311; protected rows unchanged")


if __name__ == "__main__":
    main()
