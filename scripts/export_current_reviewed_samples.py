#!/usr/bin/env python3
"""Export all-year reviewed sample tables without treating pending rows as exclusions."""
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v15_跨年快速复核第五批.csv"
OUT = ROOT / "outputs"
KEEP = [
    "股票代码", "公司全称", "年份", "行业分类代码", "行业分类名称", "入口依据",
    "涉农业务名称", "涉农业务营业收入", "公司营业收入", "涉农收入占比",
    "是否存在分部收入重叠", "严格样本结论", "扩展样本结论", "边界样本结论",
    "纳入或剔除理由", "当年曾ST_已核实", "年末ST_已核实", "当年退市整理期_已核实",
    "年报链接", "年报主营业务表PDF页序号", "利润表PDF页序号", "复核状态", "口径提示",
]


def write(df, name):
    df[KEEP].sort_values(["年份", "股票代码"]).to_csv(OUT / name, index=False, encoding="utf-8-sig")


def main():
    df = pd.read_csv(SOURCE, dtype={"股票代码": str})
    reviewed = df["复核状态"].str.startswith("已人工复核", na=False)
    strict = df[reviewed & df["严格样本结论"].eq("是")]
    expanded = df[reviewed & df["扩展样本结论"].eq("是")]
    boundary = df[reviewed & df["边界样本结论"].eq("是")]
    excluded = df[reviewed & df["严格样本结论"].eq("否") & df["扩展样本结论"].eq("否") & ~df["边界样本结论"].eq("是")]
    unresolved_reviewed = df[reviewed & (~df["严格样本结论"].isin(["是", "否"]) | ~df["扩展样本结论"].isin(["是", "否"]))]
    pending = df[~reviewed]
    write(strict, "全期严格样本_当前已核实_v1.csv")
    write(expanded, "全期扩展样本_当前已核实_v1.csv")
    write(boundary, "全期边界样本_当前已核实_v1.csv")
    write(excluded, "全期剔除记录_当前已核实_v1.csv")
    write(unresolved_reviewed, "全期已复核但结论仍待核实_v1.csv")
    write(pending, "全期待人工复核候选记录_v1.csv")

    known_st = strict["当年曾ST_已核实"].eq("是") | strict["年末ST_已核实"].eq("是")
    known_delist = strict["当年退市整理期_已核实"].eq("是")
    provisional = strict[~known_st & ~known_delist]
    write(provisional, "全期严格样本_剔除已知ST退整_暂定回归入口_v1.csv")
    print({"reviewed": int(reviewed.sum()), "strict": len(strict), "expanded": len(expanded),
           "boundary": len(boundary), "excluded": len(excluded),
           "reviewed_unresolved": len(unresolved_reviewed), "pending": len(pending),
           "strict_after_known_ST_delist": len(provisional)})


if __name__ == "__main__":
    main()
