#!/usr/bin/env python3
"""Build standalone historical fast-review batch 16-P from fixed v26.

Frozen food, condiments/refined packaged oil and leisure-date food are deep
processing.  Only separately disclosed direct agriculture, initial processing
or agricultural inputs enter a numerator.  Unsplit "other" revenue is an upper
bound only; product and industry dimensions are never added mechanically.
"""
from decimal import Decimal, getcontext
from pathlib import Path

import pandas as pd


getcontext().prec = 60
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v26_跨年快速复核第十五批第二组.csv"
OUTPUT = ROOT / "outputs" / "跨年快速复核第十六批_P组_3家公司.csv"

# total revenue, other-business revenue/cost, frozen-food main revenue/cost,
# separately disclosed commodity-pig revenue/cost (2014 only).
SANQUAN = {
    2014: ("4094370562.23", "11265199.74", "4142954.76", "4079516138.09", "2670020128.05", "3589224.40", "4355620.01"),
    2015: ("4237398972.24", "15416675.90", "7287980.64", "4221982296.34", "2834672917.65", "0", "0"),
    2018: ("5539316059.52", "13805448.06", "2838473.06", "5525510611.46", "3568882545.50", "0", "0"),
    2019: ("5985722254.07", "12154531.08", "421331.45", "5973567722.99", "3879916024.22", "0", "0"),
    2020: ("6926082823.06", "32020169.85", "21526738.81", "6894062653.21", "4836048432.27", "0", "0"),
    2021: ("6943439865.01", "42496079.50", "16106599.79", "6900943785.51", "5040812593.01", "0", "0"),
    2022: ("7434297659.46", "54485146.66", "20622070.74", "7379812512.80", "5327205785.11", "0", "0"),
}

# total revenue/cost, product-table "other" revenue/summary cost, edible-oil
# revenue/summary cost, and the detailed manufacturing-cost amount for "other".
# From 2015 onward the oil line mixes refined/packaged oil with tea-seed-oil
# projects or pressed peanut oil, so it is an expanded upper bound only.
JAJIA = {
    # total, total cost, other revenue, other summary cost, other detailed cost,
    # oil revenue, oil summary cost, oil detailed cost
    2014: ("1684750620.69", "1179741918.27", "52951308.48", "", "41682358.62", "0", "", ""),
    2015: ("1755008747.88", "1258004173.01", "84351458.49", "", "60310645.68", "503469565.93", "441126730.67", "445042934.46"),
    2018: ("1788414097.53", "1319332749.71", "94003840.40", "", "65051319.98", "518767559.28", "471304692.10", "471304692.10"),
    2019: ("2039752817.05", "1488753128.45", "138121243.78", "", "92223023.37", "609121459.42", "531319509.12", "531319509.12"),
    2020: ("2072648552.29", "1469782416.91", "148253906.40", "111316489.78", "104593298.23", "641590844.86", "523632323.44", "523632323.44"),
    2021: ("1754683993.13", "1402832602.57", "125591894.03", "91282030.73", "85722614.39", "550655417.41", "526570507.68", "526570507.68"),
    2022: ("1686107669.16", "1339061127.04", "154793783.19", "119077435.10", "104248498.18", "444865648.83", "420019447.06", "420019447.06"),
}

# total, audited other-business revenue/cost, separately disclosed original-date
# or mixed red-date revenue/cost.  Original-date sales in 2014-15 are confirmed
# initial processing; later red-date categories mix initial and deep processing.
HAOXIANGNI = {
    2014: ("972923969.99", "15819243.48", "9127662.87", "645800666.11", "350538700.47", "原枣类", True),
    2015: ("1113050303.75", "38861310.55", "41302812.67", "682588148.37", "", "原枣类", True),
    2018: ("4949436723.89", "31101711.86", "25575981.15", "868044839.85", "528494209.36", "红枣类", False),
    2019: ("5961168475.57", "61532366.54", "50815470.18", "734812453.66", "490717617.99", "红枣类", False),
    2020: ("3001375668.95", "48799979.64", "46482534.71", "665709589.37", "470407959.64", "红枣及相关类", False),
    2021: ("1281122736.07", "46406293.71", "36522847.98", "984559606.51", "711704998.00", "红枣及相关类", False),
    2022: ("1400490690.34", "60293415.53", "52110644.84", "955215978.76", "698859945.63", "红枣及相关类", False),
}


def D(value: str) -> Decimal:
    return Decimal(value)


def ratio(n: Decimal, d: Decimal) -> str:
    return format(n / d, "f")


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
        source["股票代码"].isin(["002216", "002650", "002582"])
        & source["复核状态"].str.startswith("年报及业务表已定位", na=False)
    ].sort_values(["股票代码", "年份"])
    assert len(source) == 958 and len(selected) == 21
    assert selected.groupby("股票代码").size().to_dict() == {"002216": 7, "002582": 7, "002650": 7}
    assert not selected.duplicated(["股票代码", "年份"]).any()

    rows = []
    for _, src in selected.iterrows():
        code, year = src["股票代码"], int(src["年份"])
        direct = initial = D("0")
        direct_cost_s = initial_cost_s = "0"
        if code == "002216":
            total_s, unknown_s, unknown_cost_s, deep_s, deep_cost_s, pig_s, pig_cost_s = SANQUAN[year]
            total, unknown, deep, deep_cost, pig = map(D, (total_s, unknown_s, deep_s, deep_cost_s, pig_s))
            direct, direct_cost_s = pig, pig_cost_s
            strict_lo = expanded_lo = pig
            strict_hi = expanded_hi = pig + unknown
            strict_business = "2014年单列商品猪（直接农业）；其余年份未单列直接农业收入"
            expanded_business = "同严格口径；速冻米面食品属于深加工，不纳入扩展口径"
            strict_formula = f"下界=商品猪{pig:.2f}；上界=商品猪{pig:.2f}+未拆其他业务{unknown:.2f}={strict_hi:.2f}"
            expanded_formula = strict_formula
            deep_label = "速冻面米制品等深加工食品"
            overlap = "主营/其他业务为互斥维度；分产品与分地区不相加；2014商品猪已从深加工主营收入中剔除"
            reason = "仅2014年单列商品猪属于直接农业；速冻食品为深加工，原料采购和原料基地不替代涉农收入。"
            pending = "其他业务未拆是否含直接农业、初加工或投入品，仅作上界；上界不影响结论。"
            cost_note = f"商品猪成本{D(pig_cost_s):.2f}；深加工主营成本{deep_cost:.2f}；其他业务成本{D(unknown_cost_s):.2f}，均未倒推收入"
        elif code == "002650":
            total_s, total_cost_s, unknown_s, unknown_cost_s, other_mfg_cost_s, oil_s, oil_cost_s, oil_mfg_cost_s = JAJIA[year]
            total, total_cost, unknown, oil = D(total_s), D(total_cost_s), D(unknown_s), D(oil_s)
            strict_lo = expanded_lo = D("0")
            strict_hi = unknown
            expanded_hi = unknown if year == 2014 else oil + unknown
            deep, deep_cost = total - oil - unknown, D("0")
            strict_business = "未单列直接农业生产收入"
            expanded_business = (
                "未单列可确认农产品初加工或农业投入品收入；产品“其他”仅作上界"
                if year == 2014 else "食用植物油混合大类（含茶籽油项目/压榨花生油初加工候选）及产品“其他”，仅作扩展上界"
            )
            strict_formula = f"下界=0；上界=未拆产品其他{unknown:.2f}"
            expanded_formula = strict_formula if year == 2014 else f"下界=0；上界=食用植物油混合大类{oil:.2f}+产品其他{unknown:.2f}={expanded_hi:.2f}"
            deep_label = "酱油、味精、食醋、鸡精等深加工食品（食用植物油混合大类另列扩展上界）"
            overlap = "产品维度覆盖营业收入，仅取产品“其他”作上界；不再叠加行业维度“其他”"
            reason = "调味品属于深加工；2015年后食用植物油大类同时存在精炼/分装与茶籽油项目、压榨花生油等初加工候选，不能整体确认为初加工。"
            pending = "产品“其他”未拆业务性质。" if year == 2014 else "食用植物油未拆初加工与精炼/分装收入，产品“其他”亦未拆，均只作扩展上界。"
            if year == 2014:
                cost_note = f"产品其他仅取得制造成本表成本{D(other_mfg_cost_s):.2f}；2014植物油维持排除，不以成本比例拆分收入"
            else:
                other_cost_text = (
                    f"产品其他摘要成本{D(unknown_cost_s):.2f}、制造成本表成本{D(other_mfg_cost_s):.2f}"
                    if unknown_cost_s else f"产品其他仅取得制造成本表成本{D(other_mfg_cost_s):.2f}"
                )
                cost_note = (
                    f"食用植物油摘要成本{D(oil_cost_s):.2f}、制造成本表成本{D(oil_mfg_cost_s):.2f}；{other_cost_text}。"
                    "摘要与制造成本表口径差异单列，不跨口径倒算或按成本比例拆分收入"
                )
        else:
            total_s, unknown_s, unknown_cost_s, dates_s, dates_cost_s, dates_label, original = HAOXIANGNI[year]
            total, unknown, dates = D(total_s), D(unknown_s), D(dates_s)
            if original:
                strict_lo, strict_hi = D("0"), dates + unknown
                expanded_lo, expanded_hi = dates, dates + unknown
                initial, initial_cost_s = dates, dates_cost_s
                strict_formula = f"下界=0；上界=原枣类{dates:.2f}+未拆其他业务{unknown:.2f}={strict_hi:.2f}"
                expanded_formula = f"下界=单列原枣类{dates:.2f}；上界=原枣类{dates:.2f}+未拆其他业务{unknown:.2f}={expanded_hi:.2f}"
                expanded_business = "单列原枣类（分选、清洗、包装等初加工）"
                pending = "其他业务未拆，仅作上下界增量；2015原枣类未取得同口径销售成本，不影响收入结论。" if year == 2015 else "其他业务未拆，仅作上界增量；不影响扩展样本结论。"
            else:
                strict_lo, strict_hi = D("0"), dates + unknown
                expanded_lo, expanded_hi = D("0"), dates + unknown
                strict_formula = f"下界=0；上界=混合{dates_label}{dates:.2f}+未拆其他业务{unknown:.2f}={strict_hi:.2f}"
                expanded_formula = f"下界=0；上界=混合{dates_label}{dates:.2f}+未拆其他业务{unknown:.2f}={expanded_hi:.2f}"
                expanded_business = f"{dates_label}混合类别（可能含原枣初加工，也含枣类休闲食品深加工）"
                pending = f"{dates_label}未拆原枣初加工与休闲食品深加工；其他业务亦未拆，均仅作上界。"
                if year == 2019:
                    pending += " 管理层产品表列其他业务61,493,991.41元，其主营产品小计5,899,674,484.16元；审计附注/营业收入扣除表列其他业务61,532,366.54元、主营业务5,899,636,109.03元，两端均差38,375.13元；采用审计附注数。"
            deep, deep_cost = dates, D(dates_cost_s) if dates_cost_s else D("0")
            strict_business = "未单列公司自营种植或其他直接农业收入"
            deep_label = (
                f"{dates_label}（确认初加工，非深加工反向证据）"
                if original else f"{dates_label}（初加工与枣类休闲食品深加工混合类别）"
            )
            overlap = "产品维度与主营/其他业务维度不机械相加；上界只加互斥的其他业务，原料基地和采购均不作收入"
            reason = "公司采购红枣及设原料基地不等于公司农业生产收入；2014—2015单列原枣类按扩展初加工纳入，后续混合红枣类别不能拆分。"
            cost_note = (
                f"{dates_label}对应成本{D(dates_cost_s):.2f}；其他业务成本{D(unknown_cost_s):.2f}，仅作反向核对"
                if dates_cost_s else f"{dates_label}未取得同口径销售成本；其他业务成本{D(unknown_cost_s):.2f}，不以成本倒推收入"
            )

        assert D("0") <= strict_lo <= strict_hi <= total
        assert D("0") <= expanded_lo <= expanded_hi <= total
        sr_lo, sr_hi = strict_lo / total, strict_hi / total
        er_lo, er_hi = expanded_lo / total, expanded_hi / total
        strict_result, expanded_result = threshold(sr_lo, sr_hi), threshold(er_lo, er_hi)
        boundary_result = "是" if code == "002650" and year >= 2015 else boundary(er_lo, er_hi)
        assert compact(total_s) in compact(src["利润表原文摘录"]) or "营业收入" in compact(src["利润表原文摘录"])

        strict_formal = f"{strict_lo:.2f}" if strict_lo == strict_hi else ""
        expanded_formal = f"{expanded_lo:.2f}" if expanded_lo == expanded_hi or expanded_result == "是" else ""
        rows.append({
            "股票代码": code,
            "公司全称": src["公司全称"],
            "年份": year,
            "行业分类代码": src["行业分类代码"] or "待核实",
            "行业分类名称": src["行业分类名称"] or "待核实",
            "严格口径涉农业务": strict_business,
            "严格口径正式涉农收入_元": strict_formal,
            "严格口径收入下界_元": f"{strict_lo:.2f}",
            "严格口径收入上界_元": f"{strict_hi:.2f}",
            "严格口径上下界公式": strict_formula,
            "严格口径下界占比_原始未四舍五入": ratio(strict_lo, total),
            "严格口径上界占比_原始未四舍五入": ratio(strict_hi, total),
            "扩展口径涉农业务": expanded_business,
            "扩展口径正式涉农收入_元": expanded_formal,
            "扩展口径收入下界_元": f"{expanded_lo:.2f}",
            "扩展口径收入上界_元": f"{expanded_hi:.2f}",
            "扩展口径上下界公式": expanded_formula,
            "扩展口径下界占比_原始未四舍五入": ratio(expanded_lo, total),
            "扩展口径上界占比_原始未四舍五入": ratio(expanded_hi, total),
            "公司营业收入_元": f"{total:.2f}",
            "公司营业收入公式": "合并利润表营业收入",
            "直接农业收入_元": f"{direct:.2f}",
            "确认初加工收入_元": f"{initial:.2f}",
            "直接农业成本_元_反向证据": f"{D(direct_cost_s):.2f}" if direct_cost_s else "",
            "确认初加工成本_元_反向证据": f"{D(initial_cost_s):.2f}" if initial_cost_s else "",
            "食用植物油混合大类收入_元_扩展上界": f"{oil:.2f}" if code == "002650" and year >= 2015 else "",
            "食用植物油混合大类成本_元_反向证据": f"{D(oil_cost_s):.2f}" if code == "002650" and year >= 2015 else "",
            "食用植物油混合大类制造成本_元_反向证据": f"{D(oil_mfg_cost_s):.2f}" if code == "002650" and year >= 2015 else "",
            "未拆其他营业收入上界增量_元": f"{unknown:.2f}",
            "未拆其他营业成本_元_反向证据": f"{D(unknown_cost_s):.2f}" if unknown_cost_s else "",
            "未拆其他制造成本_元_反向证据": f"{D(other_mfg_cost_s):.2f}" if code == "002650" else "",
            "深加工或混合类别": deep_label,
            "深加工或混合类别收入_元_反向证据": f"{deep:.2f}",
            "深加工或混合类别成本_元_反向证据": f"{deep_cost:.2f}" if deep_cost else "",
            "收入成本判别": cost_note,
            "严格样本结论": strict_result,
            "扩展样本结论": expanded_result,
            "边界样本结论": boundary_result,
            "是否存在分部收入重叠": overlap,
            "纳入或剔除理由": reason,
            "待核实点": pending,
            "年报主营业务证据PDF页序号": src["年报主营业务候选PDF页序号"],
            "公司营业收入证据PDF页序号": src["利润表PDF页序号"],
            "年报链接": src["年报链接"],
            "2022行业字段处理": "沿用v26原值；待核实字段不插值、不复制相邻年份",
            "记录类型": "跨年快速复核第十六批P组（未合并）",
            "复核状态": "已人工复核（第十六批P组；主表未合并）",
            "复核日期": "2026-08-11",
        })

    out = pd.DataFrame(rows)
    assert len(out) == 21 and not out.duplicated(["股票代码", "年份"]).any()
    assert out["严格样本结论"].value_counts().to_dict() == {"否": 17, "待核实": 4}
    assert out["扩展样本结论"].value_counts().to_dict() == {"否": 17, "是": 2, "待核实": 2}
    assert out["边界样本结论"].value_counts().to_dict() == {"否": 13, "是": 6, "待核实": 2}
    sq14 = out[(out["股票代码"] == "002216") & (out["年份"] == 2014)].iloc[0]
    assert (sq14["严格口径收入下界_元"], sq14["严格口径收入上界_元"]) == ("3589224.40", "14854424.14")
    hx = out[out["股票代码"] == "002582"].set_index("年份")
    assert hx.loc[2014, "严格样本结论"] == "待核实" and hx.loc[2015, "严格样本结论"] == "待核实"
    assert hx.loc[2018, "严格样本结论"] == "否" and hx.loc[2020, "严格样本结论"] == "否"
    assert hx.loc[2021, "严格样本结论"] == "待核实" and hx.loc[2022, "严格样本结论"] == "待核实"
    assert hx.loc[2014, "扩展样本结论"] == "是" and hx.loc[2015, "扩展样本结论"] == "是"
    assert hx.loc[2021, "扩展样本结论"] == "待核实" and hx.loc[2022, "扩展样本结论"] == "待核实"
    jj = out[out["股票代码"] == "002650"].set_index("年份")
    assert jj.loc[2014, "边界样本结论"] == "否"
    assert jj.loc[[2015, 2018, 2019, 2020, 2021, 2022], "边界样本结论"].eq("是").all()
    assert out.loc[out["年份"].eq(2022), "行业分类代码"].eq("待核实").all()
    assert out.loc[out["年份"].eq(2022), "行业分类名称"].eq("待核实").all()
    assert out["年报链接"].str.startswith("https://static.cninfo.com.cn/").all()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("batch16-P rows=21; strict no=17/pending=4; expanded no=17/yes=2/pending=2; boundary no=13/yes=6/pending=2; not merged")


if __name__ == "__main__":
    main()
