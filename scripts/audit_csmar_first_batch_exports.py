#!/usr/bin/env python3
"""Audit the first three raw CSMAR financial-statement exports.

This program deliberately does not map financial values, calculate variables,
deduplicate observations, or overwrite source files.  Every source-column name
comes from a user-edited JSON mapping.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


TABLE_LABELS = {
    "balance_sheet": "资产负债表",
    "income_statement": "利润表",
    "cashflow_statement": "现金流量表",
}
REQUIRED_KEYS = ("stock_code", "accounting_period")
OPTIONAL_AUDIT_KEYS = ("company_name", "report_type", "statement_scope", "unit")
PLACEHOLDER_MARKERS = ("页面确认", "填写", "replace", "placeholder")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit CSMAR balance-sheet, income-statement and cash-flow exports."
    )
    parser.add_argument("--balance", required=True, help="Balance-sheet CSV/XLSX")
    parser.add_argument("--income", required=True, help="Income-statement CSV/XLSX")
    parser.add_argument("--cashflow", required=True, help="Cash-flow CSV/XLSX")
    parser.add_argument("--mapping", required=True, help="User-edited JSON mapping")
    parser.add_argument("--codes", required=True, help="Expected six-digit stock codes, one per line")
    parser.add_argument("--output-dir", required=True, help="Directory for audit-only outputs")
    parser.add_argument(
        "--header-only",
        action="store_true",
        help="Validate headers/mapping with zero-row fixtures; skip data-quality failures.",
    )
    return parser.parse_args()


def unresolved(value: Any) -> bool:
    if value is None or not str(value).strip():
        return True
    lowered = str(value).lower()
    return any(marker.lower() in lowered for marker in PLACEHOLDER_MARKERS)


def load_mapping(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        mapping = json.load(handle)
    if "tables" not in mapping or not isinstance(mapping["tables"], dict):
        raise ValueError("Mapping JSON must contain an object named 'tables'.")
    absent = sorted(set(TABLE_LABELS) - set(mapping["tables"]))
    if absent:
        raise ValueError(f"Mapping JSON lacks table sections: {absent}")
    return mapping


def load_codes(path: Path) -> list[str]:
    codes = [line.strip() for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    invalid = sorted({code for code in codes if not re.fullmatch(r"\d{6}", code)})
    duplicates = sorted(code for code, count in Counter(codes).items() if count > 1)
    if invalid:
        raise ValueError(f"Expected-code file contains non-six-digit values: {invalid[:10]}")
    if duplicates:
        raise ValueError(f"Expected-code file contains duplicates: {duplicates[:10]}")
    if not codes:
        raise ValueError("Expected-code file is empty.")
    return codes


def read_delimited(path: Path, delimiter: str | None) -> tuple[pd.DataFrame, str]:
    encodings = ("utf-8-sig", "gb18030")
    errors: list[str] = []
    for encoding in encodings:
        try:
            kwargs: dict[str, Any] = {
                "dtype": str,
                "keep_default_na": False,
                "encoding": encoding,
            }
            if delimiter:
                kwargs["sep"] = delimiter
            else:
                kwargs.update({"sep": None, "engine": "python"})
            return pd.read_csv(path, **kwargs), encoding
        except UnicodeDecodeError as exc:
            errors.append(f"{encoding}: {exc}")
    raise UnicodeError("; ".join(errors))


def read_source(path: Path, table_cfg: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        sheet_name = table_cfg.get("sheet_name", 0)
        df = pd.read_excel(path, sheet_name=sheet_name, dtype=str, keep_default_na=False)
        read_meta = {"format": suffix.lstrip("."), "sheet_name": sheet_name, "encoding": None}
    elif suffix in {".csv", ".txt"}:
        df, encoding = read_delimited(path, table_cfg.get("delimiter"))
        read_meta = {"format": suffix.lstrip("."), "sheet_name": None, "encoding": encoding}
    else:
        raise ValueError(f"Unsupported input extension for {path}: use CSV, TXT, XLSX or XLS")
    df.columns = [str(column).strip() for column in df.columns]
    duplicate_headers = sorted(column for column, count in Counter(df.columns).items() if count > 1)
    if duplicate_headers:
        raise ValueError(f"Duplicate source headers in {path.name}: {duplicate_headers}")
    return df, read_meta


def distribution(series: pd.Series, limit: int = 100) -> tuple[list[dict[str, Any]], bool]:
    values = series.astype(str).map(str.strip).replace("", "<BLANK>")
    counts = values.value_counts(dropna=False)
    rows = [{"value": str(value), "count": int(count)} for value, count in counts.head(limit).items()]
    return rows, len(counts) > limit


def audit_table(
    key: str,
    source_path: Path,
    table_cfg: dict[str, Any],
    expected_codes: set[str],
    expected_start: pd.Timestamp,
    expected_end: pd.Timestamp,
    annual_month_day: str,
    header_only: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]], pd.DataFrame, set[str], set[tuple[str, int]]]:
    df, read_meta = read_source(source_path, table_cfg)
    fields = table_cfg.get("fields", {})
    if not isinstance(fields, dict):
        raise ValueError(f"tables.{key}.fields must be an object")

    mapped: dict[str, str] = {}
    unmapped: list[str] = []
    absent_headers: list[str] = []
    for logical in (*REQUIRED_KEYS, *OPTIONAL_AUDIT_KEYS):
        source_column = fields.get(logical)
        if unresolved(source_column):
            unmapped.append(logical)
        elif str(source_column) not in df.columns:
            absent_headers.append(str(source_column))
        else:
            mapped[logical] = str(source_column)

    fatal_mapping = [logical for logical in REQUIRED_KEYS if logical not in mapped]
    statuses: list[dict[str, Any]] = []

    def add(check: str, status: str, detail: str) -> None:
        statuses.append({"table_key": key, "table_label": TABLE_LABELS[key], "check": check, "status": status, "detail": detail})

    add("source_read", "PASS", f"{source_path.name}; format={read_meta['format']}; rows={len(df)}; columns={len(df.columns)}")
    add("required_mapping", "FAIL" if fatal_mapping else "PASS", f"unresolved_or_absent={fatal_mapping or 'none'}")
    add("optional_mapping", "WARN" if unmapped or absent_headers else "PASS", f"unmapped={unmapped}; absent_headers={absent_headers}")
    add("row_count", "PASS" if len(df) > 0 else ("SKIP" if header_only else "FAIL"), str(len(df)))

    result: dict[str, Any] = {
        "table_key": key,
        "table_label": TABLE_LABELS[key],
        "source_file": str(source_path.resolve()),
        "read_metadata": read_meta,
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "source_headers": list(df.columns),
        "mapped_fields": mapped,
        "unmapped_logical_fields": unmapped,
        "mapped_headers_absent_from_source": absent_headers,
    }
    empty_duplicates = pd.DataFrame(columns=["table_key", "stock_code_raw", "year", "duplicate_row_count"])
    if fatal_mapping or header_only:
        for audit_key in ("date_range", "stock_code_format", "report_type_distribution", "statement_scope_distribution", "unit_distribution", "company_year_duplicates", "expected_code_coverage"):
            add(audit_key, "SKIP", "header-only or required mapping unresolved")
        result.update({
            "date_audit": None,
            "stock_code_audit": None,
            "value_distributions": {},
            "duplicate_company_year_keys": 0,
            "duplicate_company_year_rows": 0,
            "expected_code_coverage": None,
        })
        return result, statuses, empty_duplicates, set(), set()

    code_col = mapped["stock_code"]
    date_col = mapped["accounting_period"]
    codes_raw = df[code_col].astype(str).map(str.strip)
    valid_code_mask = codes_raw.str.fullmatch(r"\d{6}", na=False)
    invalid_codes = sorted(set(codes_raw[~valid_code_mask]))
    observed_codes = set(codes_raw[valid_code_mask])
    missing_codes = sorted(expected_codes - observed_codes)
    unexpected_codes = sorted(observed_codes - expected_codes)
    coverage_rate = len(expected_codes & observed_codes) / len(expected_codes)
    add("stock_code_format", "PASS" if not invalid_codes else "FAIL", f"invalid_rows={int((~valid_code_mask).sum())}; examples={invalid_codes[:10]}")
    add("expected_code_coverage", "PASS" if not missing_codes and not unexpected_codes else "WARN", f"covered={len(expected_codes & observed_codes)}/{len(expected_codes)}; missing={len(missing_codes)}; unexpected={len(unexpected_codes)}")

    parsed_dates = pd.to_datetime(df[date_col].astype(str).str.strip(), errors="coerce")
    invalid_date_rows = int(parsed_dates.isna().sum())
    valid_dates = parsed_dates.dropna()
    out_of_range = int(((valid_dates < expected_start) | (valid_dates > expected_end)).sum())
    expected_month, expected_day = map(int, annual_month_day.split("-"))
    non_annual = int(((valid_dates.dt.month != expected_month) | (valid_dates.dt.day != expected_day)).sum())
    date_status = "PASS" if invalid_date_rows == 0 and out_of_range == 0 and non_annual == 0 else "FAIL"
    date_min = valid_dates.min().strftime("%Y-%m-%d") if not valid_dates.empty else None
    date_max = valid_dates.max().strftime("%Y-%m-%d") if not valid_dates.empty else None
    add("date_range", date_status, f"min={date_min}; max={date_max}; invalid={invalid_date_rows}; out_of_range={out_of_range}; non_{annual_month_day}={non_annual}")

    distributions: dict[str, Any] = {}
    for logical in ("report_type", "statement_scope", "unit"):
        if logical in mapped:
            rows, truncated = distribution(df[mapped[logical]])
            distributions[logical] = {"rows": rows, "truncated_after_100_values": truncated}
            add(f"{logical}_distribution", "PASS", f"distinct={df[mapped[logical]].astype(str).nunique(dropna=False)}; see distribution output")
        else:
            distributions[logical] = None
            add(f"{logical}_distribution", "WARN", "logical field is not mapped; value distribution unavailable")

    years = parsed_dates.dt.year.astype("Int64")
    duplicate_frame = pd.DataFrame({"stock_code_raw": codes_raw, "year": years})
    duplicate_frame = duplicate_frame[duplicate_frame["year"].notna()]
    counts = duplicate_frame.value_counts(["stock_code_raw", "year"]).rename("duplicate_row_count").reset_index()
    duplicate_keys = counts[counts["duplicate_row_count"] > 1].copy()
    duplicate_keys.insert(0, "table_key", key)
    duplicate_rows = int(duplicate_keys["duplicate_row_count"].sum()) if not duplicate_keys.empty else 0
    add("company_year_duplicates", "PASS" if duplicate_keys.empty else "FAIL", f"duplicate_keys={len(duplicate_keys)}; rows_in_duplicate_keys={duplicate_rows}; no rows were removed")

    valid_keys = set(
        (code, int(year))
        for code, year in zip(codes_raw[valid_code_mask & years.notna()], years[valid_code_mask & years.notna()])
    )
    result.update({
        "date_audit": {
            "minimum": date_min,
            "maximum": date_max,
            "invalid_rows": invalid_date_rows,
            "out_of_expected_range_rows": out_of_range,
            "non_annual_month_day_rows": non_annual,
            "distinct_years": sorted(int(x) for x in years.dropna().unique()),
        },
        "stock_code_audit": {
            "invalid_format_rows": int((~valid_code_mask).sum()),
            "invalid_values_examples": invalid_codes[:25],
            "distinct_valid_codes": len(observed_codes),
            "unexpected_codes": unexpected_codes,
        },
        "value_distributions": distributions,
        "duplicate_company_year_keys": int(len(duplicate_keys)),
        "duplicate_company_year_rows": duplicate_rows,
        "expected_code_coverage": {
            "expected_codes": len(expected_codes),
            "covered_codes": len(expected_codes & observed_codes),
            "coverage_rate": coverage_rate,
            "missing_codes": missing_codes,
        },
    })
    return result, statuses, duplicate_keys, observed_codes, valid_keys


def write_markdown(summary: dict[str, Any], path: Path) -> None:
    lines = [
        "# CSMAR首批三表导出验收报告",
        "",
        f"生成时间（UTC）：{summary['generated_at_utc']}",
        "",
        f"总体状态：**{summary['overall_status']}**",
        "",
        "> 本报告只审计原始导出的结构、键和覆盖；未读取或输出任何财务数值，未去重，未计算论文变量。",
        "",
        "## 汇总",
        "",
        "| 表 | 行数 | 列数 | 日期范围 | 有效代码数 | 146代码覆盖 | 公司—年重复键 |",
        "|---|---:|---:|---|---:|---:|---:|",
    ]
    for table in summary["tables"]:
        date = table["date_audit"] or {}
        code = table["stock_code_audit"] or {}
        coverage = table["expected_code_coverage"] or {}
        date_range = f"{date.get('minimum')}—{date.get('maximum')}" if date else "未执行"
        covered = f"{coverage.get('covered_codes', 0)}/{coverage.get('expected_codes', 0)}" if coverage else "未执行"
        lines.append(
            f"| {table['table_label']} | {table['row_count']} | {table['column_count']} | {date_range} | {code.get('distinct_valid_codes', 0)} | {covered} | {table['duplicate_company_year_keys']} |"
        )
    lines.extend(["", "## 检查结果", "", "| 表 | 检查 | 状态 | 详情 |", "|---|---|---|---|"])
    for check in summary["checks"]:
        detail = str(check["detail"]).replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {check['table_label']} | {check['check']} | {check['status']} | {detail} |")
    lines.extend([
        "",
        "## 输出说明",
        "",
        "- `audit_summary.json`：全部结构化审计结果和报告类型/口径/单位值分布；",
        "- `audit_checks.csv`：逐项PASS/WARN/FAIL；",
        "- `duplicate_company_year_keys.csv`：重复键及行数，不含财务数值；",
        "- `missing_expected_codes.csv`：各表未覆盖的入口池代码；",
        "- `unexpected_codes.csv`：格式正确但不属于入口池的代码；",
        "- 原始文件没有被修改，重复行没有被自动删除。",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    mapping = load_mapping(Path(args.mapping))
    expected_codes_list = load_codes(Path(args.codes))
    expected_codes = set(expected_codes_list)
    expected_cfg = mapping.get("expected", {})
    expected_start = pd.Timestamp(expected_cfg.get("start_date", "2012-12-31"))
    expected_end = pd.Timestamp(expected_cfg.get("end_date", "2023-12-31"))
    annual_month_day = expected_cfg.get("annual_month_day", "12-31")
    if not re.fullmatch(r"\d{2}-\d{2}", annual_month_day):
        raise ValueError("expected.annual_month_day must use MM-DD, for example 12-31")

    sources = {
        "balance_sheet": Path(args.balance),
        "income_statement": Path(args.income),
        "cashflow_statement": Path(args.cashflow),
    }
    for path in sources.values():
        if not path.is_file():
            raise FileNotFoundError(path)

    results: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    duplicates: list[pd.DataFrame] = []
    observed_by_table: dict[str, set[str]] = {}
    keys_by_table: dict[str, set[tuple[str, int]]] = {}
    for key, source in sources.items():
        result, table_checks, duplicate_keys, observed_codes, valid_keys = audit_table(
            key=key,
            source_path=source,
            table_cfg=mapping["tables"][key],
            expected_codes=expected_codes,
            expected_start=expected_start,
            expected_end=expected_end,
            annual_month_day=annual_month_day,
            header_only=args.header_only,
        )
        results.append(result)
        checks.extend(table_checks)
        duplicates.append(duplicate_keys)
        observed_by_table[key] = observed_codes
        keys_by_table[key] = valid_keys

    failed = any(check["status"] == "FAIL" for check in checks)
    summary = {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "overall_status": "FAIL" if failed else "PASS_WITH_WARNINGS" if any(c["status"] == "WARN" for c in checks) else "PASS",
        "header_only": bool(args.header_only),
        "expected_code_count": len(expected_codes),
        "expected_date_range": [expected_start.strftime("%Y-%m-%d"), expected_end.strftime("%Y-%m-%d")],
        "tables": results,
        "checks": checks,
        "cross_table": {
            "codes_in_all_three_tables": len(set.intersection(*observed_by_table.values())) if all(observed_by_table.values()) else 0,
            "company_year_keys_in_all_three_tables": len(set.intersection(*keys_by_table.values())) if all(keys_by_table.values()) else 0,
        },
    }

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "audit_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame(checks).to_csv(output_dir / "audit_checks.csv", index=False, encoding="utf-8-sig")
    pd.concat(duplicates, ignore_index=True).to_csv(output_dir / "duplicate_company_year_keys.csv", index=False, encoding="utf-8-sig")

    missing_rows = []
    unexpected_rows = []
    for result in results:
        coverage = result.get("expected_code_coverage") or {}
        stock_audit = result.get("stock_code_audit") or {}
        missing_rows.extend({"table_key": result["table_key"], "stock_code": code} for code in coverage.get("missing_codes", []))
        unexpected_rows.extend({"table_key": result["table_key"], "stock_code": code} for code in stock_audit.get("unexpected_codes", []))
    pd.DataFrame(missing_rows, columns=["table_key", "stock_code"]).to_csv(output_dir / "missing_expected_codes.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(unexpected_rows, columns=["table_key", "stock_code"]).to_csv(output_dir / "unexpected_codes.csv", index=False, encoding="utf-8-sig")
    write_markdown(summary, output_dir / "audit_report.md")
    print(f"overall_status={summary['overall_status']}; output_dir={output_dir}")
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, ValueError, KeyError, UnicodeError, ImportError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
