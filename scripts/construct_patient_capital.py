#!/usr/bin/env python3
"""Construct PatientCapital only after the actual RESSET export header is mapped."""
import argparse
import json
from pathlib import Path

import pandas as pd


BASE = [
    "insurance_hold_pct_total",
    "social_security_hold_pct_total",
    "enterprise_annuity_hold_pct_total",
]
ROBUST = {
    "patient_capital_a": [
        "insurance_hold_pct_a", "social_security_hold_pct_a",
        "enterprise_annuity_hold_pct_a",
    ],
    "patient_capital_unrestricted_a": [
        "insurance_hold_pct_unrestricted_a",
        "social_security_hold_pct_unrestricted_a",
        "enterprise_annuity_hold_pct_unrestricted_a",
    ],
}
ABSENCE_AUDIT = {
    "insurance_hold_pct_total": (
        "insurance_hold_shares_total", "insurance_holder_count_total",
        "all_institution_hold_pct_total",
    ),
    "social_security_hold_pct_total": (
        "social_security_hold_shares_total", "social_security_holder_count_total",
        "all_institution_hold_pct_total",
    ),
    "enterprise_annuity_hold_pct_total": (
        "enterprise_annuity_hold_shares_total", "enterprise_annuity_holder_count_total",
        "all_institution_hold_pct_total",
    ),
    "insurance_hold_pct_a": (
        "insurance_hold_shares_a", "insurance_holder_count_a", "all_institution_hold_pct_a",
    ),
    "social_security_hold_pct_a": (
        "social_security_hold_shares_a", "social_security_holder_count_a",
        "all_institution_hold_pct_a",
    ),
    "enterprise_annuity_hold_pct_a": (
        "enterprise_annuity_hold_shares_a", "enterprise_annuity_holder_count_a",
        "all_institution_hold_pct_a",
    ),
    "insurance_hold_pct_unrestricted_a": (
        "insurance_hold_shares_unrestricted_a", "insurance_holder_count_unrestricted_a",
        "all_institution_hold_pct_unrestricted_a",
    ),
    "social_security_hold_pct_unrestricted_a": (
        "social_security_hold_shares_unrestricted_a", "social_security_holder_count_unrestricted_a",
        "all_institution_hold_pct_unrestricted_a",
    ),
    "enterprise_annuity_hold_pct_unrestricted_a": (
        "enterprise_annuity_hold_shares_unrestricted_a", "enterprise_annuity_holder_count_unrestricted_a",
        "all_institution_hold_pct_unrestricted_a",
    ),
}


def read_table(path):
    path = Path(path)
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path, dtype=str)
    return pd.read_csv(path, dtype=str)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("mapping_json")
    ap.add_argument("output")
    args = ap.parse_args()
    cfg = json.loads(Path(args.mapping_json).read_text(encoding="utf-8"))
    unit = cfg.get("ratio_unit")
    if unit not in {"percent", "fraction"}:
        raise ValueError("ratio_unit 必须由人工核实后明确写为 percent 或 fraction")
    missing_policy = cfg.get("missing_component_policy")
    if missing_policy not in {"propagate", "audited_structural_zero"}:
        raise ValueError("missing_component_policy须为propagate或audited_structural_zero")

    raw = read_table(args.input)
    mapping = cfg.get("column_map", {})
    absent = sorted(set(mapping) - set(raw.columns))
    if absent:
        raise KeyError(f"正式导出缺少已映射表头: {absent}")
    df = raw.rename(columns=mapping).copy()
    required = {"stock_code", "end_date", *BASE}
    missing = sorted(required - set(df.columns))
    if missing:
        raise KeyError(f"映射后缺少基准字段: {missing}")

    df["stock_code"] = df["stock_code"].str.extract(r"(\d+)", expand=False).str.zfill(6)
    df["end_date"] = pd.to_datetime(df["end_date"], errors="raise")
    df = df[df["end_date"].dt.strftime("%m-%d") == "12-31"].copy()
    df["year"] = df["end_date"].dt.year
    if df.empty:
        raise ValueError("过滤后没有12月31日记录；不得以三季度替代")

    ratio_cols = [c for c in BASE + sum(ROBUST.values(), []) if c in df]
    for col in ratio_cols:
        df[col] = pd.to_numeric(df[col], errors="raise")
        if unit == "percent":
            df[col] = df[col] / 100.0
        if ((df[col].dropna() < 0) | (df[col].dropna() > 1)).any():
            raise ValueError(f"{col} 转为小数后超出[0,1]，请复核单位或字段")

    if missing_policy == "audited_structural_zero":
        diagnostic_cols = sorted({x for c in ratio_cols for x in ABSENCE_AUDIT[c]})
        missing_diagnostics = sorted(set(diagnostic_cols) - set(df.columns))
        if missing_diagnostics:
            raise KeyError(f"结构性零值判断缺少审计字段: {missing_diagnostics}")
        for col in diagnostic_cols:
            df[col] = pd.to_numeric(df[col], errors="raise")

    key = ["stock_code", "year"]
    if df.duplicated(key).any():
        if cfg.get("duplicate_policy") != "latest_stat_date" or "stat_date" not in df:
            raise ValueError("公司—年份存在重复；须保留stat_date并明确版本规则")
        df["stat_date"] = pd.to_datetime(df["stat_date"], errors="raise")
        same_day_duplicate = df.duplicated([*key, "stat_date"], keep=False)
        if same_day_duplicate.any() and not {"update_date", "resset_row_id"}.issubset(df.columns):
            raise ValueError("同一公司—年份—统计日期存在重复；须保留update_date和resset_row_id择新")
        version_order = [*key, "stat_date"]
        if "update_date" in df:
            df["update_date"] = pd.to_datetime(df["update_date"], errors="raise")
            version_order.append("update_date")
        if "resset_row_id" in df:
            df["resset_row_id"] = pd.to_numeric(df["resset_row_id"], errors="raise")
            version_order.append("resset_row_id")
        df = df.sort_values(version_order).drop_duplicates(key, keep="last")

    structural_flags = []
    if missing_policy == "audited_structural_zero":
        for ratio in ratio_cols:
            shares, count, institutional_total = ABSENCE_AUDIT[ratio]
            signature = df[[ratio, shares, count]].notna().sum(axis=1)
            if signature.isin([1, 2]).any():
                bad = int(signature.isin([1, 2]).sum())
                raise ValueError(f"{ratio}有{bad}条比例/持股数/机构数不一致，禁止自动补0")
            flag = f"{ratio}_structural_zero"
            df[flag] = signature.eq(0) & df[institutional_total].notna()
            df.loc[df[flag], ratio] = 0.0
            structural_flags.append(flag)

    df["patient_capital_total"] = df[BASE].sum(axis=1, min_count=len(BASE))
    for out, cols in ROBUST.items():
        if set(cols).issubset(df.columns):
            df[out] = df[cols].sum(axis=1, min_count=len(cols))
    keep = key + [c for c in [*BASE, "patient_capital_total", *ROBUST, *structural_flags] if c in df]
    out = df[keep].sort_values(key)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"rows={len(out)}; firms={out.stock_code.nunique()}; years={out.year.min()}-{out.year.max()}")
    print("patient_capital_total missing=", int(out.patient_capital_total.isna().sum()))


if __name__ == "__main__":
    main()
