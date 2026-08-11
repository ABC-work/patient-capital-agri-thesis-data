#!/usr/bin/env python3
"""Merge audited batch-17 R group into v28."""
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v28_跨年快速复核第十七批第一组.csv"
BATCH = ROOT / "outputs" / "跨年快速复核第十七批_R组_3家公司.csv"
OUTPUT = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v29_跨年快速复核第十七批第二组.csv"


def main() -> None:
    source = pd.read_csv(SOURCE, dtype={"股票代码": str}, keep_default_na=False)
    batch = pd.read_csv(BATCH, dtype={"股票代码": str}, keep_default_na=False)
    assert len(source) == 958 and len(batch) == 21
    assert not batch.duplicated(["股票代码", "年份"]).any()
    verified_before = source["复核状态"].str.startswith("已人工复核", na=False)
    assert int(verified_before.sum()) == 736
    protected = source.loc[verified_before].reset_index(drop=True).copy()
    updates = batch.set_index(["股票代码", "年份"])
    merged = source.copy()
    editable = [
        "涉农业务名称", "涉农业务营业收入", "公司营业收入", "涉农收入占比",
        "是否存在分部收入重叠", "严格样本结论", "扩展样本结论", "边界样本结论",
        "纳入或剔除理由", "复核状态", "口径提示", "年报主营业务表PDF页序号",
    ]
    merged[editable] = merged[editable].astype("object")
    for index, row in merged.iterrows():
        key = (str(row["股票代码"]), int(row["年份"]))
        if key not in updates.index:
            continue
        assert not str(row["复核状态"]).startswith("已人工复核")
        update = updates.loc[key]
        merged.at[index, "涉农业务名称"] = update["扩展口径涉农业务"]
        merged.at[index, "涉农业务营业收入"] = update["扩展口径正式涉农收入_元"]
        merged.at[index, "公司营业收入"] = update["公司营业收入_元"]
        merged.at[index, "涉农收入占比"] = ""
        merged.at[index, "是否存在分部收入重叠"] = update["是否存在分部收入重叠"]
        merged.at[index, "严格样本结论"] = update["严格样本结论"]
        merged.at[index, "扩展样本结论"] = update["扩展样本结论"]
        merged.at[index, "边界样本结论"] = update["边界样本结论"]
        merged.at[index, "纳入或剔除理由"] = update["纳入或剔除理由"]
        merged.at[index, "复核状态"] = "已人工复核（跨年快速核对第十七批R组）"
        merged.at[index, "口径提示"] = (
            "逐年核对官方年报；药品、饮片、食品和植物提取属于深加工；基地、种苗研发"
            "或优惠供苗不能替代已拆分收入，正式分子留空并以上界检验低于30%。 "
            + update["待核实点"]
        ).strip()
        merged.at[index, "年报主营业务表PDF页序号"] = update["年报主营业务证据PDF页序号"]

    assert len(merged) == 958
    assert not merged.duplicated(["股票代码", "年份"]).any()
    reviewed_after = merged["复核状态"].str.startswith("已人工复核", na=False)
    assert int(reviewed_after.sum()) == 757
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
    assert merged.loc[
        merged["年份"].eq(2022), ["行业分类代码", "行业分类名称"]
    ].eq("待核实").all().all()
    assert int((merged["严格样本结论"] == "是").sum()) == 192
    assert int((merged["扩展样本结论"] == "是").sum()) == 362
    assert int((merged["边界样本结论"] == "是").sum()) == 43
    merged.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("v29 rows=958; R=21; reviewed=757; strict=192; expanded=362; boundary=43")


if __name__ == "__main__":
    main()
