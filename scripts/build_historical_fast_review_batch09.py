#!/usr/bin/env python3
"""Build historical fast-review batch 09 from the fixed v17 worktable.

The batch reviews the 30 pending company-years for 新五丰、丰乐种业 and
敦煌种业. Every numerator and denominator comes from that year's official
annual report. Strict and expanded numerators use one industry dimension and
never add overlapping product, region or segment disclosures.
"""
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v17_跨年快速复核第七批.csv"
OUTPUT = ROOT / "outputs" / "跨年快速复核第九批_3家公司30条_v1.csv"

# strict numerator, expansion-only addend, total revenue, evidence page.
VERIFIED = {
    "600975": {
        2013: ("572810599.98", "141167377.49", "1130087615.49", "13"),
        2014: ("559401796.02", "171350479.09", "1302493866.31", "13"),
        2015: ("610404414.43", "130898663.58", "1326036664.34", "14"),
        2016: ("885580075.40", "93121809.74", "1691374321.68", "16"),
        2017: ("859308658.00", "78004012.05", "1723720756.85", "16"),
        2018: ("1015482383.55", "52110715.08", "2041039866.32", "16"),
        2019: ("1010503847.68", "27420860.42", "2130425322.84", "17"),
        2020: ("1327309581.14", "19020084.59", "2723731158.81", "20"),
        2021: ("869569202.59", "14780378.06", "2002862891.24", "20"),
        2022: ("2731125858.15", "2117685.00", "4932239352.73", "23"),
    },
    "000713": {
        2013: ("705473720.09", "530049248.42", "1693934876.29", "15"),
        2014: ("584528318.19", "540665510.17", "1378800048.18", "15"),
        2015: ("417646916.29", "466482271.29", "1112655608.79", "15"),
        2016: ("308780049.49", "657655523.68", "1217693090.22", "18"),
        2017: ("272108530.82", "876878478.98", "1446714027.92", "18"),
        2018: ("280913013.17", "1229088836.27", "1927145479.56", "19"),
        2019: ("405703041.56", "1533113077.11", "2403955879.24", "23"),
        2020: ("383979770.49", "1752747804.48", "2456598310.13", "22"),
        2021: ("445214621.90", "1863807925.46", "2617242367.84", "22"),
        2022: ("658797974.54", "2066060417.92", "3005259332.24", "21"),
    },
    "600354": {
        2013: ("1082784780.02", "0.00", "1874811756.60", "10"),
        2014: ("852627126.91", "0.00", "1255860454.79", "11"),
        2015: ("873453457.30", "0.00", "1304026666.04", "10"),
        2016: ("422224211.85", "0.00", "655137590.83", "11"),
        2017: ("253342332.80", "0.00", "485178519.19", "11"),
        2018: ("338570901.99", "0.00", "767469079.12", "11"),
        2019: ("338316962.70", "0.00", "1183712575.19", "11"),
        2020: ("389762957.24", "0.00", "954210631.49", "10"),
        2021: ("605636998.38", "0.00", "922131315.29", "10"),
        2022: ("738441249.75", "0.00", "1004680753.38", "10"),
    },
}


def ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    return (numerator / denominator).quantize(
        Decimal("0.00000001"), rounding=ROUND_HALF_UP
    )


def labels(code: str) -> tuple[str, str, str]:
    if code == "600975":
        return "畜牧业（生猪）", "畜牧业（生猪）、饲料加工", "同一分行业维度"
    if code == "000713":
        return "种子类", "种子类、农化类", "同一分行业维度"
    return "种子", "种子", "同一分行业维度"


def explanation(
    code: str,
    strict_share: Decimal,
    expanded_share: Decimal,
    strict: str,
    expanded: str,
    boundary: str,
) -> str:
    sp, ep = strict_share * 100, expanded_share * 100
    if code == "600975":
        if strict == "是":
            return (
                f"畜牧业收入占{sp:.2f}%，达到50%严格门槛；同一行业维度加入饲料加工后"
                f"占{ep:.2f}%。批发零售未计入。"
            )
        if expanded == "是":
            return (
                f"畜牧业收入占{sp:.2f}%，未达严格门槛；同一行业维度加入农业投入品饲料加工后"
                f"占{ep:.2f}%，达到扩展样本门槛。批发零售未计入。"
            )
        return (
            f"畜牧业收入占{sp:.2f}%；同一行业维度加入饲料加工后占{ep:.2f}%，处于30%—50%，"
            "列为边界样本。批发零售未计入。"
        )
    if code == "000713":
        return (
            f"种子收入占{sp:.2f}%，未达严格门槛；同一行业维度加入农业投入品农化业务后"
            f"占{ep:.2f}%，达到扩展样本门槛。香料业务未计入。"
        )
    if strict == "是":
        return (
            f"种子收入占{sp:.2f}%，达到50%严格门槛；食品与贸易、棉花、果蔬及其他业务均未"
            "用于放大分子。"
        )
    if boundary == "是":
        return (
            f"种子收入占{sp:.2f}%，处于30%—50%，列为边界样本；食品与贸易、棉花、果蔬及"
            "其他业务均未计入。"
        )
    return (
        f"种子收入占{sp:.2f}%，低于30%，不纳入严格、扩展或边界样本；食品与贸易、棉花、"
        "果蔬及其他业务均未计入。"
    )


def main() -> None:
    source = pd.read_csv(SOURCE, dtype={"股票代码": str})
    keys = {(code, year) for code, years in VERIFIED.items() for year in years}
    assert len(keys) == 30
    assert not ({"002696", "300094", "601118"} & {code for code, _ in keys})
    selected = source[
        source.apply(lambda row: (row["股票代码"], int(row["年份"])) in keys, axis=1)
    ].copy()
    assert len(selected) == 30
    assert not selected.duplicated(["股票代码", "年份"]).any()
    assert not selected["复核状态"].str.startswith("已人工复核", na=False).any()

    rows = []
    for _, source_row in selected.sort_values(["股票代码", "年份"]).iterrows():
        code, year = source_row["股票代码"], int(source_row["年份"])
        strict_raw, add_raw, total_raw, page = VERIFIED[code][year]
        strict_n, add_n, total = map(Decimal, (strict_raw, add_raw, total_raw))
        expanded_n = strict_n + add_n
        strict_fraction, expanded_fraction = strict_n / total, expanded_n / total
        strict_share, expanded_share = ratio(strict_n, total), ratio(expanded_n, total)
        strict = "是" if strict_fraction >= Decimal("0.50") else "否"
        expanded = "是" if expanded_fraction >= Decimal("0.50") else "否"
        boundary = "是" if Decimal("0.30") <= expanded_fraction < Decimal("0.50") else "否"
        strict_name, expanded_name, dimension = labels(code)
        stored_n = strict_n if strict == "是" else expanded_n
        stored_name = strict_name if strict == "是" else expanded_name
        stored_share = ratio(stored_n, total)

        rows.append({
            "股票代码": code,
            "公司全称": source_row["公司全称"],
            "年份": year,
            "行业分类代码": source_row["行业分类代码"] if pd.notna(source_row["行业分类代码"]) else "待核实",
            "行业分类名称": source_row["行业分类名称"] if pd.notna(source_row["行业分类名称"]) else "待核实",
            "涉农业务_保守不重叠口径": stored_name,
            "工作表采用涉农业务营业收入_元": f"{stored_n:.2f}",
            "严格口径营业收入_元": f"{strict_n:.2f}",
            "扩展口径营业收入_元": f"{expanded_n:.2f}",
            "公司营业收入_元": f"{total:.2f}",
            "工作表采用涉农收入占比": f"{stored_share:.8f}",
            "严格口径收入占比": f"{strict_share:.8f}",
            "扩展口径收入占比": f"{expanded_share:.8f}",
            "严格样本结论": strict,
            "扩展样本结论": expanded,
            "边界样本结论": boundary,
            "是否存在分部收入重叠": f"否（仅使用{dimension}）",
            "复核说明": explanation(code, strict_share, expanded_share, strict, expanded, boundary),
            "年报主营业务证据PDF页序号": page,
            "公司营业收入证据PDF页序号": source_row["利润表PDF页序号"],
            "年报链接": source_row["年报链接"],
            "记录类型": "本次新增跨年快速复核",
            "复核日期": "2026-08-11",
        })

    output = pd.DataFrame(rows)
    assert len(output) == 30
    assert not output.duplicated(["股票代码", "年份"]).any()
    assert output["股票代码"].value_counts().to_dict() == {
        "600975": 10, "000713": 10, "600354": 10
    }
    assert output["严格样本结论"].value_counts().to_dict() == {"否": 20, "是": 10}
    assert output["扩展样本结论"].value_counts().to_dict() == {"是": 24, "否": 6}
    assert output["边界样本结论"].value_counts().to_dict() == {"否": 25, "是": 5}
    output.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("batch09 rows=30; strict yes=10; expanded yes=24; boundary=5")


if __name__ == "__main__":
    main()
