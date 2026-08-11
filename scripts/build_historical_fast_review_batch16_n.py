#!/usr/bin/env python3
"""Build independent fast-review batch 16-N from the fixed v26 worktable.

Plant extracts, pigments and starch sugars are manufacturing/deep-processing
products and are not included merely because their raw materials are crops.
Separately disclosed feed, animal-nutrition amino acids and fertiliser are
agricultural inputs.  Product rows with both feed and non-feed uses are used
only as upper bounds, and separately identifiable trading/other-business
revenue is excluded.
"""
from decimal import Decimal, getcontext
from pathlib import Path

import pandas as pd


getcontext().prec = 60
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v26_跨年快速复核第十五批第二组.csv"
OUTPUT = ROOT / "outputs" / "跨年快速复核第十六批_N组_3家公司.csv"


# year: total, eligible lower, mixed-use upper increment, corresponding lower
# cost, corresponding upper-increment cost, separately identified
# trade/other-business revenue, evidence pages, precision note.
#
# The 2018/2019 upper bounds use the financial-note "main operating revenue by
# product" rows, not the broader management table, thereby removing separately
# identifiable other-business/trading revenue.  From 2020 the report no longer
# provides this split; the mixed cottonseed row remains an upper bound because
# it can contain trading and non-feed products.
MORNING = {
    2014: ("1207179702.30", "458410236.96", "341671198.35", "427472251.89", "290688246.13", "5533210.72", "20|21", "产品收入、成本均为元"),
    2015: ("1267629195.49", "359317855.36", "445767450.22", "325523828.27", "390672374.24", "78479938.14", "19|20", "产品收入、成本均为元"),
    2018: ("3063440575.35", "0", "2482572554.74", "0", "2515030006.58", "464302190.19", "20|21|203", "收入上界采用财务附注主营业务产品行；成本为管理表较宽成本上限"),
    2019: ("3265232815.43", "0", "2740287998.04", "0", "2558097153.87", "402010672.92", "19|20|217", "收入上界采用财务附注主营业务产品行；成本为管理表较宽成本上限"),
    2020: ("3912935282.07", "0", "3770817899.73", "0", "3134788400.00", "0", "29|30|247", "产品成本按年报万元表×10,000；混合行内贸易无法另拆"),
    2021: ("4873610394.24", "0", "4695688386.99", "0", "3997655400.00", "0", "31|32|237", "产品成本按年报万元表×10,000；混合行内贸易无法另拆"),
    2022: ("6295872780.53", "0", "6029458448.19", "0", "5199975000.00", "0", "30|31|214", "收入采用元表；成本按万元表×10,000，已与2022营业成本披露反核"),
}


# 2014/2015 lower = organic/compound fertiliser only.  Starch by-products are
# mixed because corn germ can be sold for oil processing while protein/fibre
# products can be feed inputs; the old broad amino-acid row and "bacterial
# protein and others" are also mixed, so all three enter only the upper bound.
# From 2018 the lower is the separately disclosed animal-nutrition amino-acid
# product row; "other" contains bio-fertiliser together with petroleum xanthan
# and other non-agricultural products and therefore enters only the upper bound.
# The final tuple item is separately disclosed other-business revenue excluded
# from the numerator.
MEIHUA = {
    2014: ("9864967361.84", "139920975.21", "5112919823.39", "121400276.22", "3932001255.90", "168332793.25", "15"),
    2015: ("11853174318.23", "252319500.95", "5979744632.67", "234410600.70", "4886019830.31", "55067885.79", "16|17"),
    2018: ("12648045803.79", "5254769165.26", "1518224436.14", "4024720290.50", "1007659957.80", "141405482.87", "21|22"),
    2019: ("14553547455.20", "6578651997.16", "1334471417.42", "5778450550.42", "924839145.39", "65653381.08", "17|18"),
    2020: ("17049514475.36", "8686944430.97", "1383635934.00", "7630378972.73", "1098108049.97", "445893114.20", "13|14"),
    # The 2021 denominator is the latest comparative restated in the 2022
    # annual report.  The 224,066,069.52 trial-run revenue adjustment and its
    # 164,776,214.05 cost are not allocated by product, so they enter only the
    # broad upper bounds together with the mixed "other" product row.
    2021: ("23060956394.50", "11587375122.49", "2058337330.56", "9285105151.60", "1387610354.41", "333883176.00", "18|19|20"),
    2022: ("27937152798.85", "14905702104.63", "2187761849.57", "11447666409.56", "1042521165.89", "194785627.57", "16|17|18"),
}

MEIHUA_2021_RESTATEMENT_REVENUE = Decimal("224066069.52")
MEIHUA_2021_RESTATEMENT_COST = Decimal("164776214.05")


# lower = separately disclosed feed/feed-products; upper additionally includes
# functional sugars whose disclosed applications span food and animal feed.
# Starch sugars and miscellaneous/other-business rows are not added.  The final
# tuple item is separately disclosed other-business revenue.
BAOLINGBAO = {
    2018: ("1730012458.43", "292326599.38", "494524841.50", "271443699.76", "370242954.85", "9044614.30", "14|15"),
    2019: ("1805170075.01", "299000340.72", "549853014.96", "281207529.91", "405604356.52", "10532088.58", "13|14"),
    # Use the 2021 annual report's explicitly retrospectively reclassified
    # 2020 product comparatives, not the superseded 2020-report categories.
    2020: ("2054578268.02", "212801727.43", "804052206.40", "208245326.98", "669350800.94", "13190252.91", "30|31"),
    2021: ("2764976972.69", "308328643.35", "1212152678.86", "299268260.43", "923584356.88", "9901611.91", "30|31"),
    2022: ("2712745317.35", "580708042.41", "917394915.80", "560263466.33", "759003604.05", "9588930.93", "30|31|32"),
}


def D(value: str) -> Decimal:
    return Decimal(value)


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
        source["股票代码"].isin(["300138", "600873", "002286"])
        & source["复核状态"].str.startswith("年报及业务表已定位", na=False)
    ].sort_values(["股票代码", "年份"])
    assert len(source) == 958
    assert len(selected) == 19
    assert selected.groupby("股票代码").size().to_dict() == {"002286": 5, "300138": 7, "600873": 7}
    assert not selected.duplicated(["股票代码", "年份"]).any()

    rows = []
    for _, src in selected.iterrows():
        code, year = src["股票代码"], int(src["年份"])
        strict_lo = strict_hi = strict_cost_lo = strict_cost_hi = D("0")
        trade_excluded = D("0")

        if code == "300138":
            total_s, lo_s, inc_s, clo_s, cinc_s, trade_s, pages, precision = MORNING[year]
            total, expanded_lo = D(total_s), D(lo_s)
            expanded_hi = expanded_lo + D(inc_s)
            expanded_cost_lo, expanded_cost_hi = D(clo_s), D(clo_s) + D(cinc_s)
            trade_excluded = D(trade_s)
            strict_business = "未单列直接种植或其他直接农业外销收入"
            if year <= 2015:
                expanded_business = "籽仁壳绒及粕渣等棉籽初加工产品作下界；食品/医药/饲料混合用途天然色素作上界"
                expanded_formula = (
                    f"下界=籽仁壳绒+粕渣等棉籽初加工产品{expanded_lo:.2f}；"
                    f"上界=下界+混合用途天然色素{D(inc_s):.2f}={expanded_hi:.2f}"
                )
                cost_note = f"棉籽初加工成本下界{expanded_cost_lo:.2f}、含混合天然色素成本上界{expanded_cost_hi:.2f}"
                overlap = "无；同一分产品层级加总，其他业务中的棉籽/辣椒贸易已排除"
                audit_note = (
                    "籽仁壳绒、粕渣及棉籽蛋白属于农产品初加工或饲料原料，形成确定下界；"
                    "天然色素同时用于食品、医药、化妆品和饲料，只能增加上界。"
                )
                pending = "需取得天然色素按饲料用途与非饲料用途的销售收入；其他业务棉籽/辣椒贸易不并入。"
            else:
                expanded_business = "天然色素及棉籽蛋白/粕渣存在农业用途，但产品大类混含食品医药用途、油脂及贸易"
                expanded_formula = f"下界=0；上界=可识别含农业用途的混合产品行{expanded_hi:.2f}"
                cost_note = f"混合产品成本上界{expanded_cost_hi:.2f}；不以成本倒推农业用途收入"
                overlap = "混合用途及部分贸易无法从色素/棉籽产品行拆出；仅设上界，未与行业行重复相加"
                audit_note = (
                    "植物提取、色素和油脂不因农业原料而自动纳入；棉籽大类包含农产品初加工品，"
                    "天然色素也存在饲料用途，但产品大类未拆符合与不符合扩展口径的收入，故不能形成可量化下界。"
                )
                pending = "需取得天然色素和棉籽类产品按农业/非农业用途、初加工/深加工及自产/贸易的收入拆分。"
            evidence_keyword = "粕渣" if year <= 2015 else "棉籽"
        elif code == "600873":
            total_s, lo_s, inc_s, clo_s, cinc_s, trade_s, pages = MEIHUA[year]
            total, expanded_lo = D(total_s), D(lo_s)
            expanded_hi = expanded_lo + D(inc_s)
            expanded_cost_lo, expanded_cost_hi = D(clo_s), D(clo_s) + D(cinc_s)
            trade_excluded = D(trade_s)
            precision = "单列产品收入、成本均为元；未与行业或地区维度相加"
            strict_business = "发酵制造产品不属于直接农业生产"
            if year <= 2015:
                expanded_business = "有机/复合肥作下界；淀粉副产品、混合氨基酸、菌体蛋白及其他作上界"
                expanded_formula = (
                    f"下界=有机/复合肥{expanded_lo:.2f}；"
                    f"上界=下界+淀粉副产品及混合氨基酸、菌体蛋白其他{D(inc_s):.2f}={expanded_hi:.2f}"
                )
                audit_note = (
                    "肥料为明确农业投入品；淀粉副产品中玉米胚芽可继续加工胚芽油、蛋白粉/纤维可作饲料，"
                    "旧氨基酸及菌体蛋白其他也未拆饲料级与医药/非农业用途，因此这些混合行只作上界。"
                )
                pending = "需拆分淀粉副产品的饲料用途，以及旧氨基酸、菌体蛋白其他中的饲料级、医药级和非农业产品。"
                evidence_keyword = "氨基酸"
            else:
                expanded_business = "单列动物营养氨基酸作下界；混合其他中的生物有机肥仅作上界"
                if year == 2021:
                    mixed_other = D(inc_s) - MEIHUA_2021_RESTATEMENT_REVENUE
                    expanded_formula = (
                        f"下界=原年报已单列动物营养氨基酸{expanded_lo:.2f}；"
                        f"上界=下界+混合其他{mixed_other:.2f}+未按产品分配的试运行销售重列调整"
                        f"{MEIHUA_2021_RESTATEMENT_REVENUE:.2f}={expanded_hi:.2f}"
                    )
                else:
                    expanded_formula = (
                        f"下界=动物营养氨基酸{expanded_lo:.2f}；"
                        f"上界=下界+混合其他{D(inc_s):.2f}={expanded_hi:.2f}"
                    )
                audit_note = (
                    "动物营养氨基酸行包括饲料级氨基酸及大原料副产品，属于明确农业投入品；"
                    "‘其他’同时含生物有机肥与石油级黄原胶等非农业产品，只能增加上界。"
                )
                pending = "如需精确分子，仍须拆分‘其他’中的生物有机肥；动物营养氨基酸下界可直接使用。"
                if year == 2021:
                    pending = (
                        "2022年报按解释15号将2021营业收入重列增加224,066,069.52元、成本增加164,776,214.05元，"
                        "但未按产品分配；本表统一采用最新重列分母，原报动物营养金额只作已确认下界，未分配调整额只作上界。"
                    )
                evidence_keyword = "动物营养氨基酸"
            cost_note = f"农业投入品成本下界{expanded_cost_lo:.2f}、含混合项成本上界{expanded_cost_hi:.2f}"
            if year == 2021:
                cost_note += "；成本上界含未按产品分配的重列调整164,776,214.05元，不据此计算产品毛利"
            overlap = "否（使用同一分产品层级；行业、地区和销售模式行不参与加总）"
        else:
            total_s, lo_s, inc_s, clo_s, cinc_s, trade_s, pages = BAOLINGBAO[year]
            total, expanded_lo = D(total_s), D(lo_s)
            expanded_hi = expanded_lo + D(inc_s)
            expanded_cost_lo, expanded_cost_hi = D(clo_s), D(clo_s) + D(cinc_s)
            trade_excluded = D(trade_s)
            precision = "单列产品收入、成本均为元；2022收入成本与产品表及利润表反核一致"
            strict_business = "功能配料及生物饲料制造不属于直接农业生产"
            expanded_business = "单列饲料产品作下界；食品/饲料混合用途功能糖作上界；淀粉糖深加工排除"
            expanded_formula = (
                f"下界=饲料/饲料类{expanded_lo:.2f}；"
                f"上界=下界+混合用途功能糖{D(inc_s):.2f}={expanded_hi:.2f}"
            )
            cost_note = f"饲料成本下界{expanded_cost_lo:.2f}、含混合功能糖成本上界{expanded_cost_hi:.2f}"
            overlap = "否（使用同一分产品层级；功能糖只作上界，淀粉糖和其他业务未加总）"
            audit_note = (
                "饲料/饲料类为明确农业投入品；低聚糖、糖醇及其他功能糖同时用于食品和饲料，故仅作上界；"
                "果葡糖浆、麦芽糊精和其他淀粉糖属于淀粉糖深加工，副产品及其他、其他业务及贸易排除。"
            )
            pending = "需取得功能糖按动物营养/饲料用途的销售收入；贸易公司收入不得依经营范围并入。"
            if year == 2020:
                pending += " 产品收入和成本采用2021年报对2020年追溯重分类后的最新比较数。"
            evidence_keyword = "饲料"

        denominator_evidence = src["利润表原文摘录"]
        business_evidence = src["主营业务表原文摘录"]
        if code == "600873" and year == 2021:
            denominator_evidence = selected.loc[
                (selected["股票代码"].eq("600873")) & selected["年份"].eq(2022),
                "利润表原文摘录",
            ].iloc[0]
        if code == "002286" and year == 2020:
            latest_bb = selected.loc[
                (selected["股票代码"].eq("002286")) & selected["年份"].eq(2021)
            ].iloc[0]
            denominator_evidence = latest_bb["利润表原文摘录"]
            business_evidence = latest_bb["主营业务表原文摘录"]
        assert compact(format(total, "f")) in compact(denominator_evidence), (code, year, "denominator")
        assert evidence_keyword in business_evidence, (code, year, "business evidence")
        assert D("0") <= strict_lo <= strict_hi <= total
        assert D("0") <= expanded_lo <= expanded_hi <= total
        assert D("0") <= expanded_cost_lo <= expanded_cost_hi

        sr_lo, sr_hi = strict_lo / total, strict_hi / total
        er_lo, er_hi = expanded_lo / total, expanded_hi / total
        strict_result = threshold(sr_lo, sr_hi)
        expanded_result = threshold(er_lo, er_hi)
        boundary_result = boundary(er_lo, er_hi)

        report_url = src["年报链接"]
        supplementary_original_url = ""
        profit_page = src["利润表PDF页序号"]
        business_pages = pages
        if code == "600873" and year == 2021:
            latest = selected.loc[
                (selected["股票代码"].eq("600873")) & selected["年份"].eq(2022)
            ].iloc[0]
            supplementary_original_url = report_url
            report_url = latest["年报链接"]
            profit_page = "60|83|166"
            business_pages = "原2021年报18|19|20"
        if code == "002286" and year == 2020:
            latest = selected.loc[
                (selected["股票代码"].eq("002286")) & selected["年份"].eq(2021)
            ].iloc[0]
            supplementary_original_url = report_url
            report_url = latest["年报链接"]
            profit_page = latest["利润表PDF页序号"]
            business_pages = "2021年报30|31（2020追溯重分类比较数）"

        rows.append({
            "股票代码": code, "公司全称": src["公司全称"], "年份": year,
            "行业分类代码": src["行业分类代码"] or "待核实", "行业分类名称": src["行业分类名称"] or "待核实",
            "严格口径涉农业务": strict_business, "严格口径正式涉农收入_元": "",
            "严格口径收入下界_元": f"{strict_lo:.2f}", "严格口径收入上界_元": f"{strict_hi:.2f}",
            "严格口径上下界公式": "下界=上界=0", "严格口径下界占比_原始未四舍五入": raw(strict_lo, total),
            "严格口径上界占比_原始未四舍五入": raw(strict_hi, total),
            "扩展口径涉农业务": expanded_business,
            "扩展口径正式涉农收入_元": "" if expanded_lo == 0 else f"{expanded_lo:.2f}",
            "扩展口径正式涉农收入占比_原始未四舍五入": "" if expanded_lo == 0 else raw(expanded_lo, total),
            "扩展口径收入下界_元": f"{expanded_lo:.2f}", "扩展口径收入上界_元": f"{expanded_hi:.2f}",
            "扩展口径上下界公式": expanded_formula,
            "扩展口径下界占比_原始未四舍五入": raw(expanded_lo, total),
            "扩展口径上界占比_原始未四舍五入": raw(expanded_hi, total),
            "公司营业收入_元": f"{total:.2f}", "公司营业收入公式": "合并利润表营业收入",
            "严格口径成本下界_元_反向证据": f"{strict_cost_lo:.2f}",
            "严格口径成本上界_元_反向证据": f"{strict_cost_hi:.2f}",
            "扩展口径成本下界_元_反向证据": f"{expanded_cost_lo:.2f}",
            "扩展口径成本上界_元_反向证据": f"{expanded_cost_hi:.2f}",
            "贸易或其他业务排除收入_元_反向证据": "" if trade_excluded == 0 else f"{trade_excluded:.2f}",
            "收入成本反核说明": cost_note,
            "严格样本结论": strict_result, "扩展样本结论": expanded_result, "边界样本结论": boundary_result,
            "是否存在分部收入重叠": overlap,
            "纳入或剔除理由": (
                f"严格区间[{raw(strict_lo,total)}, {raw(strict_hi,total)}]；"
                f"扩展区间[{raw(expanded_lo,total)}, {raw(expanded_hi,total)}]。{audit_note}"
            ),
            "待核实点": pending, "金额单位及精度说明": precision,
            "年报主营业务证据PDF页序号": business_pages,
            "公司营业收入证据PDF页序号": profit_page, "年报链接": report_url,
            "补充原年报链接": supplementary_original_url,
            "2022行业字段处理": "沿用v26原值；待核实字段不插值、不复制相邻年份",
            "记录类型": "跨年快速复核第十六批N组（未合并）",
            "复核状态": "已人工复核（第十六批N组；主表未合并）", "复核日期": "2026-08-11",
        })

    out = pd.DataFrame(rows)
    assert len(out) == 19 and not out.duplicated(["股票代码", "年份"]).any()
    assert out["严格样本结论"].value_counts().to_dict() == {"否": 19}
    assert out["扩展样本结论"].value_counts().to_dict() == {"待核实": 13, "否": 3, "是": 3}
    assert out["边界样本结论"].value_counts().to_dict() == {"待核实": 16, "否": 3}
    morning_early = out["股票代码"].eq("300138") & out["年份"].le(2015)
    morning_late = out["股票代码"].eq("300138") & out["年份"].ge(2018)
    assert out.loc[morning_early, "扩展口径收入下界_元"].tolist() == ["458410236.96", "359317855.36"]
    assert out.loc[morning_early, "扩展口径成本下界_元_反向证据"].tolist() == ["427472251.89", "325523828.27"]
    assert out.loc[morning_early, "扩展口径正式涉农收入_元"].ne("").all()
    assert out.loc[morning_late, "扩展口径收入下界_元"].eq("0.00").all()
    assert out.loc[morning_late, "扩展口径正式涉农收入_元"].eq("").all()
    morning_unseparated_trade = out["股票代码"].eq("300138") & out["年份"].ge(2020)
    assert out.loc[morning_unseparated_trade, "贸易或其他业务排除收入_元_反向证据"].eq("").all()
    exact_inputs = out["股票代码"].isin(["600873", "002286"])
    assert out.loc[exact_inputs, "扩展口径正式涉农收入_元"].ne("").all()
    assert out.loc[exact_inputs, "贸易或其他业务排除收入_元_反向证据"].ne("").all()
    assert out.loc[(out["股票代码"].eq("600873")) & out["年份"].ge(2020), "扩展样本结论"].eq("是").all()
    assert out.loc[(out["股票代码"].eq("002286")) & out["年份"].le(2020), "扩展样本结论"].eq("否").all()
    assert out.loc[(out["股票代码"].eq("002286")) & out["年份"].ge(2021), "扩展样本结论"].eq("待核实").all()
    assert out.loc[out["年份"].eq(2022), "行业分类代码"].eq("待核实").all()
    assert out.loc[out["年份"].eq(2022), "行业分类名称"].eq("待核实").all()
    assert out.loc[(out["股票代码"].eq("600873")) & out["年份"].eq(2022), "扩展口径成本下界_元_反向证据"].iloc[0] == "11447666409.56"
    mh_2021 = out.loc[(out["股票代码"].eq("600873")) & out["年份"].eq(2021)].iloc[0]
    assert mh_2021["公司营业收入_元"] == "23060956394.50"
    assert mh_2021["扩展口径收入下界_元"] == "11587375122.49"
    assert mh_2021["扩展口径收入上界_元"] == "13645712453.05"
    assert mh_2021["贸易或其他业务排除收入_元_反向证据"] == "333883176.00"
    assert "未按产品分配的试运行销售重列调整224066069.52" in compact(mh_2021["扩展口径上下界公式"])
    assert mh_2021["年报链接"].endswith("1216055014.PDF")
    assert mh_2021["补充原年报链接"].endswith("1212557814.PDF")
    bb_2020 = out.loc[(out["股票代码"].eq("002286")) & out["年份"].eq(2020)].iloc[0]
    assert bb_2020["扩展口径收入下界_元"] == "212801727.43"
    assert bb_2020["扩展口径收入上界_元"] == "1016853933.83"
    assert bb_2020["扩展口径成本上界_元_反向证据"] == "877596127.92"
    assert bb_2020["年报链接"].endswith("1213205314.PDF")
    assert bb_2020["补充原年报链接"].endswith("1209850534.PDF")
    assert out.loc[(out["股票代码"].eq("002286")) & out["年份"].eq(2022), "扩展口径成本下界_元_反向证据"].iloc[0] == "560263466.33"
    assert out.loc[(out["股票代码"].eq("300138")) & out["年份"].eq(2022), "扩展口径成本上界_元_反向证据"].iloc[0] == "5199975000.00"
    assert out["年报链接"].str.startswith("https://static.cninfo.com.cn/").all()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("batch16-N rows=19; strict no=19; expanded no/pending/yes=3/13/3; boundary pending/no=16/3; not merged")


if __name__ == "__main__":
    main()
