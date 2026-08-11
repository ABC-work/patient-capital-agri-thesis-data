#!/usr/bin/env python3
"""Build standalone historical fast-review batch 18-S from fixed v27.

Plant-protein beverages, leisure seed/nut foods and milk beverages are deep
processing. Only separately disclosed planting, primary processing, feed or
other agricultural-input revenue is included. Unspecified product/other-
business revenue is used only as a conservative upper bound. Revenue and cost
dimensions are kept separate; costs are reverse evidence only.
"""
from decimal import Decimal, getcontext
from pathlib import Path

import pandas as pd


getcontext().prec = 60
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v27_跨年快速复核第十六批第一组.csv"
OUTPUT = ROOT / "outputs" / "跨年快速复核第十八批_S组_3家公司.csv"

# Total revenue; excluded plant-protein beverage revenue/cost; product "other"
# revenue/cost. Product other is not disaggregated and is upper-bound only.
LULU = {
    2014: ("2702791629.97", "2700209877.10", "1577862365.55", "2581752.87", "2251529.98"),
    2015: ("2706238122.26", "2703458701.55", "1527971802.50", "2779420.71", "1294751.71"),
    2018: ("2121966609.34", "2075413591.70", "1008692503.59", "46553017.64", "36215635.73"),
    2019: ("2255394058.97", "2253373440.87", "1067134713.12", "2020618.10", "1571927.51"),
    2020: ("1860643698.75", "1859310490.40", "926952954.09", "1333208.35", "1037161.29"),
    2021: ("2523907407.01", "2521301798.90", "1340914197.61", "2605608.11", "2027016.91"),
    2022: ("2692021224.82", "2690196008.16", "1483125212.81", "1825216.66", "1419916.15"),
}

# Total revenue; excluded main-business seed/nut snack revenue/cost; unspecified
# product revenue/cost used as upper bound. For 2018-2021 the published product
# "other" already includes other business. For 2022 it is the sum of separately
# stated other products and other business.
QIAQIA = {
    2018: ("4197045559.14", "3311907734.91", "2226719894.50", "885137824.23", "662435253.53"),
    2019: ("4837252294.43", "4127334504.06", "2752722585.13", "709917790.37", "475744800.80"),
    2020: ("5289304049.87", "4675116004.90", "3164021683.89", "614188044.97", "438494498.13"),
    2021: ("5985026032.16", "5309782433.73", "3564079931.92", "675243598.43", "508432091.80"),
    2022: ("6883365207.54", "6135226699.78", "4143767355.09", "748138507.76", "539468911.72"),
}

# Total; primary grain processing revenue/cost (or 2014-15 mixed flour/oil);
# unspecified main-product other; and audited other-business revenue/cost.
WEIWEI = {
    2014: ("4462424768.90", "200805224.86", "195272737.47", "215978726.50", "125564055.22", "212062744.13", "156153265.07"),
    2015: ("3887769559.40", "175813073.09", "173595585.10", "2087894.65", "235666.91", "28897572.31", "13089993.56"),
    2018: ("5032918225.33", "2014943200.00", "1984687800.00", "72199600.00", "62540800.00", "63024988.24", "29071607.48"),
    2019: ("5039164760.23", "2055120200.00", "2011568100.00", "75765900.00", "76125700.00", "93041537.36", "38441552.30"),
    2020: ("4798816953.10", "2122421400.00", "2050144200.00", "62376200.00", "48351900.00", "90453127.86", "22498127.99"),
    2021: ("4568174605.60", "2138311200.00", "2067671600.00", "78986300.00", "64172200.00", "49927636.60", "24450676.61"),
    2022: ("4222228361.42", "1669972600.00", "1620743500.00", "65519200.00", "53425900.00", "58112022.80", "25670543.46"),
}


def D(value: str) -> Decimal:
    return Decimal(value)


def ratio(numerator: Decimal, denominator: Decimal) -> str:
    return format(numerator / denominator, "f")


def threshold(lo: Decimal, hi: Decimal) -> str:
    if lo >= D("0.50"):
        return "是"
    if hi < D("0.50"):
        return "否"
    return "待核实"


def boundary(lo: Decimal, hi: Decimal) -> str:
    if lo >= D("0.50") or hi < D("0.30"):
        return "否"
    if lo >= D("0.30") and hi < D("0.50"):
        return "是"
    return "待核实"


def compact(value: str) -> str:
    return value.replace(",", "").replace(" ", "").replace("\n", "")


def main() -> None:
    source = pd.read_csv(SOURCE, dtype={"股票代码": str}, keep_default_na=False)
    selected = source[
        source["股票代码"].isin(["000848", "002557", "600300"])
        & source["复核状态"].str.startswith("年报及业务表已定位", na=False)
    ].sort_values(["股票代码", "年份"])
    assert len(source) == 958 and len(selected) == 19
    assert selected.groupby("股票代码").size().to_dict() == {"000848": 7, "002557": 5, "600300": 7}
    assert not selected.duplicated(["股票代码", "年份"]).any()

    rows = []
    for _, src in selected.iterrows():
        code, year = src["股票代码"], int(src["年份"])
        primary_revenue = primary_cost = product_other = product_other_cost = D("0")
        other_business = other_business_cost = deep_revenue = deep_cost = D("0")

        if code == "000848":
            values = map(D, LULU[year])
            total, deep_revenue, deep_cost, product_other, product_other_cost = values
            strict_lo = expanded_lo = D("0")
            strict_hi = expanded_hi = product_other
            strict_business = "未单列农业种植或农业投入品对外收入；产品“其他”仅作上界"
            expanded_business = "未单列农产品初加工或农业投入品收入；产品“其他”仅作上界"
            strict_formula = expanded_formula = f"下界=0；上界=未拆产品其他{product_other:.2f}"
            deep_label = "杏仁露、核桃露等植物蛋白饮料"
            overlap = "植物蛋白饮料与产品其他为同一产品维度互斥项目；不叠加行业或地区维度"
            reason = "植物蛋白饮料属于深加工；未披露可确认的种植、初加工、饲料或其他农业投入品收入。"
            pending = "产品“其他”未拆具体性质，只作上界；上界低于30%。"
            cost_note = f"植物蛋白饮料成本{deep_cost:.2f}为排除项；产品其他成本{product_other_cost:.2f}只作上界反向证据"
            evidence_extra = "2014、2022管理层业务表与审计附注成本分别相差0.01元、0.05元，采用审计附注数值，不影响收入判断"
        elif code == "002557":
            values = map(D, QIAQIA[year])
            total, deep_revenue, deep_cost, product_other, product_other_cost = values
            strict_lo = expanded_lo = D("0")
            strict_hi = expanded_hi = product_other
            strict_business = "未单列农业种植或农业投入品对外收入；未拆产品其他仅作上界"
            expanded_business = "未单列初加工或农业投入品收入；未拆产品其他仅作上界"
            strict_formula = expanded_formula = f"下界=0；上界=未拆产品其他（含其他业务）{product_other:.2f}"
            deep_label = "葵花子、坚果及其他休闲食品"
            overlap = "2018—2021产品“其它”已含其他业务，不重复相加；2022产品其他与其他业务互斥后相加；不叠加行业、地区维度"
            reason = "籽类、坚果及休闲食品属于深加工；未拆“其他”不能直接认定为初加工，但全部作上界仍低于30%。"
            pending = "产品“其他”未拆初加工、农业投入品与深加工收入，只作上界。"
            cost_note = f"可确认籽类/坚果产品成本{deep_cost:.2f}为深加工排除证据；未拆产品其他成本{product_other_cost:.2f}只作反向证据"
            evidence_extra = "可确认深加工额按主营业务中葵花子与坚果互斥项目合计；2020—2022主营产品其他成本以互斥产品成本作残差核对，再加其他业务成本；不以成本比例推算收入"
        else:
            values = map(D, WEIWEI[year])
            total, primary_revenue, primary_cost, product_other, product_other_cost, other_business, other_business_cost = values
            strict_lo = D("0")
            strict_hi = product_other + other_business
            if year in (2014, 2015):
                expanded_lo = D("0")
                expanded_hi = primary_revenue + product_other + other_business
                primary_label = "食用面粉及食用油（混合披露）"
                expanded_business = "食用面粉及食用油混合项目未能可靠拆分，连同产品其他、其他业务仅作扩展上界"
                expanded_formula = (
                    f"下界=0；上界=混合面粉及食用油{primary_revenue:.2f}+产品其他{product_other:.2f}"
                    f"+审计其他业务{other_business:.2f}={expanded_hi:.2f}"
                )
                pending = "面粉与食用油合并披露，无法确认其中农产品初加工金额；未拆项目只作上界，上界低于30%。"
            else:
                expanded_lo = primary_revenue
                expanded_hi = primary_revenue + product_other + other_business
                primary_label = "粮食初加工产品"
                expanded_business = "单列粮食初加工产品纳入扩展下界；产品其他和审计其他业务只作扩展上界"
                expanded_formula = (
                    f"下界=粮食初加工{primary_revenue:.2f}；上界=下界+产品其他{product_other:.2f}"
                    f"+审计其他业务{other_business:.2f}={expanded_hi:.2f}"
                )
                pending = "产品其他和审计其他业务未拆，只作上界；扩展下界已不低于30%，且上界仍低于50%。"
            strict_business = "未单列农业种植对外收入；产品其他和审计其他业务仅作严格上界"
            strict_formula = f"下界=0；上界=产品其他{product_other:.2f}+审计其他业务{other_business:.2f}={strict_hi:.2f}"
            deep_label = "固态冲调饮料、动植物蛋白饮料、酒类、茶类等深加工；粮食初加工按扩展口径单列"
            overlap = "产品分项属于主营业务维度，审计其他业务为互斥收入层级，可相加作上界；不叠加行业、地区或销售模式维度"
            reason = "饮料及其他食品深加工不纳入；2018—2022单列粮食初加工收入纳入扩展口径，但占比不足50%。"
            precision_note = "；业务表以万元保留两位小数，换算为元后的披露精度至百元" if year >= 2018 else ""
            cost_note = (
                f"{primary_label}成本{primary_cost:.2f}；产品其他成本{product_other_cost:.2f}+其他业务成本"
                f"{other_business_cost:.2f}={product_other_cost + other_business_cost:.2f}，成本只作反向证据{precision_note}"
            )
            evidence_extra = "2014—2015混合项目不拆分、不估算；2018—2022年报明确列示“粮食初加工产品”"
            if year == 2020:
                evidence_extra += "；产品成本采用2020年年报原披露口径；2021年报将2020年营业总成本追溯重述为3781946352.88元，但未提供产品级重分配，不据此反推产品成本，不影响收入判定"

        assert D("0") <= strict_lo <= strict_hi <= total
        assert D("0") <= expanded_lo <= expanded_hi <= total
        sr_lo, sr_hi = strict_lo / total, strict_hi / total
        er_lo, er_hi = expanded_lo / total, expanded_hi / total
        # v27's 600300-2021 profit locator points to an accounting-correction
        # page rather than the statement itself; its management excerpt still
        # contains the exact consolidated revenue. Accept either fixed excerpt.
        source_evidence = compact(src["利润表原文摘录"] + src["主营业务表原文摘录"])
        assert compact(f"{total:.2f}") in source_evidence or (
            code == "600300" and year == 2021 and "78" in src["利润表PDF页序号"]
        )

        rows.append({
            "股票代码": code,
            "公司全称": src["公司全称"],
            "年份": year,
            "行业分类代码": src["行业分类代码"] or ("待核实" if year == 2022 else ""),
            "行业分类名称": src["行业分类名称"] or ("待核实" if year == 2022 else ""),
            "严格口径涉农业务": strict_business,
            "严格口径正式涉农收入_元": f"{strict_lo:.2f}" if strict_lo == strict_hi else "",
            "严格口径收入下界_元": f"{strict_lo:.2f}",
            "严格口径收入上界_元": f"{strict_hi:.2f}",
            "严格口径上下界公式": strict_formula,
            "严格口径下界占比_原始未四舍五入": ratio(strict_lo, total),
            "严格口径上界占比_原始未四舍五入": ratio(strict_hi, total),
            "扩展口径涉农业务": expanded_business,
            "扩展口径正式涉农收入_元": f"{expanded_lo:.2f}" if expanded_lo == expanded_hi else "",
            "扩展口径收入下界_元": f"{expanded_lo:.2f}",
            "扩展口径收入上界_元": f"{expanded_hi:.2f}",
            "扩展口径上下界公式": expanded_formula,
            "扩展口径下界占比_原始未四舍五入": ratio(expanded_lo, total),
            "扩展口径上界占比_原始未四舍五入": ratio(expanded_hi, total),
            "公司营业收入_元": f"{total:.2f}",
            "公司营业收入公式": "合并利润表营业收入",
            "初加工或混合项目收入_元": f"{primary_revenue:.2f}" if primary_revenue else "",
            "初加工或混合项目成本_元_反向证据": f"{primary_cost:.2f}" if primary_cost else "",
            "产品其他收入_元_上界": f"{product_other:.2f}",
            "产品其他成本_元_反向证据": f"{product_other_cost:.2f}",
            "审计其他业务收入_元_上界": f"{other_business:.2f}" if other_business else "",
            "审计其他业务成本_元_反向证据": f"{other_business_cost:.2f}" if other_business_cost else "",
            "深加工或排除类别": deep_label,
            "深加工类别收入_元_反向证据": f"{deep_revenue:.2f}" if deep_revenue else "",
            "深加工类别成本_元_反向证据": f"{deep_cost:.2f}" if deep_cost else "",
            "收入成本判别": cost_note,
            "严格样本结论": threshold(sr_lo, sr_hi),
            "扩展样本结论": threshold(er_lo, er_hi),
            "边界样本结论": boundary(er_lo, er_hi),
            "是否存在分部收入重叠": overlap,
            "纳入或剔除理由": reason,
            "待核实点": pending + ("2022行业分类字段仍待核实。" if year == 2022 else ""),
            "年报主营业务证据PDF页序号": src["年报主营业务候选PDF页序号"],
            "公司营业收入证据PDF页序号": "78" if code == "600300" and year == 2021 else src["利润表PDF页序号"],
            "补充证据说明": evidence_extra,
            "年报链接": src["年报链接"],
            "2022行业字段处理": "沿用v27原值；待核实字段不插值、不复制相邻年份",
            "记录类型": "跨年快速复核第十八批S组（未合并）",
            "复核状态": "已人工复核（第十八批S组；主表未合并）",
            "复核日期": "2026-08-11",
        })

    out = pd.DataFrame(rows)
    assert len(out) == 19 and not out.duplicated(["股票代码", "年份"]).any()
    assert out["严格样本结论"].value_counts().to_dict() == {"否": 19}
    assert out["扩展样本结论"].value_counts().to_dict() == {"否": 19}
    assert out["边界样本结论"].value_counts().to_dict() == {"否": 14, "是": 5}
    boundary_rows = out[out["边界样本结论"].eq("是")]
    assert boundary_rows[["股票代码", "年份"]].to_records(index=False).tolist() == [
        ("600300", 2018), ("600300", 2019), ("600300", 2020), ("600300", 2021), ("600300", 2022)
    ]
    vv21 = out[(out["股票代码"] == "600300") & (out["年份"] == 2021)].iloc[0]
    assert vv21["扩展口径收入上界_元"] == "2267225136.60"
    assert D(vv21["扩展口径上界占比_原始未四舍五入"]) < D("0.50")
    assert vv21["公司营业收入证据PDF页序号"] == "78"
    vv20 = out[(out["股票代码"] == "600300") & (out["年份"] == 2020)].iloc[0]
    assert "产品成本采用2020年年报原披露口径" in vv20["补充证据说明"]
    assert "3781946352.88" in vv20["补充证据说明"]
    qq22 = out[(out["股票代码"] == "002557") & (out["年份"] == 2022)].iloc[0]
    assert qq22["产品其他收入_元_上界"] == "748138507.76"
    assert qq22["产品其他成本_元_反向证据"] == "539468911.72"
    ll22 = out[(out["股票代码"] == "000848") & (out["年份"] == 2022)].iloc[0]
    assert ll22["深加工类别成本_元_反向证据"] == "1483125212.81"
    assert out.loc[out["年份"].eq(2022), "行业分类代码"].eq("待核实").all()
    assert out.loc[out["年份"].eq(2022), "行业分类名称"].eq("待核实").all()
    assert out["年报链接"].str.startswith("https://static.cninfo.com.cn/").all()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("batch18-S rows=19; strict no=19; expanded no=19; boundary yes=5/no=14; not merged")


if __name__ == "__main__":
    main()
