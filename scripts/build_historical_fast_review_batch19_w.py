#!/usr/bin/env python3
"""Build standalone historical fast-review batch 19-W from fixed v30.

Frozen prepared food, supermarket retailing, refined packaged edible oil and
liquor are processing/non-production activities and are excluded.  Only
separately disclosed direct agriculture, oilseed-crushing primary processing
or agricultural-input revenue enters a lower bound.  Generic/unclassified
revenue is upper-bound evidence only; names and procurement never substitute
for disclosed revenue.  Costs are reverse evidence and never numerators.
"""
from decimal import Decimal, getcontext
from pathlib import Path

import pandas as pd


getcontext().prec = 60
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v30_跨年快速复核第十八批.csv"
OUTPUT = ROOT / "outputs" / "跨年快速复核第十九批_W组_4家公司.csv"

# Total revenue/cost; generic farm-product or other-business upper-bound
# revenue/cost.  From 2021 the generic "农副产品" line is included only in
# the upper bound: its name does not establish direct agricultural production.
ANJING = {
    2018: ("4259090161.02", "3129917104.83", "3228204.15", "3165624.00"),
    2019: ("5266663002.38", "3909785513.94", "8233468.32", "6951235.86"),
    2020: ("6965114987.25", "5176465007.55", "7119446.74", "4255702.52"),
    2021: ("9272201669.79", "7221274324.12", "166152216.46", "135796406.37"),
    2022: ("12182663119.36", "9507716843.77", "404222676.06", "292562332.35"),
}

# Total revenue/cost; commercial retail revenue/cost.  The residual (including
# "工业及其他" and revenue outside the commercial main-business table) is an
# upper bound only.  Retail sales of fresh goods are excluded, not agriculture.
JIAYUE = {
    2018: ("12730711830.05", "9958622005.98", "11822775686.65", "9763746417.10"),
    2019: ("15263757862.93", "11929238208.08", "14180299233.88", "11689426442.99"),
    2020: ("16678468932.04", "12762813149.31", "15380185833.69", "12428456530.13"),
    2021: ("17432792405.09", "13378244447.89", "16015267874.15", "13002845423.91"),
    2022: ("18183817809.52", "13955708440.43", "16722888269.71", "13553624466.07"),
}

# Total revenue/cost; oilseed meal revenue/cost; bulk-oil plus other-business
# upper-bound revenue/cost; refined packaged-oil revenue/cost.  Meal is an
# oilseed-crushing by-product used for feed and enters the expanded lower bound.
# Bulk oil is described as mainly traded oil and therefore enters only the
# upper bound.  For 2018-2019 its cost is available only as a combined residual
# with other business; no allocation is estimated.
DAODAOQUAN = {
    2018: ("3600495170.90", "3151052631.03", "626765351.70", "600675368.16", "305069452.58", "306804080.83", "2668660366.62", "2243573182.04"),
    2019: ("4116731900.76", "3738992685.78", "587813147.75", "576966492.46", "368516998.79", "351879360.45", "3160401754.22", "2810146832.87"),
    2020: ("5287320473.49", "4904841801.54", "684611149.35", "665172576.63", "461735069.01", "458724906.51", "4140974255.13", "3780944318.40"),
    2021: ("5449474451.72", "5360900797.84", "973524828.39", "1019383663.75", "513267438.47", "450602829.75", "3962682184.86", "3890914304.34"),
    2022: ("7028343032.62", "7114455106.40", "1398579768.79", "1496517455.27", "898287017.53", "872580658.97", "4731476246.30", "4745356992.16"),
}

# Total revenue/cost; explicitly disclosed "other revenue" and its cost
# residual after the mutually exclusive liquor line.  All liquor is excluded.
LUZHOU = {
    2018: ("13055465761.55", "2934001858.91", "195941935.99", "55007388.80", "12859523825.56", "2878994470.11"),
    2019: ("15816934272.86", "3065418048.38", "201215170.43", "90933686.25", "15615719102.43", "2974484362.13"),
    2020: ("16652854549.80", "2823484558.06", "204893980.58", "112050551.09", "16447960569.22", "2711434006.97"),
    2021: ("20642261724.37", "2952431488.31", "227091255.28", "66746336.68", "20415170469.09", "2885685151.63"),
    2022: ("25123563271.62", "3369528394.02", "357441273.13", "155274677.11", "24766121998.49", "3214253716.91"),
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


def profit_pages(code: str, year: int, original: str) -> str:
    """Return PDF sequence pages that actually contain the statement values."""
    fixes = {
        ("603345", 2018): "81",
        ("603708", 2018): "74",
        ("603708", 2020): "83",
        ("002852", 2019): "77",
        ("002852", 2020): "81",
        ("002852", 2021): "79",
        ("002852", 2022): "73",
    }
    return fixes.get((code, year), original)


def main() -> None:
    source = pd.read_csv(SOURCE, dtype={"股票代码": str}, keep_default_na=False)
    selected = source[
        source["股票代码"].isin(["603345", "603708", "002852", "000568"])
        & source["年份"].isin([2018, 2019, 2020, 2021, 2022])
    ].sort_values(["股票代码", "年份"])
    assert len(source) == 958 and len(selected) == 20
    assert selected.groupby("股票代码").size().to_dict() == {
        "000568": 5, "002852": 5, "603345": 5, "603708": 5
    }
    assert selected["复核状态"].str.startswith("年报及业务表已定位", na=False).all()
    assert not selected.duplicated(["股票代码", "年份"]).any()

    rows = []
    for _, src in selected.iterrows():
        code, year = src["股票代码"], int(src["年份"])
        included_revenue = included_cost = D("0")
        upper_revenue = upper_cost = D("0")
        excluded_revenue = excluded_cost = D("0")

        if code == "603345":
            total, total_cost, upper_revenue, upper_cost = map(D, ANJING[year])
            excluded_revenue, excluded_cost = total - upper_revenue, total_cost - upper_cost
            strict_lo = expanded_lo = D("0")
            strict_hi = expanded_hi = upper_revenue
            strict_cost_lo = expanded_cost_lo = D("0")
            strict_cost_hi = expanded_cost_hi = upper_cost
            upper_label = "其他/其他业务" if year <= 2020 else "名称笼统的农副产品+其他业务"
            strict_business = f"未单列直接农业收入；{upper_label}仅作上界"
            expanded_business = f"未单列可确认初加工或农业投入品收入；{upper_label}仅作上界"
            strict_formula = expanded_formula = f"下界=0；上界={upper_label}{upper_revenue:.2f}"
            excluded_label = "速冻面米、肉、鱼糜、菜肴及休闲食品等深加工产品"
            overlap = "使用同一产品维度；农副产品和其他业务与其余产品互斥，不叠加地区、渠道或采购金额"
            reason = "速冻食品属于食品深加工；“农副产品”名称及原料采购不能证明直接农业生产，未拆金额仅作上界。"
            pending = f"{upper_label}未拆直接农业、初加工与非涉农收入；上界低于30%。"
            extra = "2021—2022“农副产品”仅为产品行名称，未见可审计的直接农业或初加工收入拆分，故不进入下界"
        elif code == "603708":
            total, total_cost, commercial, commercial_cost = map(D, JIAYUE[year])
            upper_revenue, upper_cost = total - commercial, total_cost - commercial_cost
            excluded_revenue, excluded_cost = commercial, commercial_cost
            strict_lo = expanded_lo = D("0")
            strict_hi = expanded_hi = upper_revenue
            strict_cost_lo = expanded_cost_lo = D("0")
            strict_cost_hi = expanded_cost_hi = upper_cost
            upper_label = "工业及其他及商业主营表外未分类收入残差"
            strict_business = f"未单列直接农业生产收入；{upper_label}仅作上界"
            expanded_business = f"未单列初加工、农业投入品或生产性服务收入；{upper_label}仅作上界"
            strict_formula = expanded_formula = f"下界=0；上界=合并收入{total:.2f}-商业零售{commercial:.2f}={upper_revenue:.2f}"
            excluded_label = "生鲜、食品化洗、百货等商业零售"
            overlap = "商业零售为行业维度排除项；仅以合并收入减商业收入形成互斥残差，不叠加生鲜产品或采购金额"
            reason = "公司主营为连锁商超零售；销售生鲜商品不等于从事农业生产，采购额亦不替代涉农收入。"
            pending = "工业及其他和商业主营表外收入未拆具体性质，仅作上界；上界低于30%。"
            extra = "2020执行新收入准则后联营业务按净额法确认；统一采用当年合并利润表收入和当年披露商业收入，不采用总额法可比数"
        elif code == "002852":
            (total, total_cost, included_revenue, included_cost, upper_revenue,
             upper_cost, excluded_revenue, excluded_cost) = map(D, DAODAOQUAN[year])
            # Other-business revenue is the only possible strict item; it is
            # not separately identifiable from the combined upper amount for
            # expanded scope.  Keep the strict upper explicitly year-specific.
            other_business = {
                2018: D("22642785.01"), 2019: D("29613016.74"),
                2020: D("32517748.59"), 2021: D("54334389.14"),
                2022: D("71929930.50"),
            }[year]
            strict_lo, strict_hi = D("0"), other_business
            expanded_lo, expanded_hi = included_revenue, included_revenue + upper_revenue
            strict_cost_lo, strict_cost_hi = D("0"), upper_cost
            expanded_cost_lo, expanded_cost_hi = included_cost, included_cost + upper_cost
            upper_label = "散装油+其他业务"
            strict_business = "未单列直接农业收入；性质混合的其他业务仅作严格上界"
            expanded_business = "油料压榨副产粕类纳入扩展下界；以散装油和其他业务构造扩展上界"
            strict_formula = f"下界=0；上界=其他业务{other_business:.2f}"
            expanded_formula = f"下界=粕类{included_revenue:.2f}；上界=下界+散装油及其他业务{upper_revenue:.2f}={expanded_hi:.2f}"
            excluded_label = "精炼包装食用油"
            overlap = "包装油、粕类、散装油、其他业务为同一产品维度互斥项目；不叠加地区、渠道或原料采购"
            reason = "包装油属于精炼包装深加工；粕类为油料压榨副产品并用于饲料，纳入扩展口径；散装油主要含贸易油，不能全部直接纳入。"
            pending = "散装油中的自产初榨与贸易油未拆，其他业务含副产品和装卸等混合项目，只作上界。"
            if year in (2018, 2019):
                extra = "散装油年报明确主要为贸易油；散装油与其他业务成本未分别完整披露，采用总成本扣除包装油和粕类成本后的合并残差，不按比例分摊"
            else:
                extra = "散装油主要为贸易油；粕类、散装油及其他业务收入成本采用同一产品维度逐项核对"
        else:
            total, total_cost, upper_revenue, upper_cost, excluded_revenue, excluded_cost = map(D, LUZHOU[year])
            strict_lo = expanded_lo = D("0")
            strict_hi = expanded_hi = upper_revenue
            strict_cost_lo = expanded_cost_lo = D("0")
            strict_cost_hi = expanded_cost_hi = upper_cost
            upper_label = "未拆其他收入"
            strict_business = "未单列直接农业收入；未拆其他收入仅作上界"
            expanded_business = "未单列农产品初加工或农业投入品收入；未拆其他收入仅作上界"
            strict_formula = expanded_formula = f"下界=0；上界=其他收入{upper_revenue:.2f}"
            excluded_label = "中高档及其他白酒"
            overlap = "酒类与其他收入为同一收入构成维度互斥项目；不叠加地区、渠道、原粮采购或产量"
            reason = "白酒属于食品深加工；原粮采购、酿造窖池和产品名称均不能替代直接农业或初加工收入。"
            pending = "其他收入未拆具体业务性质，只作上界；上界低于30%。"
            extra = "酒类成本为产品/行业表可确认金额；其他收入成本按合并营业成本减酒类成本的互斥残差核对，不以成本反推收入"

        assert D("0") <= strict_lo <= strict_hi <= total
        assert D("0") <= expanded_lo <= expanded_hi <= total
        assert strict_cost_lo <= strict_cost_hi <= total_cost
        assert expanded_cost_lo <= expanded_cost_hi <= total_cost
        assert included_revenue + upper_revenue + excluded_revenue == total
        assert included_cost + upper_cost + excluded_cost == total_cost
        sr_lo, sr_hi = strict_lo / total, strict_hi / total
        er_lo, er_hi = expanded_lo / total, expanded_hi / total
        source_evidence = compact(src["利润表原文摘录"] + src["主营业务表原文摘录"])
        assert compact(f"{total:.2f}") in source_evidence or (
            code == "002852"
            and compact(f"{included_revenue:.2f}") in source_evidence
            and compact(f"{excluded_revenue:.2f}") in source_evidence
        ) or (
            code == "002852" and year == 2022
            and "826357087.03" in source_evidence
            and "71929930.50" in source_evidence
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
            "公司营业成本_元_反向证据": f"{total_cost:.2f}",
            "公司营业收入公式": "合并利润表营业收入",
            "严格口径成本下界_元_反向证据": f"{strict_cost_lo:.2f}",
            "严格口径成本上界_元_反向证据": f"{strict_cost_hi:.2f}",
            "扩展口径成本下界_元_反向证据": f"{expanded_cost_lo:.2f}",
            "扩展口径成本上界_元_反向证据": f"{expanded_cost_hi:.2f}",
            "单列初加工或农业投入品收入_元": f"{included_revenue:.2f}" if included_revenue else "",
            "单列初加工或农业投入品成本_元_反向证据": f"{included_cost:.2f}" if included_cost else "",
            "未拆上界项目": upper_label,
            "未拆上界项目收入_元": f"{upper_revenue:.2f}",
            "未拆上界项目成本_元_反向证据": f"{upper_cost:.2f}",
            "明确排除类别": excluded_label,
            "明确排除收入_元_反向证据": f"{excluded_revenue:.2f}",
            "明确排除成本_元_反向证据": f"{excluded_cost:.2f}",
            "收入成本判别": "收入决定纳入范围；同维度成本仅作反向核对，不用成本率推算或拆分收入",
            "严格样本结论": threshold(sr_lo, sr_hi),
            "扩展样本结论": threshold(er_lo, er_hi),
            "边界样本结论": boundary(er_lo, er_hi),
            "是否存在分部收入重叠": overlap,
            "纳入或剔除理由": reason,
            "待核实点": pending + ("2022行业分类字段仍待核实。" if year == 2022 else ""),
            "年报主营业务证据PDF页序号": src["年报主营业务候选PDF页序号"],
            "公司营业收入证据PDF页序号": profit_pages(code, year, src["利润表PDF页序号"]),
            "补充证据说明": extra,
            "年报链接": src["年报链接"],
            "2022行业字段处理": "沿用v30原值；待核实字段不插值、不复制相邻年份",
            "记录类型": "跨年快速复核第十九批W组（未合并）",
            "复核状态": "已人工复核（第十九批W组；主表未合并）",
            "复核日期": "2026-08-11",
        })

    out = pd.DataFrame(rows)
    assert len(out) == 20 and not out.duplicated(["股票代码", "年份"]).any()
    assert out["严格样本结论"].value_counts().to_dict() == {"否": 20}
    assert out["扩展样本结论"].value_counts().to_dict() == {"否": 20}
    assert out["边界样本结论"].value_counts().to_dict() == {"否": 19, "待核实": 1}
    pending_boundary = out[out["边界样本结论"].eq("待核实")]
    assert pending_boundary[["股票代码", "年份"]].to_records(index=False).tolist() == [("002852", 2022)]
    dq = out[out["股票代码"].eq("002852")].set_index("年份")
    assert dq.loc[2022, "扩展口径收入下界_元"] == "1398579768.79"
    assert dq.loc[2022, "扩展口径收入上界_元"] == "2296866786.32"
    assert D(dq.loc[2022, "扩展口径下界占比_原始未四舍五入"]) < D("0.30")
    assert D(dq.loc[2022, "扩展口径上界占比_原始未四舍五入"]) >= D("0.30")
    assert out.loc[out["年份"].eq(2022), "行业分类代码"].eq("待核实").all()
    assert out.loc[out["年份"].eq(2022), "行业分类名称"].eq("待核实").all()
    dq_pages = out[out["股票代码"].eq("002852")].set_index("年份")["公司营业收入证据PDF页序号"].to_dict()
    assert dq_pages == {2018: "71", 2019: "77", 2020: "81", 2021: "79", 2022: "73"}
    anjing_pages = out[out["股票代码"].eq("603345")].set_index("年份")["公司营业收入证据PDF页序号"].to_dict()
    assert anjing_pages == {2018: "81", 2019: "79", 2020: "82", 2021: "85", 2022: "96"}
    jy_pages = out[out["股票代码"].eq("603708")].set_index("年份")["公司营业收入证据PDF页序号"].to_dict()
    assert jy_pages == {2018: "74", 2019: "104", 2020: "83", 2021: "82", 2022: "79"}
    luzhou_pages = out[out["股票代码"].eq("000568")].set_index("年份")["公司营业收入证据PDF页序号"].to_dict()
    assert luzhou_pages == {2018: "65", 2019: "70", 2020: "76", 2021: "82", 2022: "87"}
    assert out["年报链接"].str.startswith("https://static.cninfo.com.cn/").all()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("batch19-W rows=20; strict no=20; expanded no=20; boundary no=19/pending=1; not merged")


if __name__ == "__main__":
    main()
