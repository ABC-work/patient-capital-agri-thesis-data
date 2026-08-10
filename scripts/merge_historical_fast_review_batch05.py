#!/usr/bin/env python3
"""Merge historical fast-review batch 05 while preserving all prior reviews."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v14_跨年快速复核第四批.csv"
BATCH = ROOT / "outputs" / "跨年快速复核第五批_神农科技9条_v1.csv"
OUTPUT = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v15_跨年快速复核第五批.csv"


def main():
    source = pd.read_csv(SOURCE, dtype={"股票代码": str})
    batch = pd.read_csv(BATCH, dtype={"股票代码": str})
    assert len(source) == 958 and len(batch) == 9
    before_2023 = source[source["年份"].eq(2023)].reset_index(drop=True).copy()
    merged = source.copy()
    editable = ["涉农业务名称", "涉农业务营业收入", "公司营业收入", "涉农收入占比", "是否存在分部收入重叠", "严格样本结论", "扩展样本结论", "边界样本结论", "纳入或剔除理由", "复核状态", "口径提示"]
    merged[editable] = merged[editable].astype("object")
    updates = batch.set_index(["股票代码", "年份"])
    mapping = {"涉农业务名称": "直接涉农业务_保守不重叠口径", "涉农业务营业收入": "直接涉农业务营业收入_元", "公司营业收入": "公司营业收入_元", "涉农收入占比": "直接涉农收入占比", "是否存在分部收入重叠": "是否存在分部收入重叠", "严格样本结论": "严格样本结论", "扩展样本结论": "扩展样本结论", "边界样本结论": "边界样本结论", "纳入或剔除理由": "复核说明"}
    n = 0
    for i, row in merged.iterrows():
        key = (row["股票代码"], int(row["年份"]))
        if key not in updates.index:
            continue
        assert not str(row["复核状态"]).startswith("已人工复核")
        update = updates.loc[key]
        for target, origin in mapping.items():
            merged.at[i, target] = update[origin]
        merged.at[i, "复核状态"] = "已人工复核（跨年快速核对第五批）"
        merged.at[i, "口径提示"] = "逐年核对官方年报分产品收入，业务转型年份按当年实际口径判定。"
        n += 1
    assert n == 9 and len(merged) == 958
    assert merged["复核状态"].str.startswith("已人工复核", na=False).sum() == 232
    pd.testing.assert_frame_equal(before_2023, merged[merged["年份"].eq(2023)].reset_index(drop=True), check_dtype=False)
    changed = (source.fillna("<NA>") != merged.fillna("<NA>")).any(axis=1)
    assert set(map(tuple, merged.loc[changed, ["股票代码", "年份"]].values.tolist())) == set(map(tuple, batch[["股票代码", "年份"]].values.tolist()))
    merged.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("v15 rows=958; new reviews=9; cumulative reviewed=232; 2023 unchanged")


if __name__ == "__main__":
    main()
