#!/usr/bin/env python3
"""Construct a dimension-balanced entropy NQP index from audited raw indicators."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_csv")
    ap.add_argument("config_json")
    ap.add_argument("output_csv")
    ap.add_argument("weights_csv")
    args = ap.parse_args()
    cfg = json.loads(Path(args.config_json).read_text(encoding="utf-8"))
    if cfg.get("missing_policy") != "complete_within_dimension":
        raise ValueError("当前版本只允许维度内完整观测；不做均值插补或零填充")
    specs = cfg["indicators"]
    cols = [x["column"] for x in specs]
    ids = cfg.get("id_columns", ["stock_code", "year"])
    df = pd.read_csv(args.input_csv, dtype={ids[0]: str})
    missing = sorted(set(ids + cols) - set(df.columns))
    if missing:
        raise KeyError(f"缺少NQP原始指标: {missing}")
    if df.duplicated(ids).any():
        raise ValueError("NQP输入存在重复公司—年份")
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors="raise")

    lo, hi = cfg.get("winsor_limits", [0.01, 0.99])
    z = pd.DataFrame(index=df.index)
    records = []
    eps = float(cfg.get("epsilon", 1e-12))
    dimensions = sorted({x["dimension"] for x in specs})
    for spec in specs:
        c, direction = spec["column"], spec["direction"]
        s = df[c].clip(df[c].quantile(lo), df[c].quantile(hi))
        span = s.max() - s.min()
        if pd.isna(span) or span <= 0:
            raise ValueError(f"{c} 无有效横截面变异，不能计算熵权")
        z[c] = (s - s.min()) / span if direction == "positive" else (s.max() - s) / span

    indicator_weight = {}
    for dim in dimensions:
        dcols = [x["column"] for x in specs if x["dimension"] == dim]
        complete = z[dcols].notna().all(axis=1)
        zz = z.loc[complete, dcols] + eps
        n = len(zz)
        if n <= 1:
            raise ValueError(f"维度{dim}完整观测不足")
        p = zz.div(zz.sum(axis=0), axis=1)
        entropy = -(p * np.log(p)).sum(axis=0) / np.log(n)
        diversity = 1 - entropy
        if diversity.sum() <= 0:
            raise ValueError(f"维度{dim}信息效用为0")
        within = diversity / diversity.sum()
        dim_weight = 1 / len(dimensions) if cfg.get("dimension_equal_weight", True) else 1
        for c in dcols:
            indicator_weight[c] = float(within[c] * dim_weight)
            records.append({"dimension": dim, "indicator": c,
                            "within_dimension_weight": float(within[c]),
                            "final_weight": indicator_weight[c],
                            "complete_n": n})

    df["NQP_entropy"] = sum(z[c] * w for c, w in indicator_weight.items())
    df["NQP_complete"] = z[cols].notna().all(axis=1).astype(int)
    df.loc[df["NQP_complete"] == 0, "NQP_entropy"] = np.nan
    Path(args.output_csv).parent.mkdir(parents=True, exist_ok=True)
    df[ids + cols + ["NQP_entropy", "NQP_complete"]].to_csv(args.output_csv, index=False, encoding="utf-8-sig")
    pd.DataFrame(records).to_csv(args.weights_csv, index=False, encoding="utf-8-sig")
    print(f"rows={len(df)}; complete NQP={int(df.NQP_complete.sum())}; dimensions={len(dimensions)}")


if __name__ == "__main__":
    main()
