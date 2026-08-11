#!/usr/bin/env python3
"""Build medicinal-company fast-review batch 15-K from the fixed v24 table.

Finished Chinese/chemical medicines and medical services are not agriculture.
Medicinal-herb bases or subsidiary business scopes do not establish external
agricultural revenue.  Mixed herb sales/other-industry rows are only upper
bounds unless the annual report separately labels cultivation revenue.
"""
from decimal import Decimal, getcontext
from pathlib import Path

import pandas as pd


getcontext().prec = 60
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v24_跨年快速复核第十四批第一组.csv"
OUTPUT = ROOT / "outputs" / "跨年快速复核第十五批_K组_3家公司.csv"


# year: consolidated operating revenue, cultivation/other-industry upper,
# related row cost, business-table pages.  Only 2014 is explicitly labelled
# "cultivation industry" and therefore forms an exact direct-agriculture value.
XINBANG = {
    2014: ("2476183059.91", "5685105.29", "3763641.91", "17"),
    2015: ("4179756099.15", "5386105.48", "2708079.33", "18|20"),
    2018: ("6580278918.05", "25452578.02", "18164672.28", "14|16"),
    2019: ("6655063577.50", "35296705.73", "25634032.46", "15|17"),
    2020: ("5845621525.69", "51003929.55", "37740036.00", "16|18"),
    2021: ("6471866334.96", "14286876.15", "12259464.98", "23|25"),
    2022: ("6350025827.03", "8605144.68", "4668387.62", "25|28"),
}


# year: consolidated operating revenue, mixed herb-sale revenue and cost,
# separately disclosed fertiliser-input revenue and cost, pages.
BAILING = {
    2014: ("1574672162.30", "8992647.10", "4049224.37", "5355144.56", "3583263.64", "15"),
    2015: ("1899087619.14", "43109781.16", "40538338.88", "8695730.97", "4657648.24", "19|20"),
    2018: ("3136843231.96", "121449676.91", "128417218.81", "8090329.35", "4559796.43", "16|18"),
    2019: ("2850585250.74", "31613537.81", "22794797.94", "5590629.55", "3685217.21", "18|20"),
    2020: ("3087888201.57", "8456920.89", "5986092.45", "13042770.44", "8552040.38", "19|21"),
    2021: ("3111649547.82", "3495954.90", "0", "0", "0", "20"),
    2022: ("3540132272.77", "2455834.92", "0", "0", "0", "21"),
}


# Aodong does not separately report consolidated external revenue from its deer
# breeding/cultivation activities or agricultural inputs.  Deer-industry and
# cultivation evidence means that zero is only a lower bound: the eligible
# revenue may be internally supplied or mixed into food, Chinese-medicine or
# other rows.  No numeric upper bound can therefore be inferred from the annual
# reports, and "other industry" must not be wholly relabelled as gelatin or any
# other single activity.
AODONG = {
    2014: ("2240099344.17", "16"),
    2015: ("2334760837.13", "13"),
    2018: ("3324078265.78", "15"),
    2019: ("3088379591.97", "15"),
    2020: ("2251650950.38", "18"),
    2021: ("2303763763.87", "29"),
    2022: ("2868211464.89", "32"),
}


AODONG_EVIDENCE = {
    2014: (
        "年报披露消耗性生物资产、梅花鹿生产性生物资产及农林牧渔业项目所得减免税，"
        "证明存在农业活动；但未披露其合并外销收入。",
        "16|98|107|117",
    ),
    2015: (
        "年报披露中药材种植、畜牧养殖/梅花鹿业务及消耗性生物资产，"
        "但相关收入可能内部供料或混入食品、中药及其他收入，无法拆分。",
        "13|37|77|98",
    ),
    2018: (
        "年报明确提及梅花鹿饲养产业和药材种植业，并披露生物资产及相关免税信息；"
        "合并收入表未单列相应外销收入。",
        "15|46|117|132",
    ),
    2019: (
        "年报明确提及梅花鹿饲养产业和药材种植业，并披露生产性生物资产及鹿业免税；"
        "相关外销收入未单列。",
        "15|43|125|147",
    ),
    2020: (
        "年报披露新设吉林敖东红石鹿业有限责任公司，经营梅花鹿养殖、鹿副产品、"
        "中药材种植及农业初加工服务；合并收入未按这些活动拆分。",
        "18|20|27|152",
    ),
    2021: (
        "年报继续披露红石鹿业、畜牧业改造工程、梅花鹿和淫羊藿生产性生物资产及农林牧渔免税；"
        "未单列对应合并外销收入。",
        "29|41|165|185",
    ),
    2022: (
        "年报继续披露红石鹿业；本年收购的仁和农作物购买日至年末收入为0，"
        "但该0仅属于被购买方该期间，不能代表其他鹿业或种植活动为0；"
        "同时披露新设经营中草药种植、种苗及肥药等业务的主体，合并收入仍无法拆分。",
        "32|35|46|98|235|238",
    ),
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
    src = pd.read_csv(SOURCE, dtype={"股票代码": str}, keep_default_na=False)
    target = src[
        src["股票代码"].isin(["002390", "002424", "000623"])
        & src["复核状态"].str.startswith("年报及业务表已定位", na=False)
    ].sort_values(["股票代码", "年份"])
    assert len(src) == 958
    assert len(target) == 21
    assert target.groupby("股票代码").size().to_dict() == {"000623": 7, "002390": 7, "002424": 7}
    assert not target.duplicated(["股票代码", "年份"]).any()

    rows = []
    for _, s in target.iterrows():
        code, year = s["股票代码"], int(s["年份"])
        strict_lo = expanded_lo = D("0")
        herb_cost = input_cost = D("0")
        precision_note = ""
        locator_note = ""

        if code == "002390":
            total_s, mixed_s, cost_s, pages = XINBANG[year]
            total, mixed, herb_cost = D(total_s), D(mixed_s), D(cost_s)
            if year == 2014:
                strict_hi = expanded_hi = mixed
                strict_lo = expanded_lo = mixed
                strict_business = "年报单列种植业（中药材）"
                strict_formula = expanded_formula = f"下界=上界=种植业{mixed:.2f}"
                note = "种植业行与中药材产品行金额一致，为同层级表格的相互反核，不重复相加。"
            else:
                strict_hi = expanded_hi = mixed
                strict_business = "其他行业混合项中可能包含中药材种植/初加工（仅作上界）"
                strict_formula = expanded_formula = f"下界=0；上界=其他行业{mixed:.2f}"
                note = "年报只列‘其他行业/其他产品’；基地、子公司经营范围及税收优惠不能把混合项改写为种植收入。"
            expanded_business = strict_business
            cost_note = f"对应种植业/其他行业行成本{herb_cost:.2f}，仅作反向证据"
            pending = "需取得其他行业的外销中药材种植或初加工收入明细；未拆分前不写入正式分子。"
            evidence_keyword = "种植业" if year == 2014 else "其他行业"
            if year == 2022:
                locator_note = "v24主营业务摘录从PDF页26的地区行开始；收入混合行回到PDF页25，对应成本在PDF页28。"
        elif code == "002424":
            total_s, herb_s, herb_cost_s, fertiliser_s, fertiliser_cost_s, pages = BAILING[year]
            total, herb, herb_cost = D(total_s), D(herb_s), D(herb_cost_s)
            fertiliser, input_cost = D(fertiliser_s), D(fertiliser_cost_s)
            strict_hi = herb
            expanded_lo, expanded_hi = fertiliser, fertiliser + herb
            strict_business = "中药材销售混合项（可能含自产种植，也存在贸易，仅作上界）"
            expanded_business = "肥料销售作农业投入品下界；中药材混合销售只作上界"
            strict_formula = f"下界=0；上界=中药材销售{herb:.2f}"
            expanded_formula = f"下界=肥料销售{fertiliser:.2f}；上界=下界+中药材销售{herb:.2f}"
            cost_note = (
                "中药材及农业投入品对应产品成本未单列，不作0值、不估算"
                if year >= 2021 else
                f"中药材销售成本{herb_cost:.2f}；肥料销售成本{input_cost:.2f}；成本仅作收入列反核"
            )
            note = "2014年年报明示中药材贸易增长；后续年份亦未把自产种植与外购贸易拆分，故中药材项不形成确定下界。"
            pending = "需取得中药材销售中自产种植/初加工与外购贸易的分拆；2021—2022年产品成本亦未单列。"
            evidence_keyword = "中药材"
            if year == 2021:
                precision_note = (
                    "采用2021年当年报告营业收入3,111,649,547.82元；"
                    "2022年比较栏重列为3,111,123,827.82元，不以后续比较数覆盖。"
                )
            if year == 2014:
                locator_note = "v24主营业务摘录落在PDF页16的表后页；中药材/肥料收入与成本均在PDF页15。"
            elif year == 2021:
                locator_note = "v24主营业务摘录从PDF页21的地区行开始；中药材产品收入在PDF页20。"
        else:
            total_s, pages = AODONG[year]
            total = D(total_s)
            strict_hi = expanded_hi = None
            strict_business = "梅花鹿养殖、鹿业及中药材种植等直接农业活动（合并外销收入未拆分）"
            expanded_business = "严格口径活动及种苗、肥药等农业投入品（合并外销收入未拆分）"
            strict_formula = expanded_formula = "下界=0；上界无法数值拆分（不得以未单列推定为0）"
            cost_note = "合格农业收入及对应成本未单列；不把成本、资产余额或经营范围估算为收入"
            evidence, pages = AODONG_EVIDENCE[year]
            note = (
                f"{evidence}梅花鹿/鹿业、中草药种植收入可能用于内部供料，"
                "也可能混入食品、中药或其他收入；不能把‘其他行业’全部解释为明胶等专用化学品。"
            )
            pending = (
                "需取得鹿业、种植、初加工及农业投入品的合并外销收入，并剔除内部交易；"
                "未拆分前严格、扩展和边界结论均保持待核实。"
            )
            evidence_keyword = "中成药" if year != 2022 else "中药"

        assert D("0") <= strict_lo <= total
        assert D("0") <= expanded_lo <= total
        assert strict_hi is None or strict_lo <= strict_hi <= total
        assert expanded_hi is None or expanded_lo <= expanded_hi <= total
        assert herb_cost >= 0 and input_cost >= 0
        # Three v24 excerpts start on the page immediately after the relevant
        # table; the corrected page locators above were checked in the PDFs.
        excerpt_page_misses = {("002424", 2014), ("002424", 2021), ("002390", 2022)}
        assert evidence_keyword in s["主营业务表原文摘录"] or (code, year) in excerpt_page_misses
        assert compact(str(total)) in compact(s["利润表原文摘录"])

        sr_lo = strict_lo / total
        er_lo = expanded_lo / total
        sr_hi = None if strict_hi is None else strict_hi / total
        er_hi = None if expanded_hi is None else expanded_hi / total
        if strict_hi is None or expanded_hi is None:
            strict_result = expanded_result = boundary_result = "待核实"
        else:
            strict_result = threshold(sr_lo, sr_hi)
            expanded_result = threshold(er_lo, er_hi)
            boundary_result = boundary(er_lo, er_hi)
        rows.append({
            "股票代码": code,
            "公司全称": s["公司全称"],
            "年份": year,
            "行业分类代码": s["行业分类代码"] or "待核实",
            "行业分类名称": s["行业分类名称"] or "待核实",
            "严格口径涉农业务": strict_business,
            "严格口径正式涉农收入_元": f"{strict_lo:.2f}" if strict_result == "是" else "",
            "严格口径收入下界_元": f"{strict_lo:.2f}",
            "严格口径收入上界_元": "" if strict_hi is None else f"{strict_hi:.2f}",
            "严格口径上下界公式": strict_formula,
            "严格口径下界占比_原始未四舍五入": ratio(strict_lo, total),
            "严格口径上界占比_原始未四舍五入": "" if strict_hi is None else ratio(strict_hi, total),
            "扩展口径涉农业务": expanded_business,
            "扩展口径正式涉农收入_元": f"{expanded_lo:.2f}" if expanded_result == "是" else "",
            "扩展口径收入下界_元": f"{expanded_lo:.2f}",
            "扩展口径收入上界_元": "" if expanded_hi is None else f"{expanded_hi:.2f}",
            "扩展口径上下界公式": expanded_formula,
            "扩展口径下界占比_原始未四舍五入": ratio(expanded_lo, total),
            "扩展口径上界占比_原始未四舍五入": "" if expanded_hi is None else ratio(expanded_hi, total),
            "公司营业收入_元": f"{total:.2f}",
            "公司营业收入公式": "合并利润表营业收入",
            "中药材或混合项成本_元_反向证据": f"{herb_cost:.2f}" if herb_cost else "",
            "农业投入品成本_元_反向证据": f"{input_cost:.2f}" if input_cost else "",
            "收入成本判别": cost_note,
            "严格样本结论": strict_result,
            "扩展样本结论": expanded_result,
            "边界样本结论": boundary_result,
            "是否存在分部收入重叠": (
                "待核实（农业活动可能内部供料或混入食品、中药及其他收入，未作机械相加）"
                if strict_hi is None else
                "否（同一收入构成层级设上下界，不与行业/产品行交叉相加）"
            ),
            "纳入或剔除理由": (
                f"严格区间[{ratio(strict_lo,total)}, "
                f"{'待拆分' if strict_hi is None else ratio(strict_hi,total)}]；"
                f"扩展区间[{ratio(expanded_lo,total)}, "
                f"{'待拆分' if expanded_hi is None else ratio(expanded_hi,total)}]。{note}"
            ),
            "金额精度或追溯说明": precision_note,
            "证据定位更正说明": locator_note,
            "待核实点": pending,
            "年报主营业务证据PDF页序号": pages,
            "公司营业收入证据PDF页序号": s["利润表PDF页序号"],
            "年报链接": s["年报链接"],
            "2022行业字段处理": "沿用v24原值；待核实字段不插值、不复制相邻年份",
            "记录类型": "跨年快速复核第十五批K组（未合并）",
            "复核状态": "已人工复核（第十五批K组；主表未合并）",
            "复核日期": "2026-08-11",
        })

    out = pd.DataFrame(rows)
    assert len(out) == 21 and not out.duplicated(["股票代码", "年份"]).any()
    expected_results = {"否": 14, "待核实": 7}
    assert out["严格样本结论"].value_counts().to_dict() == expected_results
    assert out["扩展样本结论"].value_counts().to_dict() == expected_results
    assert out["边界样本结论"].value_counts().to_dict() == expected_results
    assert out.loc[out["年份"].eq(2022), "行业分类代码"].eq("待核实").all()
    assert out.loc[out["年份"].eq(2022), "行业分类名称"].eq("待核实").all()
    aodong = out.loc[out["股票代码"].eq("000623")]
    assert aodong["严格口径正式涉农收入_元"].eq("").all()
    assert aodong["扩展口径正式涉农收入_元"].eq("").all()
    assert aodong["严格口径收入下界_元"].eq("0.00").all()
    assert aodong["扩展口径收入下界_元"].eq("0.00").all()
    assert aodong["严格口径收入上界_元"].eq("").all()
    assert aodong["扩展口径收入上界_元"].eq("").all()
    assert aodong[["严格样本结论", "扩展样本结论", "边界样本结论"]].eq("待核实").all().all()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("batch15-K rows=21; each result: no=14, pending=7; not merged")


if __name__ == "__main__":
    main()
