#!/usr/bin/env python3
"""Build batch 08 from v17 without merging it into a new master worktable.

Targets: 百洋股份、国联水产、海南橡胶, all 30 pending years.  The
script deliberately leaves mixed initial/deep processing or self-produced/
third-party trading disclosures unresolved instead of treating the combined
amount as eligible agricultural revenue.
"""
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v17_跨年快速复核第七批.csv"
OUTPUT = ROOT / "outputs" / "跨年快速复核第八批_3家公司30条_v1.csv"

# For conclusive Baiyang rows: strict numerator, expanded numerator, total,
# evidence PDF page, strict-revenue upper bound (only when exact direct revenue
# is unavailable). Expanded numerator uses a single annual-report product
# or industry dimension and excludes education/other activities.
BAIYANG = {
    2013: ("18740392.40", "1308202107.16", "1349625914.90", "13", ""),
    2014: ("40413420.54", "1686182463.23", "1780815051.84", "15", ""),
    2015: ("41594547.63", "1683975612.71", "1863739460.06", "14", ""),
    2016: ("59307038.63", "2033352195.47", "2068525079.14", "14", ""),
    2017: ("138116457.72", "2121824980.66", "2394128757.97", "18", ""),
    2018: ("110645847.59", "2514742187.00", "3133583902.86", "17", ""),
    # The whole far-ocean segment is only an upper bound for direct fishing;
    # at 13.18% it cannot change the strict-sample conclusion.
    2019: ("", "2441053514.99", "2844133734.97", "17", "374899493.27"),
    2020: ("", "2476497256.51", "2482574247.63", "16", "1059554822.51"),
    2021: ("89035629.50", "2889684160.40", "2905284846.26", "18", ""),
    2022: ("129035825.79", "3198423836.66", "3213988743.45", "16", ""),
}

# Guolian's disclosed direct production is below 50%, but its water-product
# aggregate cannot be split reliably into initial processing, deep processing
# and trading.  Hence expanded/boundary remain pending, matching the verified
# 2023 treatment.
GUOLIAN = {
    2013: ("50729909.78", "2200249935.96", "2213827410.03", "22"),
    2014: ("58309070.00", "2125946854.50", "2129362231.99", "2014年报131；2015年报14（同期产品数）"),
    2015: ("52716502.16", "2068941559.87", "2070469926.65", "14"),
    2016: ("64639580.88", "2604200300.22", "2621366941.32", "15"),
    2017: ("52428135.60", "4090238762.13", "4095806660.34", "17"),
    2018: ("31898726.00", "4723620273.89", "4737778725.97", "18"),
    2019: ("57213889.16", "4623444874.37", "4637165159.34", "25"),
    2020: ("", "4414481552.97", "4494106122.88", "14"),
    2021: ("", "4369408776.17", "4474169975.45", "19"),
    2022: ("", "5029115830.89", "5114218375.88", "15"),
}

# Hainan Rubber reports an agriculture/natural-rubber aggregate dominated in
# part by third-party trading; it does not disclose revenue for self-produced
# rubber separately.  The combined amount is retained solely for audit.
HAINAN_RUBBER = {
    2013: ("11437906232.88", "11694732913.16", "13"),
    2014: ("10818419306.53", "11198671739.10", "11"),
    2015: ("7920927409.40", "8400121545.48", "9"),
    2016: ("8144831743.78", "8876506775.80", "12"),
    2017: ("10271653925.31", "10818322651.34", "13"),
    2018: ("6519261296.34", "6754522891.75", "14"),
    2019: ("13443468791.91", "13747601241.97", "18"),
    2020: ("15190587885.67", "15532109816.38", "14"),
    2021: ("14682866114.20", "15207422670.09", "14"),
    2022: ("14791688496.94", "15371271093.62", "15"),
}


def ratio(numerator: str, denominator: str) -> str:
    if not numerator:
        return ""
    value = (Decimal(numerator) / Decimal(denominator)).quantize(
        Decimal("0.00000001"), rounding=ROUND_HALF_UP
    )
    return f"{value:.8f}"


def main() -> None:
    source = pd.read_csv(SOURCE, dtype={"股票代码": str}, keep_default_na=False)
    targets = {"002696", "300094", "601118"}
    selected = source[
        source["股票代码"].isin(targets)
        & ~source["复核状态"].str.startswith("已人工复核", na=False)
    ].sort_values(["股票代码", "年份"])
    assert len(selected) == 30
    assert selected.groupby("股票代码").size().to_dict() == {
        "002696": 10, "300094": 10, "601118": 10
    }
    assert set(selected["年份"]) == set(range(2013, 2023))
    assert not selected.duplicated(["股票代码", "年份"]).any()

    rows = []
    for _, src in selected.iterrows():
        code, year = src["股票代码"], int(src["年份"])
        if code == "002696":
            strict_n, expanded_n, total, page, strict_upper = BAIYANG[year]
            strict_share, expanded_share = ratio(strict_n, total), ratio(expanded_n, total)
            assert Decimal(expanded_share) >= Decimal("0.50")
            strict_upper_share = ratio(strict_upper, total)
            if strict_n:
                assert Decimal(strict_share) < Decimal("0.50")
                strict_evidence = f"可识别直接养殖/捕捞收入占{Decimal(strict_share) * 100:.2f}%"
                business = "饲料及饲料原料、水产品加工、可识别养殖/捕捞（扩展口径）"
            else:
                assert strict_upper and Decimal(strict_upper_share) < Decimal("0.50")
                strict_evidence = (
                    f"直接养殖/捕捞收入未单列；按最宽范围计算的严格收入上界为"
                    f"{Decimal(strict_upper):,.2f}元、占{Decimal(strict_upper_share) * 100:.2f}%"
                )
                business = "饲料及水产品加工（扩展口径）；直接养殖/捕捞仅可确定收入上界"
            reason = (
                f"同一披露维度内的农业投入品、水产品加工及可识别直接渔业收入占{Decimal(expanded_share) * 100:.2f}%，"
                f"超过50%；教育及其他业务未计入。{strict_evidence}，严格样本为否。"
            )
            stored, stored_share = expanded_n, expanded_share
            strict, expanded, boundary = "否", "是", "否"
            mixed = "否（仅使用同一分行业或分产品维度）"
            combined = ""
        elif code == "300094":
            strict_n, combined, total, page = GUOLIAN[year]
            strict_share = ratio(strict_n, total)
            business = "可确认的种苗/养殖；水产加工与贸易、深加工未可靠拆分"
            reason = (
                "年报披露的直接种苗/养殖收入不足50%；水产品或加工销售合并口径包含初加工、"
                "精深加工及/或贸易，无法可靠得到符合扩展定义的收入分子，扩展和边界均待核实。"
            )
            stored = stored_share = expanded_n = expanded_share = ""
            strict, expanded, boundary = "否", "待核实", "待核实"
            mixed = "是（合并披露含初加工、深加工及/或贸易，不能直接采用）"
        else:
            combined, total, page = HAINAN_RUBBER[year]
            business = "自产天然橡胶收入未单列"
            reason = (
                f"年报农业/天然橡胶合并披露收入为{Decimal(combined):,.2f}元，但同时包含自产种植初加工和"
                "大规模第三方橡胶贸易；自产收入未单列，不能将合并金额作为涉农分子，严格、扩展及边界均待核实。"
            )
            strict_n = strict_share = expanded_n = expanded_share = stored = stored_share = ""
            strict = expanded = boundary = "待核实"
            mixed = "是（自产种植初加工与第三方贸易收入不可拆分）"

        rows.append({
            "股票代码": code,
            "公司全称": src["公司全称"],
            "年份": year,
            "行业分类代码": src["行业分类代码"],
            "行业分类名称": src["行业分类名称"],
            "涉农业务_保守不重叠口径": business,
            "工作表采用涉农业务营业收入_元": stored,
            "严格口径营业收入_元": strict_n,
            "严格口径收入上界_元": strict_upper if code == "002696" else "",
            "扩展口径营业收入_元": expanded_n,
            "不可直接采用的合并披露收入_元": combined,
            "公司营业收入_元": total,
            "工作表采用涉农收入占比": stored_share,
            "严格口径收入占比": strict_share,
            "严格口径收入上界占比": strict_upper_share if code == "002696" else "",
            "扩展口径收入占比": expanded_share,
            "严格样本结论": strict,
            "扩展样本结论": expanded,
            "边界样本结论": boundary,
            "是否存在分部收入重叠": mixed,
            "复核说明": reason,
            "年报主营业务证据PDF页序号": page,
            "公司营业收入证据PDF页序号": src["利润表PDF页序号"],
            "年报链接": src["年报链接"],
            "记录类型": "本次新增跨年快速复核（未合并）",
            "复核日期": "2026-08-11",
        })

    output = pd.DataFrame(rows)
    assert len(output) == 30
    assert not output.duplicated(["股票代码", "年份"]).any()
    assert output["严格样本结论"].value_counts().to_dict() == {"否": 20, "待核实": 10}
    assert output["扩展样本结论"].value_counts().to_dict() == {"是": 10, "待核实": 20}
    assert output["边界样本结论"].value_counts().to_dict() == {"待核实": 20, "否": 10}
    assert output.loc[output["扩展样本结论"].eq("是"), "扩展口径收入占比"].ne("").all()
    assert output.loc[output["扩展样本结论"].eq("待核实"), "工作表采用涉农业务营业收入_元"].eq("").all()
    output.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("batch08 rows=30; strict no=20/pending=10; expanded yes=10/pending=20; not merged")


if __name__ == "__main__":
    main()
