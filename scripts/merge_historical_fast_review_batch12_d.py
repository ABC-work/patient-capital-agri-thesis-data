#!/usr/bin/env python3
"""Merge the independently audited batch-12 D group into v21."""
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v21_跨年快速复核第十一批.csv"
BATCH = ROOT / "outputs" / "跨年快速复核第十二批_D组_3家公司.csv"
OUTPUT = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v22_跨年快速复核第十二批.csv"


def main() -> None:
    source = pd.read_csv(SOURCE, dtype={"股票代码": str}, keep_default_na=False)
    batch = pd.read_csv(BATCH, dtype={"股票代码": str}, keep_default_na=False)
    assert len(source) == 958 and len(batch) == 26
    assert not source.duplicated(["股票代码", "年份"]).any()
    assert not batch.duplicated(["股票代码", "年份"]).any()

    verified_before = source["复核状态"].str.startswith("已人工复核", na=False)
    assert int(verified_before.sum()) == 451
    protected = source.loc[verified_before].reset_index(drop=True).copy()
    merged = source.copy()
    editable = [
        "涉农业务名称", "涉农业务营业收入", "公司营业收入", "涉农收入占比",
        "是否存在分部收入重叠", "严格样本结论", "扩展样本结论", "边界样本结论",
        "纳入或剔除理由", "复核状态", "口径提示", "年报主营业务表PDF页序号",
    ]
    merged[editable] = merged[editable].astype("object")
    updates = batch.set_index(["股票代码", "年份"])
    updated = 0
    for index, row in merged.iterrows():
        key = (str(row["股票代码"]), int(row["年份"]))
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
        merged.at[index, "复核状态"] = "已人工复核（跨年快速核对第十二批D组）"
        merged.at[index, "口径提示"] = (
            "逐年核对官方年报；纤维板/人造板、园林工程、租摆和贸易不计入初加工；"
            "自产育种与外购或进口混合且跨门槛时保留上下界。 " + update["待核实点"]
        ).strip()
        merged.at[index, "年报主营业务表PDF页序号"] = update["年报主营业务证据PDF页序号"]
        updated += 1

    assert updated == 26
    assert len(merged) == 958
    assert not merged.duplicated(["股票代码", "年份"]).any()
    reviewed_after = merged["复核状态"].str.startswith("已人工复核", na=False)
    assert int(reviewed_after.sum()) == 477
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
    assert int((merged["严格样本结论"] == "是").sum()) == 178
    assert int((merged["扩展样本结论"] == "是").sum()) == 292
    assert int((merged["边界样本结论"] == "是").sum()) == 26

    merged.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("v22 rows=958; batch12D=26; reviewed=477; strict=178; expanded=292; boundary=26")


if __name__ == "__main__":
    main()
