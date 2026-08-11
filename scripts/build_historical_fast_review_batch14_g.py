#!/usr/bin/env python3
"""Build independent historical fast-review batch 14 G from fixed v23.

The script only reads v23 and writes a standalone evidence CSV.  It does not
modify or merge the master worktable.
"""
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import re

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v23_跨年快速复核第十三批.csv"
OUTPUT = ROOT / "outputs" / "跨年快速复核第十四批_G组_3家公司.csv"


# total, agricultural-products upper bound, feed, animal-health, feed-cost guard, pages
# “农产品”包括种苗、生猪、禽产业链和水产养殖；禽产业链可能夹含屠宰或
# 食品加工，不能整项写入严格口径。扩展下界仅使用明确的饲料和动保。
HAID = {
    2014: ("21090411325.24", "234725137.17", "19435041917.47", "134226677.65", "17543553413.49", "17"),
    2015: ("25567402483.20", "335343627.25", "20170113480.71", "175928869.90", "17923939507.69", "19|20|21"),
    2018: ("42156628800.11", "1741602049.75", "34965196221.20", "473324165.98", "31106349787.96", "25|26"),
    2019: ("47612587464.50", "2741203586.44", "38985186067.96", "574064192.41", "34759643284.59", "22|23|24"),
    2020: ("60323862405.94", "6368085797.46", "48765213907.42", "664662163.91", "43734476976.26", "24|25"),
    2021: ("85998559748.78", "8629261147.71", "69825872761.95", "892463422.53", "63485844564.16", "24|25"),
    2022: ("104715417485.92", "12455629441.65", "84892419774.07", "1044659775.65", "78060758981.95", "25"),
}


# total, strict lower/upper, expanded lower, other-product remainder upper,
# feed-cost guard, strict formula, expanded formula, pages.
DBN = {
    2014: ("18444915959.83", "0", "105186669.43", "18160561439.92", "105186669.43", "13754576201.42",
           "下界0；上界=未拆分其他产品105,186,669.43", "饲料17,188,165,669.59+种业477,700,306.64+植保115,626,277.87+动保379,069,185.82", "18"),
    2015: ("16098085185.45", "280820200.00", "280820200.00", "15944136725.76", "153948459.69", "11335374621.00",
           "生猪收入28,082.02万元×10,000", "饲料14,544,272,271.98+种业675,640,247.42+植保106,426,478.88+动保336,977,527.48+生猪280,820,200.00", "18|19|20"),
    2018: ("19302066717.55", "1326642013.16", "1326642013.16", "18807397702.53", "494669015.02", "13426867579.07",
           "养殖产品1,326,642,013.16", "饲料16,669,564,252.07+养殖1,326,642,013.16+种业391,450,581.09+植保141,165,547.94+动保278,575,308.27", "21|22"),
    2019: ("16577901766.95", "1946870552.43", "1946870552.43", "15769199151.45", "808702615.50", "10537540704.50",
           "养殖产品1,946,870,552.43", "饲料13,040,242,947.18+养殖1,946,870,552.43+种业403,122,787.02+植保160,496,326.65+疫苗105,855,283.59+兽药112,611,254.58", "22|23"),
    2020: ("22813861332.61", "3801389615.30", "3801389615.30", "21287673906.09", "158940488.76", "13972763411.53",
           "养猪产品3,801,389,615.30", "饲料16,586,626,988.53+养猪3,801,389,615.30+种业407,750,744.08+植保165,439,803.45+疫苗155,563,601.68+兽药170,903,153.05", "23|24"),
    2021: ("31328078121.44", "4698825465.49", "4698825465.49", "28487254694.88", "151795580.87", "19701979391.85",
           "养猪产品4,698,825,465.49", "饲料22,694,759,023.57+养猪4,698,825,465.49+种业560,624,798.88+植保180,913,268.66+疫苗132,031,888.53+兽药220,100,249.75", "21|22|23"),
    2022: ("32396746022.43", "5466675036.26", "5466675036.26", "29182077314.27", "135840966.91", "19722434633.68",
           "养猪产品5,466,675,036.26", "饲料22,289,989,903.12+养猪5,466,675,036.26+种业944,296,539.35+植保192,481,323.29+疫苗123,017,853.82+兽药165,616,658.43", "17|18"),
}


# total, exact expanded revenue, exact eligible-product cost, revenue formula,
# cost formula, pages.  Trade is a separately disclosed mutually exclusive product.
ZHONGMU = {
    2014: ("4035441262.62", "2277338392.81", "1395811157.44", "生物制品1,184,809,694.59+化药460,488,796.89+饲料632,039,901.33", "516,686,398.43+382,257,129.88+496,867,629.13", "14|15"),
    2015: ("4234189943.05", "2456203878.77", "1445992230.95", "生物制品1,247,947,421.80+化药552,141,944.92+饲料656,114,512.05", "514,979,753.51+422,698,788.11+508,313,689.33", "14"),
    2018: ("4434238007.41", "3280767062.18", "2021013587.53", "生物制品1,257,114,943.58+兽药903,678,109.63+饲料1,119,974,008.97", "542,372,088.53+608,673,130.14+869,968,368.86", "12"),
    2019: ("4117720021.78", "2896991893.67", "1826265644.56", "生物制品1,139,587,558.42+兽药811,089,632.12+饲料946,314,703.13", "535,956,656.86+562,833,751.45+727,475,236.25", "14"),
    2020: ("4998683678.48", "3562916342.97", "2330162402.31", "生物制品1,432,583,013.59+化药1,013,592,388.02+饲料1,116,740,941.36", "678,105,052.87+742,093,412.22+909,963,937.22", "13"),
    2021: ("5301571718.27", "3787812595.53", "2358992409.65", "生物制品1,428,974,398.94+化药1,257,014,527.93+饲料1,101,823,668.66", "598,243,510.80+867,069,596.43+893,679,302.42", "13|14"),
    2022: ("5891524963.89", "3752083185.96", "2576397101.07", "生物制品1,212,627,584.85+化药1,437,254,349.40+饲料1,102,201,251.71", "617,318,090.42+1,061,417,149.63+897,661,861.02", "11|12"),
}


def raw(n: Decimal, d: Decimal) -> str:
    return format(n / d, "f")


def r8(n: Decimal, d: Decimal) -> str:
    return f"{(n / d).quantize(Decimal('0.00000001'), rounding=ROUND_HALF_UP):.8f}"


def threshold(lower: Decimal, upper: Decimal, total: Decimal) -> str:
    if lower / total >= Decimal("0.50"):
        return "是"
    if upper / total < Decimal("0.50"):
        return "否"
    return "待核实"


def boundary(lower: Decimal, upper: Decimal, total: Decimal) -> str:
    lo, hi = lower / total, upper / total
    if lo >= Decimal("0.50") or hi < Decimal("0.30"):
        return "否"
    if lo >= Decimal("0.30") and hi < Decimal("0.50"):
        return "是"
    return "待核实"


def sum_formula_amounts(formula: str) -> Decimal:
    return sum(
        (Decimal(x.replace(",", "")) for x in re.findall(r"\d[\d,]*\.\d{2}", formula)),
        Decimal("0"),
    )


def main() -> None:
    src = pd.read_csv(SOURCE, dtype={"股票代码": str}, keep_default_na=False)
    sel = src[
        src["股票代码"].isin(["002311", "002385", "600195"])
        & ~src["复核状态"].str.startswith("已人工复核", na=False)
    ].sort_values(["股票代码", "年份"])
    assert len(sel) == 21
    assert sel.groupby("股票代码").size().to_dict() == {"002311": 7, "002385": 7, "600195": 7}
    assert set(sel["年份"].astype(int)) == {2014, 2015, 2018, 2019, 2020, 2021, 2022}
    assert not sel.duplicated(["股票代码", "年份"]).any()

    rows = []
    for _, s in sel.iterrows():
        code, year = s["股票代码"], int(s["年份"])
        precision_note = ""
        if code == "002311":
            total = Decimal(HAID[year][0]); ag_upper = Decimal(HAID[year][1]); feed = Decimal(HAID[year][2]); health = Decimal(HAID[year][3]); cost_guard = Decimal(HAID[year][4]); pages = HAID[year][5]
            sl, su = Decimal("0"), ag_upper
            el, eu = feed + health, feed + health + ag_upper
            strict_formula = "下界0；上界=年报农产品收入（含种苗、生猪、禽产业链、水产养殖，未拆屠宰/加工）"
            expanded_formula = f"下界=饲料{feed:,.2f}+动保{health:,.2f}；上界再加农产品{ag_upper:,.2f}"
            business = "直接养殖/种苗（严格上界）；饲料、动保（扩展下界）"
            overlap = "否（同一分产品维度；农产品只进入上界，贸易、其他和饲料机械排除）"
            cost_formula = (
                f"仅为饲料产品营业成本哨兵{cost_guard:,.2f}；"
                "不代表全部纳入产品成本"
            )
            note = "农产品项未拆直接养殖、种苗与禽产业链中的潜在屠宰/加工，故只作上界；扩展下界已超过50%。"
            assert el == feed + health and eu == el + ag_upper
            if year == 2021:
                precision_note = (
                    "采用2021年当年报告：营业收入85,998,559,748.78元、"
                    "农产品/养殖项8,629,261,147.71元；2022年比较栏分别重列为"
                    "86,091,961,539.13元和8,722,662,938.06元，不以后续比较数覆盖。"
                )
        elif code == "002385":
            vals = DBN[year]
            total, sl, su, el, other, cost_guard = map(Decimal, vals[:6]); eu = el + other
            strict_formula, expanded_base, pages = vals[6:9]
            assert sum_formula_amounts(expanded_base) == el
            if year == 2015:
                assert other == Decimal("434768659.69") - sl
            expanded_formula = expanded_base + (f"；上界再加未拆其他产品{other:,.2f}" if other else "")
            business = "生猪养殖（严格）；饲料、种子、植保、动保及生猪（扩展）"
            overlap = "否（同一分产品维度；2015生猪为其他产品的已披露子项，其余其他产品只进上界；原料贸易排除）"
            cost_formula = (
                f"仅为饲料产品营业成本哨兵{cost_guard:,.2f}；"
                "不代表全部纳入产品成本"
            )
            note = "饲料、种业、植保、疫苗/兽药属于农业投入品；原料贸易排除，其他产品不自动纳入。"
            if year == 2015:
                precision_note = "生猪收入按年报披露28,082.02万元换算为280,820,200.00元，来源精度为万元小数点后两位。"
        else:
            vals = ZHONGMU[year]
            total, el, cost_guard = map(Decimal, vals[:3]); sl = su = Decimal("0"); eu = el
            expanded_formula, cost_formula, pages = vals[3:]
            strict_formula = "0（未披露直接种植或养殖收入）"
            business = "生物制品、兽药/化药、饲料等农业投入品（扩展）"
            overlap = "否（同一分产品维度加总；单列贸易收入全部排除）"
            note = "生物制品、兽药/化药和饲料属于农业投入品；贸易为互斥单列产品，不计入。"
            assert sum_formula_amounts(expanded_formula) == el
            assert sum_formula_amounts(cost_formula) == cost_guard
            if year == 2019:
                precision_note = "采用2019年当年报告营业收入4,117,720,021.78元；2020年比较栏为4,135,737,308.30元，不以后续比较数覆盖。"

        assert Decimal("0") <= sl <= su <= total
        assert Decimal("0") <= el <= eu <= total
        assert sl <= el and su <= eu
        assert Decimal("0") < cost_guard < total
        strict = threshold(sl, su, total); expanded = threshold(el, eu, total); bound = boundary(el, eu, total)
        exact_s, exact_e = sl == su, el == eu
        adopted = sl if strict == "是" else el
        rows.append({
            "股票代码": code, "公司全称": s["公司全称"], "年份": year,
            "行业分类代码": s["行业分类代码"] or "待核实", "行业分类名称": s["行业分类名称"] or "待核实",
            "涉农业务_保守不重叠口径": business,
            "工作表采用涉农业务营业收入_元": f"{adopted:.2f}",
            "工作表采用收入公式": "采用可确认扩展下界：" + expanded_formula.split("；上界", 1)[0].removeprefix("下界="),
            "严格口径营业收入_元": f"{sl:.2f}" if exact_s else "", "严格口径收入公式": strict_formula if exact_s else "",
            "严格口径收入下界_元": f"{sl:.2f}", "严格口径收入上界_元": f"{su:.2f}", "严格口径上下界公式": strict_formula,
            "扩展口径营业收入_元": f"{el:.2f}" if exact_e else "", "扩展口径收入公式": expanded_formula if exact_e else "",
            "扩展口径收入下界_元": f"{el:.2f}", "扩展口径收入上界_元": f"{eu:.2f}", "扩展口径上下界公式": expanded_formula,
            "营业成本反核值_元": f"{cost_guard:.2f}", "营业成本反核公式或说明": cost_formula,
            "公司营业收入_元": f"{total:.2f}", "公司营业收入公式": "合并利润表营业收入",
            "严格口径下界原始未四舍五入比例": raw(sl, total), "严格口径上界原始未四舍五入比例": raw(su, total),
            "扩展口径下界原始未四舍五入比例": raw(el, total), "扩展口径上界原始未四舍五入比例": raw(eu, total),
            "工作表采用涉农收入占比": r8(adopted, total), "严格口径收入占比": r8(sl, total) if exact_s else "",
            "扩展口径收入占比": r8(el, total) if exact_e else "", "严格样本结论": strict,
            "扩展样本结论": expanded, "边界样本结论": bound, "是否存在分部收入重叠": overlap,
            "金额精度或补充证据说明": precision_note, "复核说明": note,
            "待核实点": "2022逐公司行业分类待核实；收入结论仅据年报，不用相邻年份外推。" if year == 2022 else "2022逐公司行业分类仍待核实，不影响本年年报收入复核。",
            "年报主营业务证据PDF页序号": pages, "公司营业收入证据PDF页序号": s["利润表PDF页序号"],
            "年报链接": s["年报链接"], "记录类型": "第十四批G组新增跨年快速复核（未合并）", "复核日期": "2026-08-11",
        })

    out = pd.DataFrame(rows)
    assert len(out) == 21 and not out.duplicated(["股票代码", "年份"]).any()
    assert out["严格样本结论"].value_counts().to_dict() == {"否": 21}
    assert out["扩展样本结论"].value_counts().to_dict() == {"是": 21}
    assert out["边界样本结论"].value_counts().to_dict() == {"否": 21}
    assert out["年报链接"].str.startswith("https://static.cninfo.com.cn/").all()
    assert out["年报主营业务证据PDF页序号"].ne("").all() and out["公司营业收入证据PDF页序号"].ne("").all()
    assert (out[out["股票代码"] == "002311"]["严格口径营业收入_元"] == "").all()
    assert out.loc[(out["股票代码"] == "002385") & (out["年份"] == 2015), "严格口径营业收入_元"].iloc[0] == "280820200.00"
    assert (out[out["股票代码"] == "600195"]["严格口径营业收入_元"] == "0.00").all()
    out.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("batch14-G rows=21; strict no=21; expanded yes=21; boundary no=21; not merged")


if __name__ == "__main__":
    main()
