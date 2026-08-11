#!/usr/bin/env python3
"""Build historical fast-review batch 13-F from the fixed v20 worktable.

The three issuers are dairy companies.  Consolidated external revenue from
own-farm raw milk is separated from dairy processing wherever possible.  A
broad liquid/dairy category is never treated wholesale as initial processing
when the annual report does not split plain milk from yoghurt, milk drinks,
powder, ice cream or other deep-processed/traded products.
"""
from decimal import Decimal, getcontext
from pathlib import Path

import pandas as pd


getcontext().prec = 60
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v20_跨年快速复核第十批.csv"
OUTPUT = ROOT / "outputs" / "跨年快速复核第十三批_F组_3家公司.csv"

# All amounts are consolidated external revenue/cost in yuan.
#
# Yantang: `initial` is the separately disclosed liquid-milk category, accepted
# as the confirmed initial-processing lower bound consistently with the already
# audited 2023 row.  `other` is only an upper bound for possible external raw
# milk/other direct agricultural revenue; self-farm milk consumed internally is
# eliminated on consolidation and must not be added again.
YANTANG = {
    2014: dict(initial="299214880.52", initial_cost="220249527.07", other="8142084.39", total="949910341.16", page="14|15"),
    2015: dict(initial="305179286.33", initial_cost="219085441.80", other="9270694.76", total="1032433862.00", page="13|14"),
    2018: dict(initial="407117671.20", initial_cost="298396751.06", other="12211324.97", total="1297195799.52", page="15|16"),
    2019: dict(initial="493327206.63", initial_cost="356363087.10", other="15057585.96", total="1470757199.10", page="15|16"),
    2020: dict(initial="580287694.58", initial_cost="471068260.03", other="12233840.33", total="1636997322.03", page="18|19"),
    2021: dict(initial="743031619.52", initial_cost="620932267.25", other="21227644.35", total="1984746938.46", page="21|22"),
    2022: dict(initial="723570181.92", initial_cost="633874347.83", other="29369254.52", total="1875194458.16", page="21|22"),
}

# Sanyuan: liquid milk mixes plain/fresh milk with fermented and other dairy
# products, so it is upper-bound evidence only.  Before 2022 no external
# husbandry category was separately disclosed.  The amounts previously mistaken
# for a non-dairy/husbandry residual are merely total revenue less main-business
# revenue (the 2020 report expressly labels this difference unrelated to main
# business), so they are retained only as excluded audit evidence and never enter
# an agricultural bound.  In 2022 the separately disclosed husbandry category is
# an upper bound because raw milk versus feed/trade is not split.
SANYUAN = {
    2014: dict(liquid="3256085514.31", liquid_cost="2383039685.20", agri_upper="0", agri_cost="", excluded_other="103883874.42", total="4502477062.70", page="9|10"),
    2015: dict(liquid="3210740638.08", liquid_cost="2202544250.62", agri_upper="0", agri_cost="", excluded_other="147963150.33", total="4549865271.00", page="11"),
    2018: dict(liquid="4003435046.33", liquid_cost="2813595263.14", agri_upper="0", agri_cost="", excluded_other="171004019.76", total="7455843969.76", page="12|13"),
    2019: dict(liquid="4559010613.28", liquid_cost="3235798700.69", agri_upper="0", agri_cost="", excluded_other="73198446.58", total="8150710056.90", page="11|12"),
    2020: dict(liquid="4308134165.95", liquid_cost="3582532203.63", agri_upper="0", agri_cost="", excluded_other="65446370.85", total="7353344572.09", page="12|13"),
    2021: dict(liquid="4775039226.99", liquid_cost="3813873390.98", agri_upper="0", agri_cost="", excluded_other="98120748.85", total="7730723573.43", page="13"),
    2022: dict(liquid="4657372879.02", liquid_cost="3420258309.08", agri_upper="794162778.71", agri_cost="787842339.39", excluded_other="", total="8002540295.90", page="18|19"),
}

# Bright Dairy: from 2015 onward the separately disclosed husbandry category
# contains external raw milk together with farm-product/feed trade in at least
# some years.  It is an upper bound, never an exact own-farm numerator.  In 2014
# no husbandry category was disclosed: 1,311,410,342 is an arithmetic residual,
# while the report's actual "other" category is 1,156,478,482; neither amount is
# automatically agricultural and both are excluded.  Liquid milk also mixes
# fresh milk, yoghurt, UHT milk and dairy drinks and is expanded-upper only.
BRIGHT = {
    2014: dict(liquid="15090409419", liquid_cost="8665017889", agri_upper="0", agri_cost="", excluded_residual="1311410342", excluded_other="1156478482", total="20385061873", page="12"),
    2015: dict(liquid="14265584772", liquid_cost="8010074885", agri_upper="1615274783", agri_cost="1456323528", excluded_residual="", excluded_other="", total="19373193032", page="9|10"),
    2018: dict(liquid="12430045464", liquid_cost="6828891535", agri_upper="2382422630", agri_cost="2140837169", excluded_residual="", excluded_other="", total="20985560398", page="11|12"),
    2019: dict(liquid="13801692502", liquid_cost="8108866369", agri_upper="1669266858", agri_cost="1464010025", excluded_residual="", excluded_other="", total="22563236819", page="11|12"),
    2020: dict(liquid="14268883149", liquid_cost="9405892312", agri_upper="2026991952", agri_cost="1797049024", excluded_residual="", excluded_other="", total="25222715966", page="13"),
    2021: dict(liquid="17100958314", liquid_cost="12458225574", agri_upper="2289551805", agri_cost="2222630389", excluded_residual="", excluded_other="", total="29205992515", page="16|17"),
    2022: dict(liquid="16091187442", liquid_cost="11894457432", agri_upper="2640585610", agri_cost="2605007821", excluded_residual="", excluded_other="", total="28214908036", page="14"),
}


def raw(n: Decimal, d: Decimal) -> str:
    return format(n / d, "f")


def threshold(lower: Decimal, upper: Decimal) -> str:
    if lower >= Decimal("0.50"):
        return "是"
    if upper < Decimal("0.50"):
        return "否"
    return "待核实"


def boundary(lower: Decimal, upper: Decimal) -> str:
    if lower >= Decimal("0.50") or upper < Decimal("0.30"):
        return "否"
    if lower >= Decimal("0.30") and upper < Decimal("0.50"):
        return "是"
    return "待核实"


def compact(value: str) -> str:
    return value.replace(",", "").replace(" ", "").replace("\n", "")


def main() -> None:
    src = pd.read_csv(SOURCE, dtype={"股票代码": str}, keep_default_na=False)
    target = src[
        src["股票代码"].isin(["002732", "600429", "600597"])
        & src["复核状态"].str.startswith("年报及业务表已定位", na=False)
    ].sort_values(["股票代码", "年份"])
    assert len(target) == 21
    assert target.groupby("股票代码").size().to_dict() == {"002732": 7, "600429": 7, "600597": 7}
    assert not target.duplicated(["股票代码", "年份"]).any()

    rows = []
    for _, s in target.iterrows():
        code, year = s["股票代码"], int(s["年份"])
        if code == "002732":
            v = YANTANG[year]
            total = Decimal(v["total"])
            strict_lo, strict_hi = Decimal("0"), Decimal(v["other"])
            expanded_lo = Decimal(v["initial"])
            expanded_hi = expanded_lo + strict_hi
            strict_formula = f"下界=0；上界=其他收入{v['other']}（仅作可能外销原奶/农业收入上限）"
            expanded_formula = f"下界=液体乳类{v['initial']}；上界=液体乳类{v['initial']}+其他{v['other']}"
            strict_business = "自有牧场原奶：内部供加工不形成合并外部收入；其他收入仅作上界"
            expanded_business = "液体乳类（可确认原奶初加工）；花式奶、乳酸菌饮料、冰淇淋排除"
            mixed_note = "液体乳类单列，按已核实2023一致口径作为初加工；自有牧场内部原奶不得与成品收入重复相加。"
            liquid, liquid_cost = v["initial"], v["initial_cost"]
            agri_cost = ""
        elif code == "600429":
            v = SANYUAN[year]
            total = Decimal(v["total"])
            strict_lo, strict_hi = Decimal("0"), Decimal(v["agri_upper"])
            expanded_lo = Decimal("0")
            expanded_hi = strict_hi + Decimal(v["liquid"])
            if year < 2022:
                strict_formula = "下界=上界=0（当年未单列畜牧业外部收入；其他业务收入不属于农业证据）"
                expanded_formula = f"下界=0；上界=液态奶{v['liquid']}"
                strict_business = "当年未披露可识别的合并外部农业生产收入"
                excluded_note = (
                    f"排除营业收入与主营业务收入的差额（其他业务收入）{v['excluded_other']}："
                    "该值不是畜牧业披露，2020年报还明示当年差额与主营业务无关。"
                )
            else:
                strict_formula = f"下界=0；上界=畜牧业{v['agri_upper']}（原奶与饲料/贸易未拆）"
                expanded_formula = f"下界=0；上界=畜牧业{v['agri_upper']}+液态奶{v['liquid']}"
                strict_business = "畜牧业外部收入未拆分自产原奶与饲料/贸易，仅作严格上界"
                excluded_note = ""
            expanded_business = "液态奶大类混合纯奶、发酵奶等产品，仅作扩展上界"
            mixed_note = (
                "液态奶未拆原奶初加工与发酵等深加工，扩展正式分子留空；"
                "固态奶、冰淇淋、涂抹酱不计入。" + excluded_note
            )
            liquid, liquid_cost = v["liquid"], v["liquid_cost"]
            agri_cost = v["agri_cost"]
        else:
            v = BRIGHT[year]
            total = Decimal(v["total"])
            strict_lo, strict_hi = Decimal("0"), Decimal(v["agri_upper"])
            expanded_lo = Decimal("0")
            expanded_hi = strict_hi + Decimal(v["liquid"])
            if year == 2014:
                strict_formula = "下界=上界=0（年报未披露牧业收入；算术残差及‘其他’均排除）"
                expanded_formula = f"下界=0；上界=液态奶{v['liquid']}"
                strict_business = "年报未单列牧业或可识别的合并外部农业生产收入"
                excluded_note = (
                    f"总收入减液态奶及其他乳制品的算术残差{v['excluded_residual']}不是牧业披露；"
                    f"年报‘其他’{v['excluded_other']}也无农业属性证据，二者均排除。"
                )
            else:
                strict_formula = f"下界=0；上界=牧业{v['agri_upper']}（含潜在农牧产品/饲料贸易）"
                expanded_formula = f"下界=0；上界=牧业{v['agri_upper']}+液态奶{v['liquid']}"
                strict_business = "自有牧场原奶与农牧产品/饲料贸易未拆，已披露牧业类仅作上界"
                excluded_note = ""
            expanded_business = "液态奶混合鲜奶、酸奶、常温奶及乳饮料，仅作扩展上界"
            mixed_note = (
                "液态奶未拆初深加工，不直接写入正式分子。"
                + (excluded_note if year == 2014 else "年报明确部分年度牧业收入含农牧产品贸易，牧业类也不直接写入正式分子。")
            )
            liquid, liquid_cost = v["liquid"], v["liquid_cost"]
            agri_cost = v["agri_cost"]

        # Revenue/cost reversal guards and consolidated P&L denominator check.
        assert Decimal(liquid) != Decimal(liquid_cost)
        if agri_cost:
            assert strict_hi != Decimal(agri_cost)
        assert compact(v["total"]) in compact(s["利润表原文摘录"]), (code, year, "P&L denominator missing")
        assert Decimal("0") <= strict_lo <= strict_hi <= total
        assert strict_lo <= expanded_lo <= expanded_hi <= total

        sr_lo, sr_hi = strict_lo / total, strict_hi / total
        er_lo, er_hi = expanded_lo / total, expanded_hi / total
        strict_conclusion = threshold(sr_lo, sr_hi)
        expanded_conclusion = threshold(er_lo, er_hi)
        boundary_conclusion = boundary(er_lo, er_hi)
        exact_expanded = expanded_lo == expanded_hi

        rows.append({
            "股票代码": code,
            "公司全称": s["公司全称"],
            "年份": year,
            "行业分类代码": s["行业分类代码"] or "待核实",
            "行业分类名称": s["行业分类名称"] or "待核实",
            "严格口径涉农业务": strict_business,
            "严格口径正式涉农收入_元": f"{strict_lo:.2f}" if strict_lo == strict_hi else "",
            "严格口径收入下界_元": f"{strict_lo:.2f}",
            "严格口径收入上界_元": f"{strict_hi:.2f}",
            "严格口径上下界公式": strict_formula,
            "严格口径下界占比_原始未四舍五入": raw(strict_lo, total),
            "严格口径上界占比_原始未四舍五入": raw(strict_hi, total),
            "扩展口径涉农业务": expanded_business,
            "扩展口径正式涉农收入_元": f"{expanded_lo:.2f}" if exact_expanded else "",
            "扩展口径收入下界_元": f"{expanded_lo:.2f}",
            "扩展口径收入上界_元": f"{expanded_hi:.2f}",
            "扩展口径上下界公式": expanded_formula,
            "扩展口径下界占比_原始未四舍五入": raw(expanded_lo, total),
            "扩展口径上界占比_原始未四舍五入": raw(expanded_hi, total),
            "公司营业收入_元": f"{total:.2f}",
            "公司营业收入公式": "合并利润表‘营业收入’（非自行汇总分部收入）",
            "液态或液体乳收入_元_初加工候选或上界": liquid,
            "液态或液体乳成本_元_反向证据": liquid_cost,
            "农业生产候选收入上界_元": f"{strict_hi:.2f}",
            "农业相关成本_元_反向证据": agri_cost,
            "收入成本判别": "采用营业收入列；成本仅作反向证据，未进入分子",
            "严格样本结论": strict_conclusion,
            "扩展样本结论": expanded_conclusion,
            "边界样本结论": boundary_conclusion,
            "是否存在分部收入重叠": "存在潜在口径重叠；内部原奶不与乳制品成品收入相加，上下界采用同一产品/行业层级",
            "纳入或剔除理由": (
                f"严格区间[{raw(strict_lo,total)}, {raw(strict_hi,total)}]；"
                f"扩展区间[{raw(expanded_lo,total)}, {raw(expanded_hi,total)}]。{mixed_note}"
            ),
            "待核实点": (
                "需取得产品明细或分部附注明确外销自产原奶、初加工乳品、深加工乳品及贸易收入；"
                "未拆分前不得按上界写入正式分子。"
            ),
            "收入分项证据PDF页序号": v["page"],
            "公司营业收入证据PDF页序号": s["利润表PDF页序号"],
            "年报链接": s["年报链接"],
            "记录类型": "跨年快速复核第十三批F组（未合并）",
            "复核状态": "已人工复核（第十三批F组；主表未合并）",
            "复核日期": "2026-08-11",
        })

    out = pd.DataFrame(rows)
    assert len(out) == 21 and not out.duplicated(["股票代码", "年份"]).any()
    assert out["严格样本结论"].value_counts().to_dict() == {"否": 21}
    assert out["扩展样本结论"].value_counts().to_dict() == {"待核实": 14, "否": 7}
    assert out["边界样本结论"].value_counts().to_dict() == {"待核实": 15, "是": 6}
    sanyuan_pre2022 = out["股票代码"].eq("600429") & out["年份"].lt(2022)
    assert out.loc[sanyuan_pre2022, "严格口径收入上界_元"].eq("0.00").all()
    assert all(
        Decimal(upper) == Decimal(liquid)
        for upper, liquid in zip(
            out.loc[sanyuan_pre2022, "扩展口径收入上界_元"],
            out.loc[sanyuan_pre2022, "液态或液体乳收入_元_初加工候选或上界"],
        )
    )
    bright_2014 = out["股票代码"].eq("600597") & out["年份"].eq(2014)
    assert out.loc[bright_2014, "严格口径收入上界_元"].eq("0.00").all()
    assert out.loc[bright_2014, "农业相关成本_元_反向证据"].eq("").all()
    assert all(
        Decimal(upper) == Decimal(liquid)
        for upper, liquid in zip(
            out.loc[bright_2014, "扩展口径收入上界_元"],
            out.loc[bright_2014, "液态或液体乳收入_元_初加工候选或上界"],
        )
    )
    uncertain = out["扩展样本结论"].eq("待核实")
    assert out.loc[uncertain, "扩展口径正式涉农收入_元"].eq("").all()
    assert out["年报链接"].str.startswith("https://static.cninfo.com.cn/").all()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("batch13-F rows=21; strict no=21; expanded pending=14/no=7; boundary pending=15/yes=6; not merged")


if __name__ == "__main__":
    main()
