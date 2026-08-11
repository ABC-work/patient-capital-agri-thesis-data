#!/usr/bin/env python3
"""Build standalone historical fast-review batch 17-Q from fixed v26.

Direct forestry/timber and separately disclosed nursery-seedling sales may enter
the strict numerator. Flooring, wood-based panels, furniture, landscape works,
design and real-estate/ecocity operations are excluded. Mixed merchandise or
seedling-and-material sales are upper bounds only; dimensions are never added.
"""
from decimal import Decimal, getcontext
from pathlib import Path

import pandas as pd


getcontext().prec = 60
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v26_跨年快速复核第十五批第二组.csv"
OUTPUT = ROOT / "outputs" / "跨年快速复核第十七批_Q组_3家公司.csv"

# total revenue, timber revenue/cost, supplementary direct-agriculture
# revenue/cost, and excluded panel/furniture revenue/cost.  Blank cost means
# that the annual report does not disclose a complete matching amount.
YONGAN = {
    2013: ("458931928.46", "69070973.90", "43021094.79", "72844.00", "34881.80", "358145423.13", "329696177.77", "金线莲"),
    2014: ("460006220.23", "75972921.95", "44325747.05", "69125.00", "", "355941388.53", "317878112.33", "金线莲"),
    2015: ("891661313.21", "64841490.95", "", "103312.00", "", "790635071.61", "608963656.98", "金线莲"),
    2018: ("754832074.55", "22961641.31", "31611460.87", "39144.00", "371019.68", "678977462.70", "622277500.08", "育肥羊、金线莲"),
    2019: ("702153143.62", "29938153.76", "30410970.64", "162860.00", "518793.81", "623192688.63", "511114453.55", "育肥羊、金线莲"),
}

# total revenue, excluded wood-processing revenue/cost, and undisaggregated
# other-business revenue/cost.  The latter is only a conservative upper bound.
DAYA = {
    2018: ("7261283057.12", "7216553906.59", "4611709556.70", "44729150.53", "5252783.52"),
    2019: ("7298011526.88", "7258754745.08", "4639829223.39", "39256781.80", "18524696.62"),
    2020: ("7264129590.32", "7221539455.64", "5109180205.17", "42590134.68", "16066825.23"),
    2021: ("8750523660.19", "8704046246.06", "6462368973.70", "46477414.13", "8464463.29"),
    2022: ("7362968357.85", "7317222702.89", "5557839092.82", "45745654.96", "28027105.33"),
}

# total revenue, separately presented seedling/merchandise revenue and cost,
# and whether the revenue label is sufficiently specific for formal inclusion.
PALM = {
    2014: ("5006942897.83", "119807509.35", "72613060.83", True, "苗木销售收入"),
    2015: ("4400507524.27", "363732227.95", "188816365.28", True, "商品销售（苗木）"),
    2018: ("5328805898.65", "59450622.80", "51991817.80", True, "苗木销售"),
    2019: ("2708825167.13", "7291222.78", "6385515.40", True, "苗木销售"),
    2020: ("4821153800.69", "21451001.89", "8091719.98", False, "商品销售"),
    2021: ("4045893458.39", "18632851.94", "8113252.72", False, "苗木绿化及材料销售"),
    2022: ("4244865320.81", "48242871.32", "45792292.00", False, "苗木及零星材料销售"),
}


def D(value: str) -> Decimal:
    return Decimal(value)


def ratio(numerator: Decimal, denominator: Decimal) -> str:
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
        source["股票代码"].isin(["000663", "000910", "002431"])
        & source["复核状态"].str.startswith("年报及业务表已定位", na=False)
    ].sort_values(["股票代码", "年份"])
    assert len(source) == 958 and len(selected) == 17
    assert selected.groupby("股票代码").size().to_dict() == {"000663": 5, "000910": 5, "002431": 7}
    assert not selected.duplicated(["股票代码", "年份"]).any()

    rows = []
    for _, src in selected.iterrows():
        code, year = src["股票代码"], int(src["年份"])
        direct = D("0")
        direct_cost_s = ""
        mixed = D("0")
        mixed_cost_s = ""
        deep = D("0")
        deep_cost_s = ""
        timber = D("0")
        supplementary_direct = D("0")
        supplementary_direct_cost_s = ""
        supplementary_direct_label = ""

        if code == "000663":
            (total_s, timber_s, timber_cost_s, supplementary_direct_s,
             supplementary_direct_cost_s, deep_s, deep_cost_s,
             supplementary_direct_label) = YONGAN[year]
            total, timber = D(total_s), D(timber_s)
            supplementary_direct = D(supplementary_direct_s)
            direct = timber + supplementary_direct
            direct_cost_s = (
                f"{D(timber_cost_s) + D(supplementary_direct_cost_s):.2f}"
                if timber_cost_s and supplementary_direct_cost_s else timber_cost_s
            )
            deep = D(deep_s)
            strict_lo = strict_hi = expanded_lo = expanded_hi = direct
            strict_business = f"林业/木材及{supplementary_direct_label}（直接农业）"
            expanded_business = "同严格口径；木材二次加工产品、家具不纳入"
            strict_formula = expanded_formula = (
                f"木材收入{timber:.2f}+{supplementary_direct_label}收入"
                f"{supplementary_direct:.2f}={direct:.2f}"
            )
            deep_label = "木材二次加工产品、人造板、家具、甲醛、胶粘剂及装饰设计"
            overlap = "采用合并口径产品和劳务对外交易收入；产品维度不与行业维度相加，内部供料不另计"
            reason = "单列木材及金线莲/育肥羊属于直接农业，可进入严格口径；板材、家具等属于深加工。直接农业收入占比不足30%。"
            if year == 2015:
                pending = "2015年木材及金线莲未取得同口径单列成本；不影响以收入计算的样本结论。"
            elif year == 2014:
                pending = "2014年金线莲成本未单列；已披露木材成本仅作不完整反向证据，不影响收入结论。"
            else:
                pending = "无影响结论的待核实项。"
            if direct_cost_s:
                completeness = "已知合计" if supplementary_direct_cost_s else "已披露木材部分"
                cost_note = f"直接农业成本{completeness}{D(direct_cost_s):.2f}，只作反向核对，不以成本比例倒推收入"
            else:
                cost_note = "年报未单列完整同口径直接农业成本；不以成本比例倒推收入"
            cost_note += f"；板材/家具等排除收入{deep:.2f}、成本{D(deep_cost_s):.2f}"
            evidence_extra = "2019年报财务附注PDF第208页同时列示2019年木材成本30,410,970.64元及2018年31,611,460.87元" if year in (2018, 2019) else "管理层主营业务表"
        elif code == "000910":
            total_s, deep_s, deep_cost_s, mixed_s, mixed_cost_s = DAYA[year]
            total, deep = D(total_s), D(deep_s)
            mixed = D(mixed_s)
            strict_lo = expanded_lo = D("0")
            strict_hi = expanded_hi = mixed
            strict_business = "未单列公司自营林木种植、采伐或其他直接农业收入"
            expanded_business = "未单列农产品初加工、农业投入品或农业生产性服务收入"
            strict_formula = expanded_formula = f"下界=0；上界=未拆其他/其他业务收入{mixed:.2f}"
            deep_label = "木地板、中高密度板、木门及衣帽间、竹/石塑地板等装饰材料"
            overlap = "行业与产品维度不相加；原材料采购、绿色产业链及品牌称号不形成农业收入"
            reason = "主营业务为人造板和木地板生产销售，属于木材深加工；其他业务未拆分，故直接农业收入下界为0、以其他业务全额作为保守上界，仍不足30%。"
            pending = "其他/其他业务收入未拆出可能的林木销售，不估算；2022行业分类字段仍按v26保留待核实。" if year == 2022 else "其他/其他业务收入未拆出可能的林木销售，不估算。"
            cost_note = f"装饰材料业收入{deep:.2f}、成本{D(deep_cost_s):.2f}；其他业务收入{mixed:.2f}、成本{D(mixed_cost_s):.2f}均已核对，成本不用于倒推收入"
            evidence_extra = "合并子公司大亚饰面板（江苏）经营范围含人造板销售、林业种植；合并存货披露消耗性生物资产—林木约156,157,411.40元，但未单列对外林木销售。30%联营企业大亚（江西）林业收入不归入上市公司合并营业收入。"
        else:
            total_s, mixed_s, mixed_cost_s, separable, label = PALM[year]
            total, mixed = D(total_s), D(mixed_s)
            if separable:
                direct = mixed
                direct_cost_s = mixed_cost_s
                strict_lo = strict_hi = expanded_lo = expanded_hi = direct
                formal_note = "单列苗木销售可确认"
            else:
                strict_lo = expanded_lo = D("0")
                strict_hi = expanded_hi = mixed
                formal_note = "混合商品/材料收入不能整体确认，只作上界"
            strict_business = f"{label}（{formal_note}）"
            expanded_business = f"同严格口径；园林工程、景观设计、生态城镇/地产不作为农业生产性服务"
            if separable:
                strict_formula = expanded_formula = f"单列{label}{mixed:.2f}"
            else:
                strict_formula = expanded_formula = f"下界=0；上界={label}{mixed:.2f}"
            deep_label = "园林工程、景观设计、生态城镇/地产及未单列农业属性的其他业务"
            overlap = "只使用合并口径外部销售；苗木用于园林项目形成的内部供料不另计，产品与行业维度不相加"
            reason = "仅单列苗木外销可作为直接林业；园林施工、设计和地产并非农业生产性服务。即使将混合商品/材料销售全作上界，占比仍低于30%。"
            pending = (
                "无影响结论的待核实项。"
                if separable else f"{label}未拆苗木与其他材料，不能可靠拆分；不估算，只保留0至{mixed:.2f}元上下界。"
            )
            cost_note = f"{label}对应/汇总成本{D(mixed_cost_s):.2f}，只作反向证据，不按成本比例拆分收入"
            evidence_extra = "2021年收入附注称“苗木绿化及材料销售”；2022年称“苗木及零星材料销售”，成本表亦显示材料混合" if year in (2021, 2022) else "管理层收入构成、成本构成及苗圃苗木销售收入确认政策"

        assert D("0") <= strict_lo <= strict_hi <= total
        assert D("0") <= expanded_lo <= expanded_hi <= total
        sr_lo, sr_hi = strict_lo / total, strict_hi / total
        er_lo, er_hi = expanded_lo / total, expanded_hi / total
        strict_result, expanded_result = threshold(sr_lo, sr_hi), threshold(er_lo, er_hi)
        boundary_result = boundary(er_lo, er_hi)
        assert (
            compact(total_s) in compact(src["利润表原文摘录"])
            or compact(total_s) in compact(src["主营业务表原文摘录"])
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
            "直接林业或苗木收入_元": f"{direct:.2f}" if direct else "",
            "直接林业或苗木成本_元_反向证据": f"{D(direct_cost_s):.2f}" if direct_cost_s else "",
            "其中木材收入_元": f"{timber:.2f}" if timber else "",
            "其中金线莲或育肥羊收入_元": f"{supplementary_direct:.2f}" if supplementary_direct else "",
            "金线莲或育肥羊成本_元_反向证据": f"{D(supplementary_direct_cost_s):.2f}" if supplementary_direct_cost_s else "",
            "混合商品或材料销售收入_元_上界": f"{mixed:.2f}" if mixed and not direct else "",
            "混合商品或材料销售成本_元_反向证据": f"{D(mixed_cost_s):.2f}" if mixed and not direct else "",
            "深加工或排除类别": deep_label,
            "深加工类别收入_元_反向证据": f"{deep:.2f}" if deep else "",
            "深加工类别成本_元_反向证据": f"{D(deep_cost_s):.2f}" if deep_cost_s else "",
            "收入成本判别": cost_note,
            "严格样本结论": strict_result,
            "扩展样本结论": expanded_result,
            "边界样本结论": boundary_result,
            "是否存在分部收入重叠": overlap,
            "纳入或剔除理由": reason,
            "待核实点": pending,
            "年报主营业务证据PDF页序号": src["年报主营业务候选PDF页序号"],
            "公司营业收入证据PDF页序号": src["利润表PDF页序号"],
            "补充证据说明": evidence_extra,
            "年报链接": src["年报链接"],
            "2022行业字段处理": "沿用v26原值；待核实字段不插值、不复制相邻年份",
            "记录类型": "跨年快速复核第十七批Q组（未合并）",
            "复核状态": "已人工复核（第十七批Q组；主表未合并）",
            "复核日期": "2026-08-11",
        })

    out = pd.DataFrame(rows)
    assert len(out) == 17 and not out.duplicated(["股票代码", "年份"]).any()
    assert out["严格样本结论"].value_counts().to_dict() == {"否": 17}
    assert out["扩展样本结论"].value_counts().to_dict() == {"否": 17}
    assert out["边界样本结论"].value_counts().to_dict() == {"否": 17}
    yongan = out[out["股票代码"] == "000663"].set_index("年份")
    assert yongan["严格口径正式涉农收入_元"].to_dict() == {
        2013: "69143817.90", 2014: "76042046.95", 2015: "64944802.95",
        2018: "23000785.31", 2019: "30101013.76",
    }
    assert yongan["深加工类别收入_元_反向证据"].to_dict() == {
        2013: "358145423.13", 2014: "355941388.53", 2015: "790635071.61",
        2018: "678977462.70", 2019: "623192688.63",
    }
    assert yongan.loc[2013, "直接林业或苗木成本_元_反向证据"] == "43055976.59"
    assert yongan.loc[2014, "直接林业或苗木成本_元_反向证据"] == "44325747.05"
    assert yongan.loc[2015, "直接林业或苗木成本_元_反向证据"] == ""
    assert yongan.loc[2018, "直接林业或苗木成本_元_反向证据"] == "31982480.55"
    assert yongan.loc[2019, "直接林业或苗木成本_元_反向证据"] == "30929764.45"
    daya = out[out["股票代码"] == "000910"].set_index("年份")
    assert daya["严格口径正式涉农收入_元"].eq("").all()
    assert daya["严格口径收入下界_元"].eq("0.00").all()
    assert daya["严格口径收入上界_元"].to_dict() == {
        2018: "44729150.53", 2019: "39256781.80", 2020: "42590134.68",
        2021: "46477414.13", 2022: "45745654.96",
    }
    assert (daya["严格口径上界占比_原始未四舍五入"].map(D) < D("0.01")).all()
    palm = out[out["股票代码"] == "002431"].set_index("年份")
    assert palm.loc[[2014, 2015, 2018, 2019], "严格口径正式涉农收入_元"].ne("").all()
    assert palm.loc[[2020, 2021, 2022], "严格口径正式涉农收入_元"].eq("").all()
    assert palm.loc[2022, "公司营业收入_元"] == "4244865320.81"
    assert palm.loc[2022, "混合商品或材料销售收入_元_上界"] == "48242871.32"
    assert palm.loc[2022, "混合商品或材料销售成本_元_反向证据"] == "45792292.00"
    daya22 = daya.loc[2022]
    assert daya22["公司营业收入_元"] == "7362968357.85"
    assert daya22["深加工类别收入_元_反向证据"] == "7317222702.89"
    assert daya22["深加工类别成本_元_反向证据"] == "5557839092.82"
    assert out.loc[out["年份"].eq(2022), "行业分类代码"].eq("待核实").all()
    assert out.loc[out["年份"].eq(2022), "行业分类名称"].eq("待核实").all()
    assert out["年报链接"].str.startswith("https://static.cninfo.com.cn/").all()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("batch17-Q rows=17; strict no=17; expanded no=17; boundary no=17; not merged")


if __name__ == "__main__":
    main()
