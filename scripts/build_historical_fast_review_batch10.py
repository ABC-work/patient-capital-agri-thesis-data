#!/usr/bin/env python3
"""Build independent historical fast-review batch 10 from v17.

Targets all pending years for 华英农业、福成股份、景谷林业 (29 rows).
This script only writes the batch evidence CSV; it does not merge or create a
new master worktable.
"""
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v17_跨年快速复核第七批.csv"
OUTPUT = ROOT / "outputs" / "跨年快速复核第十批_3家公司29条_v1.csv"

# strict numerator, expanded numerator, total revenue, evidence PDF page.
# Huaying follows its verified 2023 rule: direct poultry = duck/chick/egg and
# live poultry; expanded adds frozen poultry, feed, raw feather and down. Cooked
# food and finished down products are excluded.
HUAYING = {
    2013: ("154549908.04", "1573059951.64", "1756369219.80", "15"),
    2014: ("212456773.06", "1658479355.15", "1843102830.81", "17"),
    2015: ("289428210.07", "1653080641.49", "1857499503.11", "16"),
    2016: ("258188473.41", "2214507296.97", "2514708469.80", "16"),
    2017: ("265286221.36", "3501102798.25", "4121925898.01", "17"),
    2018: ("501868086.76", "4462888025.93", "5348828565.38", "16"),
    2019: ("716313268.16", "4698234467.18", "5517686134.68", "16"),
    2020: ("87989625.61", "2552344669.38", "3125556245.34", "21"),
    2021: ("7967178.91", "2643337409.78", "3192457799.66", "27"),
    2022: ("575434.40", "2344679271.90", "2898364526.87", "22"),
}

# Fucheng strict numerator is live cattle/calves and separately disclosed raw
# milk. Expanded adds beef and lamb. Dairy products are reported separately as
# a possible increment, but even the upper bound stays below 30% in 2013-2022.
FUCHENG = {
    2013: ("60783039.34", "271071006.56", "7046681.65", "1026673081.47", "13"),
    2014: ("71302900.09", "295253874.04", "3224634.36", "1100242977.76", "13"),
    2015: ("68226814.50", "316414140.11", "10383344.81", "1343812355.13", "10"),
    2016: ("43953568.89", "298533182.25", "14350351.99", "1370995900.08", "13"),
    2017: ("3028843.43", "279797322.30", "16999955.96", "1360558933.25", "12"),
    2018: ("9710281.06", "289617557.44", "24478693.44", "1453720417.48", "12"),
    2019: ("9673574.31", "287329672.69", "23313975.15", "1446840589.75", "13"),
    2020: ("0", "227191916.47", "20448542.84", "1086334896.36", "14"),
    2021: ("0", "242651671.00", "14778854.87", "1268506611.25", "19"),
    2022: ("90738540.00", "294841234.22", "23177397.00", "1073890737.22", "19"),
}

# Jinggu direct forestry is separately disclosed forest/tree sales. Expanded
# adds forest-board/wood and eligible forest-chemical primary processing. The
# 2018 forest-chemical item is explicitly trading and is therefore excluded.
JINGGU = {
    2013: ("163095400.00", "243041540.21", "250238489.62", "23"),
    2014: ("0", "92824141.50", "95927290.65", "11"),
    2015: ("0", "82894713.72", "87847153.84", "11"),
    2016: ("0", "64965591.94", "70718280.47", "13"),
    2017: ("0", "63042437.46", "65973576.91", "14"),
    2018: ("40558600.00", "82879261.42", "118866706.52", "10、63"),
    # 2019 annual-report transaction price is not revenue. The later official
    # annual-report inquiry reply discloses total forest sales of RMB29.0433m.
    # It is converted from ten-thousand yuan and must retain a precision note.
    2019: ("29043300.00", "72625814.64", "203245285.52", "16-17；问询函9"),
    2020: ("0", "33498212.64", "50678245.07", "15"),
    2021: ("0", "129420890.75", "137029110.46", "18"),
}


def share(numerator: str, denominator: str) -> Decimal:
    return (Decimal(numerator) / Decimal(denominator)).quantize(
        Decimal("0.00000001"), rounding=ROUND_HALF_UP
    )


def main() -> None:
    source = pd.read_csv(SOURCE, dtype={"股票代码": str}, keep_default_na=False)
    targets = {"002321", "600965", "600265"}
    selected = source[
        source["股票代码"].isin(targets)
        & ~source["复核状态"].str.startswith("已人工复核", na=False)
    ].sort_values(["股票代码", "年份"])
    assert len(selected) == 29
    assert selected.groupby("股票代码").size().to_dict() == {
        "002321": 10, "600265": 9, "600965": 10
    }
    assert not selected.duplicated(["股票代码", "年份"]).any()

    rows = []
    for _, src in selected.iterrows():
        code, year = src["股票代码"], int(src["年份"])
        extra_audit = ""
        precision_note = ""
        supplementary_url = ""
        if code == "002321":
            strict_n, expanded_n, total, page = HUAYING[year]
            business = "禽苗、种蛋及活禽；冻禽、鸭毛、饲料、羽绒初加工（扩展口径）"
            reason_base = (
                "原毛经洗涤、干燥、分级形成的羽绒材料计入初加工；熟食、成品羽绒制品、"
                "租赁及其他业务未计入；仅在同一分产品维度加总。"
            )
        elif code == "600965":
            strict_n, expanded_n, dairy, total, page = FUCHENG[year]
            business = "活牛/小牛、原奶；牛肉和羊肉初加工（扩展口径）"
            upper = share(str(Decimal(expanded_n) + Decimal(dairy)), total)
            assert upper < Decimal("0.30")
            extra_audit = dairy
            reason_base = (
                f"乳制品{Decimal(dairy):,.2f}元因初加工部分未拆分而不计入；即使全部计入，占比上限也仅"
                f"{upper * 100:.2f}%。肉制品、速食品、餐饮及殡葬业务未计入。"
            )
        else:
            strict_n, expanded_n, total, page = JINGGU[year]
            if year == 2018:
                business = "林木销售及林板/木材初加工（林化产品贸易排除）"
                reason_base = (
                    "林木销售计入直接林业，林板/木材计入扩展口径；年报明确列为贸易的林化产品已排除。"
                    "能源、租赁、林地使用权及固定资产处置不计入。"
                )
            else:
                business = "林木销售；林板、木材及林化初加工（扩展口径）"
                reason_base = (
                    "林木销售计入直接林业；林板/木材和松香、松节油等林化初加工计入扩展口径；"
                    "能源、租赁、林地使用权及固定资产处置不计入。"
                )
            if year == 2019:
                precision_note = (
                    "全年林木销售收入由公司2020年年报问询函按万元披露为2,904.33万元；"
                    "换算为元用于比例，来源精度为万元，并非精确到元。"
                )
                supplementary_url = "https://static.cninfo.com.cn/finalpage/2021-05-18/1209994251.PDF"

        strict_fraction = Decimal(strict_n) / Decimal(total)
        expanded_fraction = Decimal(expanded_n) / Decimal(total)
        strict_share = share(strict_n, total)
        expanded_share = share(expanded_n, total)
        strict = "是" if strict_fraction >= Decimal("0.50") else "否"
        expanded = "是" if expanded_fraction >= Decimal("0.50") else "否"
        boundary = "是" if Decimal("0.30") <= expanded_fraction < Decimal("0.50") else "否"
        stored = strict_n if strict == "是" else expanded_n
        stored_share = strict_share if strict == "是" else expanded_share

        if strict == "是":
            conclusion = f"直接农业/林业收入占{strict_share * 100:.2f}%，达到50%，纳入严格样本。"
        elif expanded == "是":
            conclusion = (
                f"严格口径占{strict_share * 100:.2f}%，未达50%；同一维度加入初加工和农业投入品后占"
                f"{expanded_share * 100:.2f}%，纳入扩展样本。"
            )
        elif boundary == "是":
            conclusion = (
                f"严格口径占{strict_share * 100:.2f}%；扩展口径占{expanded_share * 100:.2f}%，"
                "处于30%—50%，列为边界样本。"
            )
        else:
            conclusion = (
                f"严格口径占{strict_share * 100:.2f}%，扩展口径占{expanded_share * 100:.2f}%，"
                "均未达到相应门槛。"
            )

        rows.append({
            "股票代码": code,
            "公司全称": src["公司全称"],
            "年份": year,
            "行业分类代码": src["行业分类代码"] if src["行业分类代码"] else "待核实",
            "行业分类名称": src["行业分类名称"] if src["行业分类名称"] else "待核实",
            "涉农业务_保守不重叠口径": business,
            "工作表采用涉农业务营业收入_元": stored,
            "严格口径营业收入_元": strict_n,
            "扩展口径营业收入_元": expanded_n,
            "未计入但用于上限检验的乳制品收入_元": extra_audit,
            "金额精度或补充证据说明": precision_note,
            "补充官方证据链接": supplementary_url,
            "公司营业收入_元": total,
            "工作表采用涉农收入占比": f"{stored_share:.8f}",
            "严格口径收入占比": f"{strict_share:.8f}",
            "扩展口径收入占比": f"{expanded_share:.8f}",
            "严格样本结论": strict,
            "扩展样本结论": expanded,
            "边界样本结论": boundary,
            "是否存在分部收入重叠": "否（仅使用同一分产品或明确交易收入；不跨维度相加）",
            "复核说明": conclusion + reason_base,
            "年报主营业务证据PDF页序号": page,
            "公司营业收入证据PDF页序号": src["利润表PDF页序号"],
            "年报链接": src["年报链接"],
            "记录类型": "本次新增跨年快速复核（未合并）",
            "复核日期": "2026-08-11",
        })

    output = pd.DataFrame(rows)
    assert len(output) == 29
    assert not output.duplicated(["股票代码", "年份"]).any()
    assert output["严格样本结论"].value_counts().to_dict() == {"否": 28, "是": 1}
    assert output["扩展样本结论"].value_counts().to_dict() == {"是": 18, "否": 11}
    assert output["边界样本结论"].value_counts().to_dict() == {"否": 28, "是": 1}
    output.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("batch10 rows=29; strict yes=1; expanded yes=18; boundary=1; not merged")


if __name__ == "__main__":
    main()
