#!/usr/bin/env python3
"""Merge audited batch 10 into v19 while protecting every prior review."""
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v19_跨年快速复核第九批.csv"
BATCH = ROOT / "outputs" / "跨年快速复核第十批_3家公司29条_v1.csv"
OUTPUT = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v20_跨年快速复核第十批.csv"


def main() -> None:
    source = pd.read_csv(SOURCE, dtype={"股票代码": str})
    batch = pd.read_csv(BATCH, dtype={"股票代码": str})
    assert len(source) == 958 and len(batch) == 29
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
        merged.at[index, "涉农业务营业收入"] = update["工作表采用涉农业务营业收入_元"]
        merged.at[index, "公司营业收入"] = update["公司营业收入_元"]
        merged.at[index, "涉农收入占比"] = update["工作表采用涉农收入占比"]
        merged.at[index, "是否存在分部收入重叠"] = update["是否存在分部收入重叠"]
        merged.at[index, "严格样本结论"] = update["严格样本结论"]
        merged.at[index, "扩展样本结论"] = update["扩展样本结论"]
        merged.at[index, "边界样本结论"] = update["边界样本结论"]
        merged.at[index, "纳入或剔除理由"] = update["复核说明"]
        merged.at[index, "复核状态"] = "已人工复核（跨年快速核对第十批）"
        precision_note = update.get("金额精度或补充证据说明", "")
        merged.at[index, "口径提示"] = (
            "逐年核对官方年报；扩展口径只计可识别初加工或农业投入品，排除贸易、熟食、"
            "成品羽绒、餐饮、殡葬、能源和资产处置。"
            + (f" {precision_note}" if isinstance(precision_note, str) and precision_note else "")
        )
        merged.at[index, "年报主营业务表PDF页序号"] = update["年报主营业务证据PDF页序号"]
        updated += 1

    assert updated == 29
    assert len(merged) == 958
    assert not merged.duplicated(["股票代码", "年份"]).any()
    reviewed_after = merged["复核状态"].str.startswith("已人工复核", na=False)
    assert int(reviewed_after.sum()) == 370
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
    assert merged.loc[merged["年份"].eq(2022), ["行业分类代码", "行业分类名称"]].eq("待核实").all().all()

    merged.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("v20 rows=958; batch10=29; cumulative reviewed=370; protected rows unchanged")


if __name__ == "__main__":
    main()
