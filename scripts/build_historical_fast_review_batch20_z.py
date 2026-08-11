#!/usr/bin/env python3
"""Build standalone historical fast-review batch 20-Z from fixed v31.

The source table is read-only. Pharmaceutical products, seasonings, braised
snacks, bakery/ready-to-eat food and dairy deep processing are excluded.
Yiming's mixed dairy line is only an expanded-scope upper bound. Consistent
with the already verified 2023 Andeli record, concentrated juice, essence and
pomace are treated as fruit primary processing in the expanded scope.
"""
from decimal import Decimal, getcontext
from pathlib import Path

import pandas as pd


getcontext().prec = 60
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v31_跨年快速复核第十九批.csv"
OUTPUT = ROOT / "outputs" / "跨年快速复核第二十批_Z组_6家公司.csv"

# company revenue/cost; disclosed main-business revenue/cost (yuan).
EXCLUDED = {
    "600351": {
        2019: ("3041915898.58", "1108100201.09", "3022731991.14", "1100714263.90"),
        2020: ("2602423106.49", "1058707121.97", "2555577668.38", "1042349372.11"),
        2021: ("2763962481.58", "1077119320.29", "2680757653.59", "1022227451.98"),
        2022: ("2718134785.52", "1199375631.96", "2680682795.66", "1183150356.03"),
    },
    "603317": {
        # Annual-report tables are in RMB 10,000 and are converted to yuan.
        2019: ("1727329107.54", "1083250464.25", "1717183500.00", "1074084400.00"),
        2020: ("2364655862.43", "1383495404.97", "2363672600.00", "1383206400.00"),
        2021: ("2025535449.58", "1372877842.63", "2023928800.00", "1369941700.00"),
        2022: ("2690710152.71", "1769938971.73", "2689357800.00", "1768962700.00"),
    },
    "603517": {
        2020: ("5276079668.28", "3509503135.43", "5138913736.65", "3426637986.60"),
        2021: ("6548621784.04", "4474155778.22", "6351831491.27", "4315334594.71"),
        2022: ("6622839829.55", "4929448355.22", "6452465855.48", "4799969962.55"),
    },
    "605338": {
        2020: ("975090303.83", "703069210.97", "974211108.11", "702812031.80"),
        2021: ("1375446232.93", "1022000212.70", "1374617712.24", "1021896176.73"),
        2022: ("1525141412.03", "1102557261.75", "1523883991.40", "1102485774.70"),
    },
}

# company revenue/cost; food main revenue/cost; mixed dairy revenue/cost.
YIMING = {
    2020: ("1947177891.01", "1167537174.13", "1810982977.83", "1078086496.04", "1033660376.63", "617694032.54"),
    2021: ("2316379444.25", "1596599300.52", "2115503055.68", "1421016152.33", "1124943023.21", "763242483.86"),
    2022: ("2432551533.24", "1714703675.05", "2237121962.45", "1540789874.10", "1178091007.56", "821104755.70"),
}

# company revenue/cost; eligible juice/essence/pomace main revenue/cost.
ANDELI = {
    2020: ("842019695.12", "640995527.94", "835579859.39", "638702439.05"),
    2021: ("871587320.36", "691914568.76", "861917167.76", "687127067.00"),
    2022: ("1065429309.28", "852294128.44", "1053115862.71", "845280946.57"),
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
    return {
        ("600351", 2020): "73",
        ("603317", 2022): "73",
        ("603517", 2020): "73",
        ("603517", 2021): "87",
    }.get((code, year), original)


def main() -> None:
    source = pd.read_csv(SOURCE, dtype={"股票代码": str}, keep_default_na=False)
    wanted = {
        "600351": {2019, 2020, 2021, 2022},
        "603317": {2019, 2020, 2021, 2022},
        "603517": {2020, 2021, 2022},
        "605179": {2020, 2021, 2022},
        "605198": {2020, 2021, 2022},
        "605338": {2020, 2021, 2022},
    }
    selected = source[source.apply(lambda r: r["股票代码"] in wanted and int(r["年份"]) in wanted[r["股票代码"]], axis=1)].copy()
    selected = selected.sort_values(["股票代码", "年份"])
    assert len(source) == 958 and len(selected) == 20
    assert selected.groupby("股票代码").size().to_dict() == {
        "600351": 4, "603317": 4, "603517": 3, "605179": 3, "605198": 3, "605338": 3
    }
    assert selected["复核状态"].str.startswith("年报及业务表已定位", na=False).all()
    assert not selected.duplicated(["股票代码", "年份"]).any()

    rows = []
    for _, src in selected.iterrows():
        code, year = src["股票代码"], int(src["年份"])
        eligible_revenue = eligible_cost = mixed_revenue = mixed_cost = D("0")
        unclassified_upper = D("0")

        if code in EXCLUDED:
            total, total_cost, disclosed_revenue, disclosed_cost = map(D, EXCLUDED[code][year])
            strict_lo = expanded_lo = D("0")
            if code == "603517":
                # The separately labelled "other" industry is not established as
                # qualifying activity, but is retained as a conservative bound.
                other = {2020: D("173356347.43"), 2021: D("541345847.45"), 2022: D("728044404.89")}[year]
                strict_hi = expanded_hi = unclassified_upper = other
                strict_business = expanded_business = "未单列直接农业或合格初加工收入；分行业“其他”仅作保守上界"
                strict_formula = expanded_formula = f"下界=0；上界=未拆分行业其他{other:.2f}"
                excluded_label = "鲜货卤制品、包装卤制品及加盟管理等休闲食品/服务"
                reason = "禽畜蔬菜是卤制食品原料或成品类别，不等于上市公司直接养殖或农产品初加工；未拆“其他”不估算。"
                pending = "分行业“其他”性质未拆，但上下界均低于30%，不影响严格、扩展及边界结论。"
            else:
                strict_hi = expanded_hi = D("0")
                strict_formula = expanded_formula = "下界=上界=0（无单列合格涉农外销收入）"
                if code == "600351":
                    strict_business = expanded_business = "未单列中药材种植、初加工或农业投入品收入"
                    excluded_label = "药品生产、医药批发及原料药等其他贸易"
                    reason = "药品及医药流通属于医药制造/贸易；药材采购、药品名称或原料药不能替代直接种植、初加工外销收入。"
                elif code == "603317":
                    strict_business = expanded_business = "未单列直接农业生产或农产品初加工收入"
                    excluded_label = "火锅调料、中式菜品调料、香肠腊肉调料、鸡精、香辣酱及其他调味品"
                    reason = "调味品属于食品深加工；采购辣椒、花椒等农产品不等于公司直接农业或初加工收入。"
                else:
                    strict_business = expanded_business = "未单列直接农业生产或农产品初加工收入"
                    excluded_label = "面点/面米、馅料、外购食品、包装辅料及加盟管理"
                    reason = "面点、馅料等即食食品属于深加工，外购食品、包装辅料和加盟管理不属于农业生产或初加工。"
                pending = "年报业务类别均可按既定规则排除；未用原料采购、产销量或成本反推收入。"
            cost_note = f"披露主营业务收入{disclosed_revenue:.2f}、成本{disclosed_cost:.2f}，仅作排除口径反向核对"
            evidence_extra = "天味主营业务表单位为万元，脚本按×10000换算为元。" if code == "603317" else "分行业与分产品是重叠维度，只使用分行业/合计一次，不机械相加。"
        elif code == "605179":
            total, total_cost, disclosed_revenue, disclosed_cost, mixed_revenue, mixed_cost = map(D, YIMING[year])
            strict_lo = strict_hi = expanded_lo = D("0")
            expanded_hi = mixed_revenue
            strict_business = "未单列合并口径外销原奶或活畜收入；内部奶源不重复计入"
            expanded_business = "乳品混合巴氏杀菌乳与发酵乳、调制乳及特色乳饮品，仅作扩展上界"
            strict_formula = "下界=上界=0（无单列合并口径外销原奶/活畜收入）"
            expanded_formula = f"下界=0；上界=未拆乳品收入{mixed_revenue:.2f}"
            excluded_label = "烘焙、其他食品，以及乳品中的发酵乳、调制乳和乳饮品"
            reason = "自有牧场主要供应内部奶源，不形成可重复计入的合并外销收入；乳品行混合基础乳品与深加工乳品，不能整体纳入。"
            pending = "需取得乳品内部巴氏杀菌乳与发酵/调制乳收入拆分；2020扩展上界跨50%，2021—2022上界低于50%。"
            cost_note = f"混合乳品成本{mixed_cost:.2f}仅作反向证据，不按成本构成推算收入；食品主营成本{disclosed_cost:.2f}"
            evidence_extra = "年报明确乳品包括低温巴氏杀菌乳、风味发酵乳、调制乳及蛋奶/热奶等特色乳饮品，且共线生产。"
        else:
            total, total_cost, eligible_revenue, eligible_cost = map(D, ANDELI[year])
            disclosed_revenue, disclosed_cost = eligible_revenue, eligible_cost
            strict_lo = strict_hi = D("0")
            expanded_lo = expanded_hi = eligible_revenue
            strict_business = "未单列果树种植或其他直接农业生产外销收入"
            expanded_business = "浓缩果汁、香精和果渣等果品初加工（与既有2023已核实口径一致）"
            strict_formula = "下界=上界=0（无单列直接种植收入）"
            expanded_formula = f"下界=上界=果汁/香精及果渣主营收入{eligible_revenue:.2f}"
            excluded_label = "公司营业收入与主营业务表之间未分类差额不纳入"
            reason = "按项目既定且已用于2023的口径，浓缩果汁、香精及果渣属于果品初加工，计入扩展口径；原料果采购不计严格口径。"
            pending = "无影响结论的金额拆分缺口；未分类收入差额不纳入扩展分子。"
            cost_note = f"初加工主营成本{eligible_cost:.2f}仅作收入表反向核对，不以成本推算收入"
            evidence_extra = "采用产品合计作为单一披露维度；不再叠加相同金额的分行业、地区或销售模式。"

        assert D("0") <= strict_lo <= strict_hi <= total
        assert D("0") <= expanded_lo <= expanded_hi <= total
        assert disclosed_revenue <= total and disclosed_cost <= total_cost
        sr_lo, sr_hi = strict_lo / total, strict_hi / total
        er_lo, er_hi = expanded_lo / total, expanded_hi / total
        source_has_total = compact(f"{total:.2f}") in compact(src["利润表原文摘录"] + src["主营业务表原文摘录"])
        # v31's 2020/2021 Juewei extract starts from the audit-opinion page;
        # the corrected locators 73/87 were checked against the linked PDFs.
        assert source_has_total or (code, year) in {("603517", 2020), ("603517", 2021)}

        rows.append({
            "股票代码": code,
            "公司全称": src["公司全称"],
            "年份": year,
            "行业分类代码": src["行业分类代码"] or ("待核实" if year == 2022 else ""),
            "行业分类名称": src["行业分类名称"] or ("待核实" if year == 2022 else ""),
            "严格口径涉农业务": strict_business,
            # Yiming has no separately disclosed external raw-milk/live-animal
            # numerator.  Zero is a classification bound, not an observed
            # formal numerator, so both formal-numerator cells stay blank.
            "严格口径正式涉农收入_元": "" if code == "605179" else (f"{strict_lo:.2f}" if strict_lo == strict_hi else ""),
            "严格口径收入下界_元": f"{strict_lo:.2f}",
            "严格口径收入上界_元": f"{strict_hi:.2f}",
            "严格口径上下界公式": strict_formula,
            "严格口径下界占比_原始未四舍五入": ratio(strict_lo, total),
            "严格口径上界占比_原始未四舍五入": ratio(strict_hi, total),
            "扩展口径涉农业务": expanded_business,
            "扩展口径正式涉农收入_元": "" if code == "605179" else (f"{expanded_lo:.2f}" if expanded_lo == expanded_hi else ""),
            "扩展口径收入下界_元": f"{expanded_lo:.2f}",
            "扩展口径收入上界_元": f"{expanded_hi:.2f}",
            "扩展口径上下界公式": expanded_formula,
            "扩展口径下界占比_原始未四舍五入": ratio(expanded_lo, total),
            "扩展口径上界占比_原始未四舍五入": ratio(expanded_hi, total),
            "公司营业收入_元": f"{total:.2f}",
            "公司营业成本_元_反向证据": f"{total_cost:.2f}",
            "公司营业收入公式": "合并利润表营业收入",
            "确认初加工收入_元": f"{eligible_revenue:.2f}" if eligible_revenue else "",
            "确认初加工成本_元_反向证据": f"{eligible_cost:.2f}" if eligible_cost else "",
            "混合乳品收入_元_扩展上界": f"{mixed_revenue:.2f}" if mixed_revenue else "",
            "混合乳品成本_元_反向证据": f"{mixed_cost:.2f}" if mixed_cost else "",
            "披露主营业务收入_元_核对": f"{disclosed_revenue:.2f}",
            "披露主营业务成本_元_核对": f"{disclosed_cost:.2f}",
            "未拆其他收入_元_上界": f"{unclassified_upper:.2f}" if unclassified_upper else "",
            "深加工或排除类别": excluded_label,
            "收入成本判别": cost_note,
            "严格样本结论": threshold(sr_lo, sr_hi),
            "扩展样本结论": threshold(er_lo, er_hi),
            "边界样本结论": boundary(er_lo, er_hi),
            "是否存在分部收入重叠": "分行业与分产品为重叠维度；采用一套不重叠口径，不相加",
            "纳入或剔除理由": reason,
            "待核实点": pending + ("2022行业分类字段仍待核实。" if year == 2022 else ""),
            "年报主营业务证据PDF页序号": src["年报主营业务候选PDF页序号"],
            "公司营业收入证据PDF页序号": profit_pages(code, year, src["利润表PDF页序号"]),
            "补充证据说明": evidence_extra,
            "年报链接": src["年报链接"],
            "2022行业字段处理": "沿用v31原值；待核实字段不插值、不复制相邻年份",
            "记录类型": "跨年快速复核第二十批Z组（未合并）",
            "复核状态": "已人工复核（第二十批Z组；主表未合并）",
            "复核日期": "2026-08-11",
        })

    out = pd.DataFrame(rows)
    assert len(out) == 20 and not out.duplicated(["股票代码", "年份"]).any()
    assert out["严格样本结论"].value_counts().to_dict() == {"否": 20}
    assert out["扩展样本结论"].value_counts().to_dict() == {"否": 16, "是": 3, "待核实": 1}
    assert out["边界样本结论"].value_counts().to_dict() == {"否": 17, "待核实": 3}
    assert out.loc[out["股票代码"].eq("605198"), "扩展样本结论"].eq("是").all()
    assert out.loc[out["股票代码"].eq("605179"), "严格样本结论"].eq("否").all()
    assert out.loc[out["股票代码"].eq("605179"), ["严格口径正式涉农收入_元", "扩展口径正式涉农收入_元"]].eq("").all().all()
    assert out.loc[out["年份"].eq(2022), "行业分类代码"].eq("待核实").all()
    assert out.loc[out["年份"].eq(2022), "行业分类名称"].eq("待核实").all()
    assert out["年报链接"].str.startswith("https://static.cninfo.com.cn/").all()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("batch20-Z rows=20; strict no=20; expanded yes=3/pending=1/no=16; boundary pending=3/no=17; not merged")


if __name__ == "__main__":
    main()
