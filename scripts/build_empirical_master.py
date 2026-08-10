#!/usr/bin/env python3
"""Merge reviewed samples and real variable exports; never fabricate missing inputs."""
import argparse
from functools import reduce
from pathlib import Path

import pandas as pd


def load(path, label):
    df = pd.read_csv(path, dtype={"stock_code": str, "股票代码": str})
    df = df.rename(columns={"股票代码": "stock_code", "年份": "year"})
    needed = {"stock_code", "year"}
    if not needed.issubset(df):
        raise KeyError(f"{label} 缺少连接键 {sorted(needed-set(df.columns))}")
    df["stock_code"] = df["stock_code"].str.zfill(6)
    df["year"] = pd.to_numeric(df["year"], errors="raise").astype(int)
    if df.duplicated(["stock_code", "year"]).any():
        raise ValueError(f"{label} 存在重复公司—年份")
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", required=True)
    ap.add_argument("--x", required=True)
    ap.add_argument("--nqp", required=True)
    ap.add_argument("--financial", required=True)
    ap.add_argument("--governance", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--coverage", required=True)
    args = ap.parse_args()
    paths = vars(args)
    for name in ["sample", "x", "nqp", "financial", "governance"]:
        if not Path(paths[name]).is_file():
            raise FileNotFoundError(f"{name}正式输入不存在: {paths[name]}")

    s = load(args.sample, "sample")
    if "复核状态" in s:
        s = s[s["复核状态"].str.startswith("已人工复核", na=False)].copy()
    if "严格样本结论" in s:
        s = s[s["严格样本结论"] == "是"].copy()
    tables = [("X", load(args.x, "X")), ("NQP", load(args.nqp, "NQP")),
              ("financial", load(args.financial, "financial")),
              ("governance", load(args.governance, "governance"))]
    master = s
    audit = []
    for label, table in tables:
        before = len(master)
        nonkeys = [c for c in table if c not in {"stock_code", "year"}]
        collision = sorted(set(nonkeys) & set(master.columns))
        if collision:
            raise ValueError(f"{label} 与已有字段重名: {collision}")
        master = master.merge(table, on=["stock_code", "year"], how="left", validate="one_to_one", indicator="_merge")
        matched = int((master["_merge"] == "both").sum())
        audit.append({"module": label, "sample_rows": before, "matched_rows": matched,
                      "coverage": matched / before if before else None,
                      "unmatched_rows": before - matched})
        master = master.drop(columns="_merge")
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    master.to_csv(args.output, index=False, encoding="utf-8-sig")
    pd.DataFrame(audit).to_csv(args.coverage, index=False, encoding="utf-8-sig")
    print(pd.DataFrame(audit).to_string(index=False))


if __name__ == "__main__":
    main()
