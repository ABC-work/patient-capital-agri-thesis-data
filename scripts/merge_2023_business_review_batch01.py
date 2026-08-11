#!/usr/bin/env python3
"""Merge verified 2023 batch 01 into a new review worktable version.

The v1 worktable remains unchanged.  The detailed strict/expanded numerators stay
in the batch file; v2 stores the numerator that determines the row's current
classification (strict first, otherwise expanded/boundary).
"""

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v1.csv"
BATCH = ROOT / "outputs" / "2023年报主营业务人工复核_第一批10家_v1.csv"
OUTPUT = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v2.csv"


def main() -> None:
    table = pd.read_csv(SOURCE, dtype={"股票代码": str})
    batch = pd.read_csv(BATCH, dtype={"股票代码": str})
    assert len(table) == 958
    assert len(batch) == 10
    assert not batch.duplicated(["股票代码", "年份"]).any()

    # The empty review columns in v1 are inferred as float64 by pandas.  Cast
    # text destinations explicitly before assigning verified Chinese labels.
    text_columns = [
        "涉农业务名称", "是否存在分部收入重叠", "严格样本结论", "扩展样本结论",
        "边界样本结论", "纳入或剔除理由", "复核状态", "口径提示",
    ]
    table[text_columns] = table[text_columns].astype("object")

    keyed = batch.set_index(["股票代码", "年份"])
    updated = 0
    for idx, row in table.iterrows():
        key = (row["股票代码"], int(row["年份"]))
        if key not in keyed.index:
            continue
        item = keyed.loc[key]
        use_strict = item["严格样本结论"] == "是"
        if use_strict:
            business = item["严格口径涉农业务"]
            revenue = item["严格口径涉农收入_元"]
            share = item["严格口径涉农收入占比"]
        else:
            business = item["扩展口径涉农业务"]
            revenue = item["扩展口径涉农收入_元"]
            share = item["扩展口径涉农收入占比"]

        table.at[idx, "涉农业务名称"] = business
        table.at[idx, "涉农业务营业收入"] = revenue
        table.at[idx, "公司营业收入"] = item["公司营业收入_元"]
        table.at[idx, "涉农收入占比"] = share
        table.at[idx, "是否存在分部收入重叠"] = item["是否存在分部收入重叠"]
        table.at[idx, "严格样本结论"] = item["严格样本结论"]
        table.at[idx, "扩展样本结论"] = item["扩展样本结论"]
        table.at[idx, "边界样本结论"] = item["边界样本结论"]
        table.at[idx, "纳入或剔除理由"] = item["纳入或剔除理由"]
        table.at[idx, "复核状态"] = item["复核状态"]
        table.at[idx, "口径提示"] = (
            f"严格口径占比={item['严格口径涉农收入占比']}；"
            f"扩展口径占比={item['扩展口径涉农收入占比']}；"
            "两套分子详见2023年报主营业务人工复核_第一批10家_v1.csv"
        )
        updated += 1

    assert updated == 10
    assert len(table) == 958
    assert not table.duplicated(["股票代码", "年份"]).any()
    assert (table["复核状态"] == "已人工复核（第一批）").sum() == 10
    table.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print(f"Wrote {len(table)} rows to {OUTPUT}; updated {updated} verified rows; v1 untouched.")


if __name__ == "__main__":
    main()
