#!/usr/bin/env python3
"""Build standalone historical fast-review batch 19-U from fixed v30.

Separately disclosed grape planting/fresh-grape or external raw-milk revenue may
enter the strict scope; primary dairy processing may enter the expanded scope.
Wine, fermented/flavoured dairy drinks and walnut/other beverages are deep
processing. Mixed dairy and mixed planting/wine disclosures use bounds. Costs
are reverse evidence only and are never used to infer revenue shares.
"""
from decimal import Decimal, getcontext
from pathlib import Path

import pandas as pd


getcontext().prec = 60
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v30_跨年快速复核第十八批.csv"
OUTPUT = ROOT / "outputs" / "跨年快速复核第十九批_U组_4家公司.csv"

# total; mixed dairy/food or mixed low+ambient milk revenue/cost
HUANGSHI = {
    2018: ("2335911679.89", "1360646585.37", "948135781.10"),
    2019: ("2253248315.76", "1520328824.94", "1074110783.08"),
    2020: ("2490168717.50", "1621310412.60", "1243839833.70"),
    2021: ("2568690730.34", "2012603645.29", "1573311242.27"),
    2022: ("2890700549.88", "2288864463.02", "1843335048.82"),
}

# total; mixed dairy revenue/cost
MAIQUER = {
    2018: ("600205244.59", "250412110.13", "169469120.63"),
    2019: ("670570447.53", "254251762.59", "191338484.13"),
    2020: ("875419375.06", "464595420.58", "380653524.34"),
    2021: ("1146225734.85", "732920146.59", "623936889.12"),
    2022: ("989090050.01", "549444647.73", "517365029.06"),
}

# total; confirmed deep beverage main business revenue/cost; audited other
# business revenue/cost, used only as an upper bound.
YANGYUAN = {
    2018: ("8144243871.80", "8141895842.39", "4075013891.63", "2348029.41", "0.00"),
    2019: ("7459290694.08", "7456262260.74", "3518020399.21", "3028433.34", "209115.43"),
    2020: ("4427115659.46", "4424772214.09", "2309625171.90", "2343445.37", "342349.16"),
    # 2021 cost uses the product-level comparative figure restated in the 2022 report.
    2021: ("6905959247.09", "6901200433.58", "3545171630.69", "4758813.51", "59327.04"),
    2022: ("5922826767.82", "5918729399.85", "3250718732.60", "4097367.97", "426478.33"),
}

# total; strict confirmed fresh-grape revenue/cost; mixed planting/wine revenue
# and cost for 2014-15 only; wine revenue/cost; audited other business.
MOGAO = {
    2014: ("325173689.10", "0.00", "0.00", "207094660.23", "83562143.87", "0.00", "0.00", "1221583.01", "835461.98"),
    2015: ("248647980.92", "0.00", "0.00", "207237556.18", "83972366.49", "0.00", "0.00", "1517227.33", "286218.50"),
    2018: ("231083125.02", "2910000.00", "2667500.00", "0.00", "0.00", "186291785.58", "61762784.42", "9096889.90", "187912.07"),
    2019: ("177268383.93", "3061002.20", "243438.50", "0.00", "0.00", "120654730.10", "24370885.93", "8903198.15", "1491896.64"),
    2020: ("133039355.94", "2793220.00", "2557500.00", "0.00", "0.00", "76116098.54", "18179727.80", "7608499.50", "346211.23"),
    2021: ("140401040.26", "0.00", "0.00", "0.00", "0.00", "48271996.96", "14578583.26", "14088522.18", "1979155.85"),
    2022: ("108314975.35", "0.00", "0.00", "0.00", "0.00", "37196426.16", "20394293.50", "15841148.93", "1224192.16"),
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


def profit_pages(code: str, year: int, original: str) -> str:
    """Correct locators where revenue and cost fall on adjacent PDF pages."""
    return {
        ("002329", 2021): "98",
        ("002329", 2022): "102|103",
        ("002719", 2020): "72|73",
        ("600543", 2019): "53|54",
        ("603156", 2020): "73|74",
    }.get((code, year), original)


def main() -> None:
    source = pd.read_csv(SOURCE, dtype={"股票代码": str}, keep_default_na=False)
    selected = source[
        source["股票代码"].isin(["600543", "002329", "002719", "603156"])
        & source["复核状态"].str.startswith("年报及业务表已定位", na=False)
    ].sort_values(["股票代码", "年份"])
    assert len(source) == 958 and len(selected) == 22
    assert selected.groupby("股票代码").size().to_dict() == {"002329": 5, "002719": 5, "600543": 7, "603156": 5}
    assert not selected.duplicated(["股票代码", "年份"]).any()

    rows = []
    for _, src in selected.iterrows():
        code, year = src["股票代码"], int(src["年份"])
        eligible_revenue = eligible_cost = mixed_revenue = mixed_cost = D("0")
        deep_revenue = deep_cost = other_revenue = other_cost = D("0")

        if code == "600543":
            values = map(D, MOGAO[year])
            total, eligible_revenue, eligible_cost, mixed_revenue, mixed_cost, deep_revenue, deep_cost, other_revenue, other_cost = values
            if year in (2014, 2015):
                strict_lo = expanded_lo = D("0")
                strict_hi = expanded_hi = mixed_revenue + other_revenue
                strict_business = "葡萄种植与葡萄酒合并披露；未拆农业种植收入及其他业务只作严格上界"
                expanded_business = "葡萄种植与葡萄酒加工合并披露；未拆项目只作扩展上界"
                strict_formula = expanded_formula = (
                    f"下界=0；上界=农业种植及加工混合收入{mixed_revenue:.2f}+审计其他业务{other_revenue:.2f}={strict_hi:.2f}"
                )
                reason = "农业种植及加工品混合了可纳入的葡萄种植与应排除的葡萄酒，不能整体纳入或按成本估算。"
                pending = "葡萄种植外销与葡萄酒收入未拆；上下界跨越50%。"
            else:
                strict_lo = expanded_lo = eligible_revenue
                strict_hi = expanded_hi = eligible_revenue + other_revenue
                strict_business = "鲜食葡萄外销按行业与葡萄酒产品互斥差额确认；审计其他业务只作上界"
                expanded_business = "鲜食葡萄外销同时纳入扩展口径；未拆其他业务只作上界"
                strict_formula = expanded_formula = (
                    f"下界=鲜食葡萄外销{eligible_revenue:.2f}；上界=下界+审计其他业务{other_revenue:.2f}={strict_hi:.2f}"
                )
                reason = "葡萄酒、药品和降解材料排除；仅确认可由互斥披露识别的鲜食葡萄外销，其他业务不估算。"
                pending = "审计其他业务未拆，只作上界；上下界均低于30%。"
            deep_label = "葡萄酒（金额字段仅列可分离的葡萄酒）；药品、环保材料等非农业类别另行排除"
            overlap = "农业种植及加工品为行业维度，葡萄酒为产品维度；2018—2020仅取二者差额识别鲜食葡萄，不重复相加；其他业务为互斥收入层级"
            cost_note = (
                f"可确认鲜食葡萄对应成本差额{eligible_cost:.2f}；混合种植/加工成本{mixed_cost:.2f}；"
                f"葡萄酒成本{deep_cost:.2f}；其他业务成本{other_cost:.2f}，成本仅作反向核对"
            )
            evidence_extra = "2018—2020年报说明农业种植及加工业务含葡萄酒和鲜食葡萄；行业收入减葡萄酒产品收入形成鲜食葡萄外销差额；2021—2022二者相等"
        elif code == "002329":
            total, mixed_revenue, mixed_cost = map(D, HUANGSHI[year])
            strict_lo = strict_hi = expanded_lo = D("0")
            expanded_hi = mixed_revenue
            milk_label = "乳制品、食品" if year in (2018, 2019) else "低温奶与常温奶"
            strict_business = "未单列合并口径外销原奶收入；内部原奶不重复计入"
            expanded_business = f"基础乳品与调制乳、发酵乳等深加工未拆；{milk_label}仅作扩展上界"
            strict_formula = "下界=上界=0（无单列合并口径外销原奶收入）"
            expanded_formula = f"下界=0；上界=未拆{milk_label}{mixed_revenue:.2f}"
            deep_label = "调制乳、发酵乳、含乳饮料、植物蛋白饮料及其他食品；混合乳品另作上界"
            overlap = "低温奶、常温奶为互斥产品项目，可相加；不叠加乳制品行业、地区、销售模式或其他业务维度"
            reason = "公司具有牧草种植、奶牛养殖和乳品加工全产业链，但未单列外销原奶；乳品项目混含可扩展的基础乳品与应排除深加工品。"
            pending = "严格口径已判否；基础乳品与调制/发酵乳收入未拆，扩展口径上下界跨越50%。"
            cost_note = f"{milk_label}成本{mixed_cost:.2f}仅作混合类别反向证据，不按成本比例推算收入"
            evidence_extra = "2020—2022低温奶含巴氏杀菌乳、巴氏调制乳和发酵乳，常温奶含灭菌乳和调制乳；2018—2019仅披露乳制品、食品合计"
        elif code == "002719":
            total, mixed_revenue, mixed_cost = map(D, MAIQUER[year])
            strict_lo = strict_hi = expanded_lo = D("0")
            expanded_hi = mixed_revenue
            strict_business = "未单列合并口径外销原奶收入；内部原奶不重复计入"
            expanded_business = "灭菌乳等基础乳品与调制乳、含乳饮料、发酵乳混合披露，仅作扩展上界"
            strict_formula = "下界=上界=0（无单列合并口径外销原奶收入）"
            expanded_formula = f"下界=0；上界=未拆乳制品收入{mixed_revenue:.2f}"
            deep_label = "调制乳、含乳饮料、发酵乳、烘焙及节日食品；乳制品混合项目另作上界"
            overlap = "乳制品为产品维度互斥项目；不叠加食品制造业、地区、销售模式或审计其他业务"
            reason = "奶牛养殖与生鲜乳生产线不替代外销收入；乳制品同时含可扩展基础乳品和应排除深加工品，不能整体纳入。"
            pending = "严格口径已判否；乳制品内部品类收入未拆，不以采购额、产能或成本估算。"
            cost_note = f"乳制品成本{mixed_cost:.2f}只作混合类别反向证据，不按成本比例推算收入"
            evidence_extra = "年报明确乳制品包括灭菌乳、调制乳、含乳饮料和发酵乳；生鲜乳采购额和生产线建设金额不属于外销收入"
        else:
            total, deep_revenue, deep_cost, other_revenue, other_cost = map(D, YANGYUAN[year])
            strict_lo = expanded_lo = D("0")
            strict_hi = expanded_hi = other_revenue
            strict_business = "未单列核桃种植或农业投入品收入；审计其他业务仅作严格上界"
            expanded_business = "未单列初加工或农业投入品收入；审计其他业务仅作扩展上界"
            strict_formula = expanded_formula = f"下界=0；上界=审计其他业务{other_revenue:.2f}"
            deep_label = "核桃乳、其他植物蛋白饮料、功能性饮料等深加工饮料"
            overlap = "饮料主营业务明确排除；其他业务为互斥收入层级，只作上界，不叠加产品、地区或销售模式"
            reason = "核桃乳及植物饮料经过研磨、调配等多道工序，属于深加工；未披露可确认的种植、初加工或农业投入品收入。"
            pending = "审计其他业务未拆具体性质，只作上界；上界远低于30%。"
            cost_note = f"深加工饮料主营成本{deep_cost:.2f}为排除证据；其他业务成本{other_cost:.2f}仅作上界反向证据"
            evidence_extra = "2021成本采用2022年报追溯重述口径；2022年报提供上年同期产品/成本构成比较数，深加工主营成本3545171630.69，其他业务59327.04，合计3545230957.73；较2021原报增加31220097.23。收入及样本结论不受影响" if year == 2021 else "主营产品均为饮料深加工；采购核桃仁不等于农业生产收入"

        assert D("0") <= strict_lo <= strict_hi <= total
        assert D("0") <= expanded_lo <= expanded_hi <= total
        sr_lo, sr_hi = strict_lo / total, strict_hi / total
        er_lo, er_hi = expanded_lo / total, expanded_hi / total
        assert compact(f"{total:.2f}") in compact(src["利润表原文摘录"] + src["主营业务表原文摘录"])

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
            "可确认种植或原奶外销收入_元": f"{eligible_revenue:.2f}" if eligible_revenue else "",
            "可确认种植或原奶外销成本_元_反向证据": f"{eligible_cost:.2f}" if eligible_cost else "",
            "混合种植或乳品收入_元_上界": f"{mixed_revenue:.2f}" if mixed_revenue else "",
            "混合种植或乳品成本_元_反向证据": f"{mixed_cost:.2f}" if mixed_cost else "",
            "审计其他业务收入_元_上界": f"{other_revenue:.2f}" if other_revenue else "",
            "审计其他业务成本_元_反向证据": f"{other_cost:.2f}" if other_revenue else "",
            "深加工或排除类别": deep_label,
            "深加工类别收入_元_反向证据": f"{deep_revenue:.2f}" if deep_revenue else "",
            "深加工类别成本_元_反向证据": f"{deep_cost:.2f}" if deep_revenue else "",
            "收入成本判别": cost_note,
            "严格样本结论": threshold(sr_lo, sr_hi),
            "扩展样本结论": threshold(er_lo, er_hi),
            "边界样本结论": boundary(er_lo, er_hi),
            "是否存在分部收入重叠": overlap,
            "纳入或剔除理由": reason,
            "待核实点": pending + ("2022行业分类字段仍待核实。" if year == 2022 else ""),
            "年报主营业务证据PDF页序号": src["年报主营业务候选PDF页序号"],
            "公司营业收入证据PDF页序号": profit_pages(code, year, src["利润表PDF页序号"]),
            "补充证据说明": evidence_extra,
            "年报链接": src["年报链接"],
            "2022行业字段处理": "沿用v30原值；待核实字段不插值、不复制相邻年份",
            "记录类型": "跨年快速复核第十九批U组（未合并）",
            "复核状态": "已人工复核（第十九批U组；主表未合并）",
            "复核日期": "2026-08-11",
        })

    out = pd.DataFrame(rows)
    assert len(out) == 22 and not out.duplicated(["股票代码", "年份"]).any()
    assert out["严格样本结论"].value_counts().to_dict() == {"否": 20, "待核实": 2}
    assert out["扩展样本结论"].value_counts().to_dict() == {"待核实": 10, "否": 12}
    assert out["边界样本结论"].value_counts().to_dict() == {"待核实": 12, "否": 10}
    mogao18 = out[(out["股票代码"] == "600543") & (out["年份"] == 2018)].iloc[0]
    assert mogao18["可确认种植或原奶外销收入_元"] == "2910000.00"
    assert mogao18["严格样本结论"] == "否"
    hs22 = out[(out["股票代码"] == "002329") & (out["年份"] == 2022)].iloc[0]
    assert hs22["混合种植或乳品收入_元_上界"] == "2288864463.02"
    mq22 = out[(out["股票代码"] == "002719") & (out["年份"] == 2022)].iloc[0]
    assert mq22["混合种植或乳品成本_元_反向证据"] == "517365029.06"
    yy22 = out[(out["股票代码"] == "603156") & (out["年份"] == 2022)].iloc[0]
    assert yy22["深加工类别收入_元_反向证据"] == "5918729399.85"
    yy21 = out[(out["股票代码"] == "603156") & (out["年份"] == 2021)].iloc[0]
    assert yy21["深加工类别成本_元_反向证据"] == "3545171630.69"
    assert out.loc[out["年份"].eq(2022), "行业分类代码"].eq("待核实").all()
    assert out.loc[out["年份"].eq(2022), "行业分类名称"].eq("待核实").all()
    assert out["年报链接"].str.startswith("https://static.cninfo.com.cn/").all()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("batch19-U rows=22; strict pending=2/no=20; expanded pending=10/no=12; not merged")


if __name__ == "__main__":
    main()
