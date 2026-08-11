#!/usr/bin/env python3
"""Build independent fast-review batch 15-M from the fixed v25 worktable.

The output is standalone and is not merged into v25.  Fibreboard, particle
board and plywood are treated as manufacturing/deep processing, while retail
sales of fresh food are not treated as agricultural production or processing.
"""
from decimal import Decimal, getcontext
from pathlib import Path

import pandas as pd


getcontext().prec = 60
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v25_跨年快速复核第十五批第一组.csv"
OUTPUT = ROOT / "outputs" / "跨年快速复核第十五批_M组_3家公司.csv"


# year: forest segment revenue/cost, mixed-other revenue/cost, internal
# elimination revenue/cost (absolute value), consolidated operating revenue.
# The first six amounts are reported in RMB 10,000 and converted below.
FENGLIN = {
    2014: ("8222.45", "3908.55", "7642.36", "7369.93", "7012.39", "6957.26", "1199474212.66"),
    2015: ("5488.62", "3037.19", "7568.85", "7290.74", "7413.31", "7356.16", "1156231820.59"),
    2018: ("4774.95", "2467.77", "15230.86", "13875.95", "5340.10", "5340.10", "1597217257.61"),
    2019: ("5715.71", "2505.98", "3079.85", "2906.29", "7769.01", "7774.48", "1942722797.84"),
    2020: ("6439.66", "3211.91", "2104.38", "1760.75", "7553.09", "7514.22", "1740378744.45"),
    2021: ("7623.47", "3148.07", "11988.63", "11196.91", "10378.10", "10395.45", "2066287371.94"),
    2022: ("7190.20", "2602.54", "12732.25", "12399.62", "11442.49", "11448.63", "2052675537.74"),
}


# year: separately disclosed fertiliser revenue, fertiliser cost and total.
# Fertiliser was not separately quantified in 2014/2015.  The 2019 annual
# report's +18.14% comparison proves that 2018 was non-zero, but does not give a
# reliable 2018 amount; the 2019 current-period amount is therefore retained
# only as a deliberately wide screening upper bound.  The 2022 product table is
# in RMB 10,000; the converted values preserve its source precision.
ERDOS = {
    2014: ("0", "0", "15568400216.07"),
    2015: ("0", "0", "15240089997.22"),
    2018: ("0", "0", "23858165635.57"),
    2019: ("1049814919.78", "707799029.16", "22789922588.51"),
    2020: ("1023829343.00", "689285463.20", "23141197882.47"),
    2021: ("1451334662.21", "920084340.59", "36473310790.40"),
    2022: ("1848543500.00", "1387273500.00", "36393429151.70"),
}


# year: excluded fresh-and-processed retail sales/cost and consolidated total.
# The retail line is retained only as counter-evidence and never enters an
# agricultural numerator.  2021/2022 were reported in RMB 10,000.
YONGHUI = {
    2014: ("16301624488.53", "14217159975.68", "36726802955.31"),
    2015: ("18506455633.13", "16136560159.60", "42144829561.56"),
    2018: ("31663327673.87", "26958736411.20", "70516654453.22"),
    2019: ("37122204483.92", "32213659463.23", "84876960043.74"),
    2020: ("41480803073.63", "35739233559.98", "93199107664.03"),
    2021: ("40825752400.00", "36186521700.00", "91061894312.13"),
    2022: ("39900463800.00", "34931325400.00", "90090819396.14"),
}


def D(value: str) -> Decimal:
    return Decimal(value)


def wan(value: str) -> Decimal:
    return D(value) * D("10000")


def raw(numerator: Decimal, denominator: Decimal) -> str:
    return format(numerator / denominator, "f")


def threshold(lower: Decimal, upper: Decimal) -> str:
    if lower >= D("0.50"):
        return "是"
    if upper < D("0.50"):
        return "否"
    return "待核实"


def boundary(lower: Decimal, upper: Decimal) -> str:
    if lower >= D("0.50") or upper < D("0.30"):
        return "否"
    if lower >= D("0.30") and upper < D("0.50"):
        return "是"
    return "待核实"


def compact(value: str) -> str:
    return value.replace(",", "").replace(" ", "").replace("\n", "")


def main() -> None:
    source = pd.read_csv(SOURCE, dtype={"股票代码": str}, keep_default_na=False)
    selected = source[
        source["股票代码"].isin(["601996", "600295", "601933"])
        & source["复核状态"].str.startswith("年报及业务表已定位", na=False)
    ].sort_values(["股票代码", "年份"])
    assert len(source) == 958
    assert len(selected) == 21
    assert selected.groupby("股票代码").size().to_dict() == {"600295": 7, "601933": 7, "601996": 7}
    assert set(selected["年份"].astype(int)) == {2014, 2015, 2018, 2019, 2020, 2021, 2022}
    assert not selected.duplicated(["股票代码", "年份"]).any()

    rows = []
    for _, src in selected.iterrows():
        code, year = src["股票代码"], int(src["年份"])
        strict_lo = strict_cost_lo = D("0")
        excluded_revenue = excluded_cost = D("0")
        internal_elimination = internal_elimination_cost = D("0")
        precision_note = ""

        if code == "601996":
            forest_s, forest_cost_s, other_s, other_cost_s, elim_s, elim_cost_s, total_s = FENGLIN[year]
            forest, forest_cost = wan(forest_s), wan(forest_cost_s)
            other, other_cost = wan(other_s), wan(other_cost_s)
            elimination, elimination_cost = wan(elim_s), wan(elim_cost_s)
            internal_elimination, internal_elimination_cost = elimination, elimination_cost
            total = D(total_s)
            strict_hi, strict_cost_hi = forest, forest_cost
            expanded_lo, expanded_cost_lo = D("0"), D("0")
            expanded_hi, expanded_cost_hi = forest + other, forest_cost + other_cost
            strict_business = "林木分部可能包含直接林业，但存在未分配内部抵消，仅作严格上界"
            expanded_business = "林木+其他混合项仅作上界；人造板、纤维板、刨花板和胶合板排除"
            strict_formula = f"下界=0；上界=林木分部{forest:.2f}"
            expanded_formula = f"下界=0；上界=林木{forest:.2f}+混合其他{other:.2f}={expanded_hi:.2f}"
            cost_note = (
                f"林木成本上界{forest_cost:.2f}；混合其他成本上界增量{other_cost:.2f}；"
                f"内部抵消收入{elimination:.2f}、成本{elimination_cost:.2f}未分配到产品行"
            )
            overlap = "存在内部交易抵消，但无法在林木与其他产品间分配；因此两项均不形成下界"
            audit_note = (
                "林板及人造板属于制造深加工，不自动认定为农产品初加工；林木虽可能是直接林业，"
                "但产品表另列内部抵消，无法证明该行全部为合并外销。其他混含苗木、化工贸易及租赁。"
            )
            pending = "需取得内部抵消按产品分配及‘其他’收入明细，方可确认合并外销林木/苗木收入。"
            evidence_keyword = "林木"
            source_unit = "主营业务表单位为万元，按×10,000换算"
        elif code == "600295":
            fertiliser_s, fertiliser_cost_s, total_s = ERDOS[year]
            fertiliser, fertiliser_cost, total = D(fertiliser_s), D(fertiliser_cost_s), D(total_s)
            strict_hi = strict_cost_hi = D("0")
            if year == 2018:
                expanded_lo, expanded_hi = D("0"), D(ERDOS[2019][0])
                expanded_cost_lo = expanded_cost_hi = D("0")
            else:
                expanded_lo = expanded_hi = fertiliser
                expanded_cost_lo = expanded_cost_hi = fertiliser_cost
            strict_business = "煤电、冶金、化工和服装均非直接农业"
            if year in {2014, 2015}:
                expanded_business = "年报未见并表口径单列化肥收入；其余煤电冶金化工及服装排除"
            elif year == 2018:
                expanded_business = "2019年报同比增幅反证2018年存在化肥收入，但2018金额无法可靠拆出"
            else:
                expanded_business = "单列化肥属于农业投入品；其余煤电冶金化工及服装排除"
            strict_formula = "下界=上界=0"
            if year in {2014, 2015}:
                expanded_formula = "未取得可计量的并表单列化肥分子；正式分子留空"
                cost_note = "未取得并表口径单列化肥营业成本；不将未单列解释为真实业务为零"
            elif year == 2018:
                expanded_formula = f"下界=0；宽上界=2019年单列化肥收入{expanded_hi:.2f}（仅用于阈值筛查）"
                cost_note = "2018化肥成本未可靠拆出，成本证据不作零值认定"
            else:
                expanded_formula = f"下界=上界=单列化肥{fertiliser:.2f}"
                cost_note = f"单列化肥营业成本{fertiliser_cost:.2f}；成本未误作收入"
            overlap = "否（采用单列分产品化肥行，未与电冶行业行交叉加总）"
            audit_note = "化肥为农业投入品；硅铁、硅锰、煤炭、电石、PVC、烧碱、多晶硅和服装均排除。2018宽上界不是正式分子。"
            pending = (
                "2014/2015未见并表单列收入，正式分子留空；不得从电冶板块反推。"
                if year in {2014, 2015} else
                "2018正式化肥分子与成本待取得原始分产品明细；2019年金额仅为宽上界。"
                if year == 2018 else "无。"
            )
            evidence_keyword = "化肥" if fertiliser else ("电冶" if year in {2014, 2015} else "硅铁")
            source_unit = "2022主营业务表单位为万元并按×10,000换算" if year == 2022 else "主营业务表单位为元"
            if year == 2022:
                precision_note = "化肥收入184,854.35万元、成本138,727.35万元；换算值保留原表万元小数点后两位精度。"
        else:
            fresh_s, fresh_cost_s, total_s = YONGHUI[year]
            excluded_revenue, excluded_cost, total = D(fresh_s), D(fresh_cost_s), D(total_s)
            strict_hi = strict_cost_hi = D("0")
            expanded_lo = expanded_hi = expanded_cost_lo = expanded_cost_hi = D("0")
            strict_business = "无单列直接农业生产收入"
            expanded_business = "生鲜及加工为超市零售商品销售，不等于农业生产或合格初加工"
            strict_formula = "下界=上界=0"
            expanded_formula = "下界=上界=0（零售生鲜及加工全部排除）"
            cost_note = f"被排除的生鲜及加工零售收入{excluded_revenue:.2f}、成本{excluded_cost:.2f}"
            overlap = "否（零售商品类别作为整体排除，不与行业或地区行加总）"
            audit_note = "采购或销售农产品不等于直接农业生产、初加工、农业投入品或农业生产性服务。"
            pending = "如未来取得公司自营农业生产或独立初加工对外收入，须另行逐项核实；当前不得由采购额推收入。"
            evidence_keyword = "生鲜"
            source_unit = "2021/2022主营业务表单位为万元并按×10,000换算" if year >= 2021 else "主营业务表单位为元"
            if year >= 2021:
                precision_note = "生鲜及加工收入、成本按年报万元表×10,000换算，保留原表万元小数点后两位精度。"

        assert compact(format(total, "f")) in compact(src["利润表原文摘录"]), (code, year, "denominator")
        assert evidence_keyword in src["主营业务表原文摘录"], (code, year, "business evidence")
        assert D("0") <= strict_lo <= strict_hi <= total
        assert D("0") <= expanded_lo <= expanded_hi <= total
        assert D("0") <= strict_cost_lo <= strict_cost_hi
        assert D("0") <= expanded_cost_lo <= expanded_cost_hi
        sr_lo, sr_hi = strict_lo / total, strict_hi / total
        er_lo, er_hi = expanded_lo / total, expanded_hi / total
        strict_result, expanded_result = threshold(sr_lo, sr_hi), threshold(er_lo, er_hi)
        boundary_result = boundary(er_lo, er_hi)

        rows.append({
            "股票代码": code, "公司全称": src["公司全称"], "年份": year,
            "行业分类代码": src["行业分类代码"] or "待核实", "行业分类名称": src["行业分类名称"] or "待核实",
            "严格口径涉农业务": strict_business, "严格口径正式涉农收入_元": "",
            "严格口径收入下界_元": f"{strict_lo:.2f}", "严格口径收入上界_元": f"{strict_hi:.2f}",
            "严格口径上下界公式": strict_formula, "严格口径下界占比_原始未四舍五入": raw(strict_lo, total),
            "严格口径上界占比_原始未四舍五入": raw(strict_hi, total),
            "扩展口径涉农业务": expanded_business,
            "扩展口径正式涉农收入_元": (
                f"{expanded_lo:.2f}" if code == "600295" and year >= 2019 else ""
            ),
            "扩展口径正式涉农收入占比_原始未四舍五入": (
                raw(expanded_lo, total) if code == "600295" and year >= 2019 else ""
            ),
            "扩展口径收入下界_元": f"{expanded_lo:.2f}", "扩展口径收入上界_元": f"{expanded_hi:.2f}",
            "扩展口径上下界公式": expanded_formula, "扩展口径下界占比_原始未四舍五入": raw(expanded_lo, total),
            "扩展口径上界占比_原始未四舍五入": raw(expanded_hi, total),
            "公司营业收入_元": f"{total:.2f}", "公司营业收入公式": "合并利润表营业收入",
            "严格口径成本下界_元_反向证据": f"{strict_cost_lo:.2f}",
            "严格口径成本上界_元_反向证据": f"{strict_cost_hi:.2f}",
            "扩展口径成本下界_元_反向证据": (
                "" if code == "600295" and year == 2018 else f"{expanded_cost_lo:.2f}"
            ),
            "扩展口径成本上界_元_反向证据": (
                "" if code == "600295" and year == 2018 else f"{expanded_cost_hi:.2f}"
            ),
            "排除项目收入_元_反向证据": f"{excluded_revenue:.2f}",
            "排除项目成本_元_反向证据": f"{excluded_cost:.2f}",
            "内部抵消收入绝对值_元_反向证据": f"{internal_elimination:.2f}",
            "内部抵消成本绝对值_元_反向证据": f"{internal_elimination_cost:.2f}",
            "收入成本反核说明": cost_note,
            "严格样本结论": strict_result, "扩展样本结论": expanded_result, "边界样本结论": boundary_result,
            "是否存在分部收入重叠": overlap,
            "纳入或剔除理由": f"严格区间[{raw(strict_lo,total)}, {raw(strict_hi,total)}]；扩展区间[{raw(expanded_lo,total)}, {raw(expanded_hi,total)}]。{audit_note}",
            "待核实点": pending, "金额单位及精度说明": source_unit + ("；" + precision_note if precision_note else ""),
            "年报主营业务证据PDF页序号": src["年报主营业务表PDF页序号"],
            "公司营业收入证据PDF页序号": src["利润表PDF页序号"], "年报链接": src["年报链接"],
            "2022行业字段处理": "沿用v25原值；待核实字段不插值、不复制相邻年份",
            "记录类型": "跨年快速复核第十五批M组（未合并）",
            "复核状态": "已人工复核（第十五批M组；主表未合并）", "复核日期": "2026-08-11",
        })

    out = pd.DataFrame(rows)
    assert len(out) == 21 and not out.duplicated(["股票代码", "年份"]).any()
    assert out["严格样本结论"].value_counts().to_dict() == {"否": 21}
    assert out["扩展样本结论"].value_counts().to_dict() == {"否": 21}
    assert out["边界样本结论"].value_counts().to_dict() == {"否": 21}
    assert out["严格口径正式涉农收入_元"].eq("").all()
    erdos_exact = out["股票代码"].eq("600295") & out["年份"].ge(2019)
    assert out.loc[erdos_exact, "扩展口径正式涉农收入_元"].ne("").all()
    assert out.loc[erdos_exact, "扩展口径正式涉农收入占比_原始未四舍五入"].ne("").all()
    assert out.loc[~erdos_exact, "扩展口径正式涉农收入_元"].eq("").all()
    assert out.loc[out["年份"].eq(2022), "行业分类代码"].eq("待核实").all()
    assert out.loc[out["年份"].eq(2022), "行业分类名称"].eq("待核实").all()
    assert out.loc[out["股票代码"].eq("601933"), "扩展口径收入上界_元"].eq("0.00").all()
    assert out.loc[out["股票代码"].eq("601996"), "扩展口径收入下界_元"].eq("0.00").all()
    assert out.loc[out["股票代码"].eq("601996"), "内部抵消收入绝对值_元_反向证据"].ne("0.00").all()
    assert out.loc[(out["股票代码"].eq("600295")) & (out["年份"].le(2015)), "扩展口径收入上界_元"].eq("0.00").all()
    assert out.loc[(out["股票代码"].eq("600295")) & (out["年份"].eq(2018)), "扩展口径收入下界_元"].iloc[0] == "0.00"
    assert out.loc[(out["股票代码"].eq("600295")) & (out["年份"].eq(2018)), "扩展口径收入上界_元"].iloc[0] == "1049814919.78"
    assert out.loc[(out["股票代码"].eq("600295")) & (out["年份"].eq(2018)), "扩展口径成本下界_元_反向证据"].iloc[0] == ""
    assert out.loc[(out["股票代码"].eq("600295")) & (out["年份"].eq(2018)), "扩展口径成本上界_元_反向证据"].iloc[0] == ""
    assert out.loc[(out["股票代码"].eq("600295")) & (out["年份"].eq(2022)), "扩展口径收入上界_元"].iloc[0] == "1848543500.00"
    assert all(D(value) < D("0.30") for value in out["扩展口径上界占比_原始未四舍五入"])
    assert out["年报链接"].str.startswith("https://static.cninfo.com.cn/").all()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("batch15-M rows=21; strict no=21; expanded no=21; boundary no=21; not merged")


if __name__ == "__main__":
    main()
