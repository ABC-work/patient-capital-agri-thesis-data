#!/usr/bin/env python3
"""Extract a RESSET INSHOLDSHR ZIP without publishing the licensed raw data.

RESSET CSV downloads may omit the header.  The companion Stata HTML stores the
ordered variable codes in its ``varNames`` query parameter; this script restores
those names, keeps the selected research fields, and writes a UTF-8 audit file.
"""
import argparse
import csv
import io
import re
import zipfile
from pathlib import Path

import pandas as pd


KEEP = {
    "UpDt": "update_date",
    "nobs": "resset_row_id",
    "CompanyCode": "company_code",
    "LComNm": "company_full_name",
    "StkCd": "stock_code",
    "LStkNm": "stock_name",
    "EndDt": "end_date",
    "StatDt": "stat_date",
    "InfoSource": "info_source",
    "InsuComHold": "insurance_hold_shares_total",
    "SocSecFdHold": "social_security_hold_shares_total",
    "EntAnnuHold": "enterprise_annuity_hold_shares_total",
    "InsuComHoldPer": "insurance_hold_pct_total",
    "SocSecFdHoldPer": "social_security_hold_pct_total",
    "EntAnnuHoldPer": "enterprise_annuity_hold_pct_total",
    "AccInsuComHold": "insurance_holder_count_total",
    "AccSocSecFdHold": "social_security_holder_count_total",
    "AccEntAnnuHold": "enterprise_annuity_holder_count_total",
    "TotInsHoldper": "all_institution_hold_pct_total",
    "InsuComHoldA": "insurance_hold_shares_a",
    "SocSecFdHoldA": "social_security_hold_shares_a",
    "EntAnnuHoldA": "enterprise_annuity_hold_shares_a",
    "InsuComHoldPerA": "insurance_hold_pct_a",
    "SocSecFdHoldPerA": "social_security_hold_pct_a",
    "EntAnnuHoldPerA": "enterprise_annuity_hold_pct_a",
    "AccInsuComHoldA": "insurance_holder_count_a",
    "AccSocSecFdHoldA": "social_security_holder_count_a",
    "AccEntAnnuHoldA": "enterprise_annuity_holder_count_a",
    "TotInsHoldperA": "all_institution_hold_pct_a",
    "InsuComHoldURA": "insurance_hold_shares_unrestricted_a",
    "SocSecFdHoldURA": "social_security_hold_shares_unrestricted_a",
    "EntAnnuHoldURA": "enterprise_annuity_hold_shares_unrestricted_a",
    "InsuComHoldPerURA": "insurance_hold_pct_unrestricted_a",
    "SocSecFdHoldPerURA": "social_security_hold_pct_unrestricted_a",
    "EntAnnuHoldPerURA": "enterprise_annuity_hold_pct_unrestricted_a",
    "AccInsuComHoldURA": "insurance_holder_count_unrestricted_a",
    "AccSocSecFdHoldURA": "social_security_holder_count_unrestricted_a",
    "AccEntAnnuHoldURA": "enterprise_annuity_holder_count_unrestricted_a",
    "TotInsHoldperURA": "all_institution_hold_pct_unrestricted_a",
    # Diagnostics used to verify that percentage fields are fractions.
    "TotInsHold": "all_institution_hold_shares_total",
    "Top10Hold": "top10_hold_shares",
    "Top10HoldPer": "top10_hold_pct_total",
}


def decode(raw):
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            pass
    raise UnicodeDecodeError("unknown", raw, 0, 1, "not UTF-8 or GB18030")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_zip")
    ap.add_argument("output_csv")
    ap.add_argument(
        "--duplicate-policy",
        choices=("keep_all", "latest_stat_date"),
        default="keep_all",
        help="Default keeps every source version for auditability.",
    )
    args = ap.parse_args()

    with zipfile.ZipFile(args.input_zip) as zf:
        csv_names = [n for n in zf.namelist() if n.upper().endswith(".CSV")]
        if len(csv_names) != 1:
            raise ValueError(f"Expected exactly one CSV, found {csv_names}")
        csv_name = csv_names[0]
        html_texts = [decode(zf.read(n)) for n in zf.namelist() if n.lower().endswith(".html")]
        helper = next((x for x in html_texts if "varNames=" in x and csv_name in x), None)
        if helper is None:
            raise ValueError("No companion Stata HTML with varNames was found")
        match = re.search(r"varNames=\+(.+?)&&tableName=", helper)
        if not match:
            raise ValueError("Cannot parse ordered RESSET variable codes")
        columns = match.group(1).split("+")
        rows = [r for r in csv.reader(io.StringIO(decode(zf.read(csv_name)))) if r]

    widths = sorted({len(r) for r in rows})
    if widths != [len(columns)]:
        raise ValueError(f"CSV widths {widths} do not match {len(columns)} recovered fields")
    raw = pd.DataFrame(rows, columns=columns).replace(r"^\s*$", pd.NA, regex=True)
    absent = sorted(set(KEEP) - set(raw.columns))
    if absent:
        raise KeyError(f"Required RESSET fields absent: {absent}")
    out = raw[list(KEEP)].rename(columns=KEEP).copy()
    out["stock_code"] = out["stock_code"].astype("string").str.zfill(6)
    out["end_date"] = pd.to_datetime(out["end_date"], errors="raise")
    out["stat_date"] = pd.to_datetime(out["stat_date"], errors="raise")
    out["year"] = out["end_date"].dt.year

    key = ["stock_code", "year"]
    duplicate_rows = int(out.duplicated(key, keep=False).sum())
    if args.duplicate_policy == "latest_stat_date":
        out = out.sort_values([*key, "stat_date", "resset_row_id"]).drop_duplicates(key, keep="last")
    out = out.sort_values([*key, "stat_date", "resset_row_id"])
    Path(args.output_csv).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output_csv, index=False, encoding="utf-8-sig")
    print(f"source_rows={len(rows)}; output_rows={len(out)}; duplicate_source_rows={duplicate_rows}")
    print(f"firms={out.stock_code.nunique()}; years={out.year.min()}-{out.year.max()}")


if __name__ == "__main__":
    main()
