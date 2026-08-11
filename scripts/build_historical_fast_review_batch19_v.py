#!/usr/bin/env python3
"""Build standalone historical fast-review batch 19-V from fixed v30.

Medicines, medical services and daily-chemical products are excluded as deep
processing. Only separately disclosed herb planting, primary processing or
agricultural-input revenue may enter a numerator. Bases, biological assets and
tax exemptions are existence evidence, not substitutes for external revenue.
"""
from decimal import Decimal, getcontext
from pathlib import Path

import pandas as pd


getcontext().prec = 60
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v30_跨年快速复核第十八批.csv"
OUTPUT = ROOT / "outputs" / "跨年快速复核第十九批_V组_4家公司.csv"

# Total revenue/cost; main-business revenue/cost; mixed herb/decoction-piece
# revenue/cost; product "other" revenue/cost. Audited other business is the
# exact residual between total and main business.
QIANJIN = {
    # The 2018 report did not yet split herb/decoction pieces from "TCM
    # production"; therefore the entire TCM-production line is a conservative
    # upper bound. Later reports separately disclose herb/decoction pieces.
    2018: ("3328553963.17", "1776271447.61", "3285183218.04", "1763458218.10", "886213880.35", "319196978.22", "7245073.38", "4166134.08"),
    2019: ("3525238122.24", "1918690938.79", "3470401491.88", "1900795622.41", "71778597.60", "46835455.05", "0", "0"),
    2020: ("3626966808.62", "2030777576.81", "3586267940.40", "2025540232.07", "59917226.30", "36245495.86", "5210825.27", "4178075.14"),
    2021: ("3663844613.10", "2032238118.97", "3598722328.57", "2004964120.92", "73760077.34", "47274543.13", "6137787.72", "3132183.85"),
    2022: ("4026278593.25", "2289865386.62", "3954932518.59", "2259704379.15", "54323403.38", "39834132.46", "2938152.94", "1292618.64"),
}

# Total revenue; rounded service/other main revenue/cost converted from the
# annual report's RMB 10,000 unit; audited other-business revenue/cost.
TAIJI = {
    2018: ("10689384281.49", "42296400", "25210700", "96091956.42", "87606505.79"),
    2019: ("11643087426.74", "53651800", "21778300", "109216491.20", "104974053.42"),
    2020: ("11207803711.75", "50233600", "7874200", "104432005.99", "106856670.61"),
    2021: ("12149432719.04", "46596300", "32903500", "73359919.22", "61401572.61"),
    2022: ("14050659364.39", "45096500", "34135500", "69371589.71", "35773547.00"),
}

# Total revenue/cost; product "other" revenue; conservative residual cost
# after deducting only separately disclosed major medicine-product costs.
XINTIAN = {
    2018: ("694259400.60", "145713216.88", "21081483.88", "21066591.64"),
    2019: ("773337464.67", "162580430.46", "22888433.04", "25174224.26"),
    2020: ("750946390.31", "165328415.77", "7314540.29", "23147815.26"),
    2021: ("969844472.18", "201157476.52", "12937414.78", "27908654.33"),
    2022: ("1087673294.88", "247286557.25", "16941971.87", "34863758.90"),
}

# Total revenue; separately disclosed planting revenue/cost; mutually
# exclusive audited other-business revenue/cost used only as an upper bound.
YUNNAN = {
    2018: ("26708213487.75", "12118066.99", "15385631.40", "28060386.52", "11378369.23"),
    2019: ("29664673868.68", "3251888.12", "4227484.49", "79460881.16", "30913475.39"),
    2020: ("32742766763.79", "376212.00", "140867.83", "47187098.34", "34501926.43"),
    2021: ("36373919016.03", "997037.00", "951299.84", "78087832.64", "58324106.31"),
    2022: ("36488372649.73", "1591729.90", "7431315.90", "48810323.96", "34346894.23"),
}

# Direct PDF-page extraction found three locator defects in fixed v30. Keep
# v30 read-only and correct the standalone batch evidence fields only.
BUSINESS_PAGE_OVERRIDES = {
    ("000538", 2018): "18|19|20|21",
    ("000538", 2020): "22|23|24",
    ("000538", 2021): "22|23|24",
    ("000538", 2022): "26|27",
    ("600479", 2022): "15|16|17",
}
PROFIT_PAGE_OVERRIDES = {
    ("000538", 2018): "97",
    ("600479", 2020): "80",
}
TAIJI_OTHER_BUSINESS_PAGES = {
    2018: "167",
    2019: "155",
    2020: "154|155",
    2021: "188|189",
    2022: "165",
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
        source["股票代码"].isin(["600479", "600129", "002873", "000538"])
        & source["复核状态"].str.startswith("年报及业务表已定位", na=False)
    ].sort_values(["股票代码", "年份"])
    assert len(source) == 958 and len(selected) == 20
    assert selected.groupby("股票代码").size().to_dict() == {"000538": 5, "002873": 5, "600129": 5, "600479": 5}
    assert not selected.duplicated(["股票代码", "年份"]).any()

    rows = []
    for _, src in selected.iterrows():
        code, year = src["股票代码"], int(src["年份"])
        planting_revenue = planting_cost = mixed_revenue = mixed_cost = D("0")
        other_revenue = other_cost = D("0")
        other_business_evidence_pages = ""

        if code == "600479":
            vals = list(map(D, QIANJIN[year]))
            total, total_cost, main_revenue, main_cost, herb, herb_cost, product_other, product_other_cost = vals
            other_revenue, other_cost = total - main_revenue, total_cost - main_cost
            strict_lo = expanded_lo = D("0")
            strict_hi = expanded_hi = herb + product_other + other_revenue
            mixed_revenue, mixed_cost = herb + product_other, herb_cost + product_other_cost
            upper_cost = mixed_cost + other_cost
            strict_business = "未单列药材种植对外收入；中药材及饮片、产品其他和其他业务仅作上界"
            expanded_business = "未单列可确认的药材初加工/农业投入品收入；未拆项目仅作上界"
            formula = f"下界=0；上界=中药材及饮片/未拆中药生产与产品其他{mixed_revenue:.2f}+其他业务{other_revenue:.2f}={strict_hi:.2f}"
            reason = "西药、药品流通、卫生用品及酒饮均属药品/日化深加工或商业；中药材及饮片混含饮片，不能整体纳入。"
            if year == 2018:
                pending = "2018未将中药材/饮片从中药生产拆出，故整项中药生产作上界；产品其他和其他业务亦作上界，合计仍低于30%。"
            else:
                pending = "中药材及饮片未拆药材购销、初加工与饮片生产；产品其他和其他业务性质未拆，但上界不足4%。"
            overlap = "产品维度中的中药材及饮片/其他与审计其他业务属于互斥收入层级；不叠加行业、地区，基地内部供料不另计"
            cost_note = f"混合产品成本{mixed_cost:.2f}+其他业务成本{other_cost:.2f}={upper_cost:.2f}，只作上界反向证据"
            deep = "中西药生产、饮片、药品批发零售、卫生用品和酒饮"
            extra = "子公司药材种植、收购、加工基地及药材公司业务范围只证明业务存在，不替代合并口径对外收入"
        elif code == "600129":
            total, service_other, service_other_cost, other_revenue, other_cost = map(D, TAIJI[year])
            strict_lo = expanded_lo = D("0")
            strict_hi = expanded_hi = service_other + other_revenue
            mixed_revenue, mixed_cost = service_other, service_other_cost
            upper_cost = service_other_cost + other_cost
            strict_business = "未单列上市公司本体药材种植对外收入；服务业及其他、其他业务仅作上界"
            expanded_business = "未单列可确认的药材初加工或农业投入品收入；未拆项目仅作上界"
            formula = f"下界=0；上界=服务业及其他（万元表换算）{service_other:.2f}+审计其他业务{other_revenue:.2f}={strict_hi:.2f}"
            reason = "医药工业、医药商业和药品均排除；药材基地、收购和受托管理种植公司不能替代上市公司本体的单列外销收入。"
            pending = "服务业及其他按年报万元口径换算，内部性质未拆；审计其他业务亦未拆，但合计上界不足2%。"
            overlap = "服务业及其他属于主营行业维度，审计其他业务属于互斥收入层级；2021—2022分部抵销不另加，地区维度不叠加"
            cost_note = f"服务业及其他成本（万元表换算）{service_other_cost:.2f}+审计其他业务成本{other_cost:.2f}={upper_cost:.2f}，只作反向证据"
            deep = "中西成药制造、医药商业、医疗及药品服务"
            other_business_evidence_pages = TAIJI_OTHER_BUSINESS_PAGES[year]
            extra = "药材基地面积、种植扶持、收购额和托管收益均不等于合并口径药材外销收入；审计附注页单独列示"
        elif code == "002873":
            total, total_cost, product_other, residual_cost = map(D, XINTIAN[year])
            strict_lo = expanded_lo = D("0")
            strict_hi = expanded_hi = product_other
            mixed_revenue, mixed_cost = product_other, residual_cost
            upper_cost = residual_cost
            strict_business = "未单列药材种植对外收入；药品产品“其他”仅作上界"
            expanded_business = "未单列药材初加工或农业投入品收入；药品产品“其他”仅作上界"
            formula = f"下界=0；上界=未拆产品其他{product_other:.2f}"
            reason = "妇科、泌尿、清热解毒等收入均为中成药；种植基地主要保障原料，未单列对外农业收入。"
            pending = "产品其他未拆具体品种，只作上界；上界不足4%。"
            overlap = "产品类别合计等于合并营业收入；只取同一产品维度的其他类，不叠加行业、地区或其他业务"
            cost_note = f"成本上界{residual_cost:.2f}=合并营业成本扣除已披露主要药品成本后的保守残差，包含部分明确排除药品成本"
            deep = "坤泰/宁泌泰等中成药、妇科药、泌尿系统药、清热解毒药"
            extra = "药材基地、存货和原料采购不替代对外收入；成本残差只作保守反向证据，不用于倒推收入"
        else:
            total, planting_revenue, planting_cost, other_revenue, other_cost = map(D, YUNNAN[year])
            strict_lo = expanded_lo = planting_revenue
            strict_hi = expanded_hi = planting_revenue + other_revenue
            mixed_revenue, mixed_cost = D("0"), D("0")
            upper_cost = planting_cost + other_cost
            strict_business = "单列种植业销售收入；未拆其他业务仅作上界"
            expanded_business = "同严格口径；未单列其他可确认的初加工或农业投入品收入"
            formula = f"下界=种植业销售{planting_revenue:.2f}；上界=种植业销售{planting_revenue:.2f}+其他业务{other_revenue:.2f}={strict_hi:.2f}"
            reason = "种植业销售属于直接农业；工业产品、药品商业、医疗及日化产品排除，其他业务性质未拆只作上界。"
            pending = "其他业务未拆农业与非农业性质，只作上界；不影响低于30%的结论。"
            overlap = "采用同一分行业收入维度；种植业与其他业务互斥，不与产品、事业部或地区维度相加"
            cost_note = f"单列种植成本{planting_cost:.2f}+其他业务成本{other_cost:.2f}={upper_cost:.2f}，只作反向核对"
            deep = "药品工业、药品批发零售、医疗健康和牙膏等日化产品"
            extra = "种植收入与种植成本均来自年报收入/成本表；生物资产、基地和免税信息未替代收入"

        assert D("0") <= strict_lo <= strict_hi <= total
        assert D("0") <= expanded_lo <= expanded_hi <= total
        sr_lo, sr_hi = strict_lo / total, strict_hi / total
        er_lo, er_hi = expanded_lo / total, expanded_hi / total
        assert compact(f"{total:.2f}") in compact(src["利润表原文摘录"]) or compact(f"{total:.2f}") in compact(src["主营业务表原文摘录"])

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
            "严格口径上下界公式": formula,
            "严格口径下界占比_原始未四舍五入": ratio(strict_lo, total),
            "严格口径上界占比_原始未四舍五入": ratio(strict_hi, total),
            "扩展口径涉农业务": expanded_business,
            "扩展口径正式涉农收入_元": f"{expanded_lo:.2f}" if expanded_lo == expanded_hi else "",
            "扩展口径收入下界_元": f"{expanded_lo:.2f}",
            "扩展口径收入上界_元": f"{expanded_hi:.2f}",
            "扩展口径上下界公式": formula,
            "扩展口径下界占比_原始未四舍五入": ratio(expanded_lo, total),
            "扩展口径上界占比_原始未四舍五入": ratio(expanded_hi, total),
            "公司营业收入_元": f"{total:.2f}",
            "公司营业收入公式": "合并利润表营业收入",
            "单列药材种植收入_元": f"{planting_revenue:.2f}" if planting_revenue else "",
            "单列药材种植成本_元_反向证据": f"{planting_cost:.2f}" if planting_cost else "",
            "中药材饮片或未拆产品收入_元_上界": f"{mixed_revenue:.2f}" if mixed_revenue else "",
            "中药材饮片或未拆产品成本_元_反向证据": f"{mixed_cost:.2f}" if mixed_cost else "",
            "审计其他业务收入_元_上界": f"{other_revenue:.2f}" if other_revenue else "",
            "审计其他业务成本_元_反向证据": f"{other_cost:.2f}" if other_cost else "",
            "上界对应成本合计_元_反向证据": f"{upper_cost:.2f}",
            "深加工或排除类别": deep,
            "收入成本判别": cost_note,
            "严格样本结论": threshold(sr_lo, sr_hi),
            "扩展样本结论": threshold(er_lo, er_hi),
            "边界样本结论": boundary(er_lo, er_hi),
            "是否存在分部收入重叠": overlap,
            "纳入或剔除理由": reason,
            "待核实点": pending,
            "年报主营业务证据PDF页序号": BUSINESS_PAGE_OVERRIDES.get((code, year), src["年报主营业务候选PDF页序号"]),
            "公司营业收入证据PDF页序号": PROFIT_PAGE_OVERRIDES.get((code, year), src["利润表PDF页序号"]),
            "审计其他业务收入成本证据PDF页序号": other_business_evidence_pages,
            "补充证据说明": extra,
            "年报链接": src["年报链接"],
            "2022行业字段处理": "沿用v30原值；待核实字段不插值、不复制相邻年份",
            "记录类型": "跨年快速复核第十九批V组（未合并）",
            "复核状态": "已人工复核（第十九批V组；主表未合并）",
            "复核日期": "2026-08-11",
        })

    out = pd.DataFrame(rows)
    assert len(out) == 20 and not out.duplicated(["股票代码", "年份"]).any()
    assert out["严格样本结论"].value_counts().to_dict() == {"否": 20}
    assert out["扩展样本结论"].value_counts().to_dict() == {"否": 20}
    assert out["边界样本结论"].value_counts().to_dict() == {"否": 20}
    qj = out[out["股票代码"] == "600479"].set_index("年份")
    assert qj.loc[2018, "严格口径收入上界_元"] == "936829698.86"
    assert qj.loc[2022, "严格口径收入上界_元"] == "128607630.98"
    tj = out[out["股票代码"] == "600129"].set_index("年份")
    assert tj.loc[2022, "严格口径收入上界_元"] == "114468089.71"
    assert tj["审计其他业务收入成本证据PDF页序号"].to_dict() == {
        2018: "167", 2019: "155", 2020: "154|155", 2021: "188|189", 2022: "165"
    }
    xt = out[out["股票代码"] == "002873"].set_index("年份")
    assert xt.loc[2022, "严格口径收入上界_元"] == "16941971.87"
    yn = out[out["股票代码"] == "000538"].set_index("年份")
    assert yn.loc[2018, "单列药材种植收入_元"] == "12118066.99"
    assert yn.loc[2022, "严格口径收入上界_元"] == "50402053.86"
    assert yn.loc[2018, "公司营业收入证据PDF页序号"] == "97"
    assert yn.loc[2018, "年报主营业务证据PDF页序号"] == "18|19|20|21"
    assert yn.loc[2020, "年报主营业务证据PDF页序号"] == "22|23|24"
    assert yn.loc[2021, "年报主营业务证据PDF页序号"] == "22|23|24"
    assert yn.loc[2022, "年报主营业务证据PDF页序号"] == "26|27"
    assert qj.loc[2020, "公司营业收入证据PDF页序号"] == "80"
    assert qj.loc[2022, "年报主营业务证据PDF页序号"] == "15|16|17"
    assert out.loc[out["年份"].eq(2022), "行业分类代码"].eq("待核实").all()
    assert out.loc[out["年份"].eq(2022), "行业分类名称"].eq("待核实").all()
    assert out["年报链接"].str.startswith("https://static.cninfo.com.cn/").all()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("batch19-V rows=20; strict no=20; expanded no=20; boundary no=20; not merged")


if __name__ == "__main__":
    main()
