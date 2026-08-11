#!/usr/bin/env python3
"""Build standalone historical fast-review batch 18-T from fixed v27.

Livestock/aquaculture farming and breeding are strict-scope activities. Feed
and animal-health products additionally enter the expanded scope. Slaughtered
fresh/frozen meat, processed food and trading are excluded. Where a product
line mixes farming and slaughter products, only auditable bounds are reported.
"""
from decimal import Decimal, getcontext
from pathlib import Path

import pandas as pd


getcontext().prec = 60
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v27_跨年快速复核第十六批第一组.csv"
OUTPUT = ROOT / "outputs" / "跨年快速复核第十八批_T组_3家公司.csv"

# Total revenue; mixed chicken revenue/cost; separately disclosed goose+pig
# revenue. Goose+pig cost is the product-dimension residual after chicken.
LIHUA = {
    2019: ("8870466583.29", "6394703948.68", "8438388501.43", "5906433933.17", "97733238.19", "334344843.67"),
    2020: ("8620966215.37", "7881614706.45", "7689428073.51", "7043682462.16", "72808778.42", "858729363.44"),
    2021: ("11131728138.55", "10253394650.23", "10009717471.55", "9076187529.65", "100396503.21", "1021614163.79"),
}

# Total revenue/cost; live poultry; ice-fresh slaughter products; product eggs;
# product "other" is the mutually exclusive product residual.
XIANGJIA = {
    2020: ("2189585769.77", "1580543007.01", "498186788.01", "520694630.08", "1587103065.23", "980455712.47", "0", "0"),
    2021: ("3005507323.26", "2477864131.87", "761025289.45", "772217202.25", "1825737636.94", "1369196027.25", "192228071.26", "178517444.45"),
    2022: ("3822999685.20", "3094788562.44", "1005505813.56", "969351804.14", "2392476010.73", "1745447654.37", "230615070.35", "208583322.57"),
}

# Total revenue; strict farming revenue/cost; special-feed revenue/cost;
# livestock-feed revenue/cost; animal-health revenue/cost. 2022 intersegment
# eliminations are handled separately below rather than allocated arbitrarily.
TIANMA = {
    2018: ("1506181112.69", "0", "0", "1047660316.40", "798843587.71", "0", "0", "1209195.88", "734608.28"),
    2019: ("2428383824.74", "10836857.83", "8529724.55", "1151564535.70", "916492005.33", "753503813.34", "698353221.80", "1957243.67", "976863.76"),
    2020: ("3639957005.03", "16904293.69", "19477420.11", "1352713317.99", "1106420405.02", "1920936211.96", "1753247885.02", "2052848.57", "1028244.14"),
    2021: ("5419021956.27", "83614349.20", "51276861.94", "1538094231.52", "1261457407.21", "3431033134.34", "3210314920.50", "1498714.38", "1008660.08"),
    2022: ("7007530405.29", "512738567.71", "367212201.15", "2134520094.91", "1806890761.32", "4285665307.35", "4073432217.86", "6750792.44", "3168573.85"),
}

# Separately disclosed water-product/processed-food lines. These are exclusion
# evidence only and must never enter either strict or expanded numerator.
TIANMA_EXCLUDED_WATER_FOOD = {
    2018: ("108364855.68", "104699281.32"),
    2019: ("311308765.88", "294960384.05"),
    2020: ("186039113.95", "194229408.85"),
    2021: ("259792639.58", "248618060.99"),
    2022: ("225351227.48", "215972457.77"),
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
        source["股票代码"].isin(["300761", "002982", "603668"])
        & source["复核状态"].str.startswith("年报及业务表已定位", na=False)
    ].sort_values(["股票代码", "年份"])
    assert len(source) == 958 and len(selected) == 11
    assert selected.groupby("股票代码").size().to_dict() == {"002982": 3, "300761": 3, "603668": 5}
    assert not selected.duplicated(["股票代码", "年份"]).any()

    rows = []
    for _, src in selected.iterrows():
        code, year = src["股票代码"], int(src["年份"])
        strict_cost_lo = strict_cost_hi = expanded_cost_lo = expanded_cost_hi = D("0")
        excluded_revenue = excluded_cost = mixed_revenue = mixed_cost = D("0")
        elimination_revenue = elimination_cost = D("0")

        if code == "300761":
            vals = list(map(D, LIHUA[year]))
            total, total_cost, mixed_revenue, mixed_cost, goose, pig = vals
            direct_known = goose + pig
            direct_known_cost = total_cost - mixed_cost
            strict_lo = expanded_lo = direct_known
            strict_hi = expanded_hi = total
            strict_cost_lo = expanded_cost_lo = direct_known_cost
            strict_cost_hi = expanded_cost_hi = total_cost
            strict_business = "单列猪收入+鹅收入；混合鸡收入含活鸡与屠宰冰鲜/冻品，仅作上界"
            expanded_business = "同严格口径；未单列对外饲料/动保收入，混合鸡收入仅作上界"
            formula = f"下界=鹅{goose:.2f}+猪{pig:.2f}={direct_known:.2f}；上界=下界+混合鸡收入{mixed_revenue:.2f}={total:.2f}"
            overlap = "猪、鹅、鸡为同一产品维度互斥项目；未叠加行业、地区或销售模式；内部饲料不另计"
            reason = "猪、鹅销售可确认为直接养殖；鸡收入同时含活鸡与屠宰后的鲜/冻产品，未披露金额拆分，不能把整项直接纳入。"
            pending = "鸡收入未拆活鸡与热鲜、冰鲜、冰冻品；上下界跨越50%，严格及扩展样本结论待核实。"
            cost_note = f"鹅+猪成本按同一产品维度残差={total_cost:.2f}-{mixed_cost:.2f}={direct_known_cost:.2f}；混合鸡成本{mixed_cost:.2f}仅作反向核对"
            excluded_label = "鸡收入中的屠宰热鲜、冰鲜及冰冻品（未单列金额）"
            extra = "年报明确主要业务含养殖及屠宰加工；鸡收入产品行无法可靠拆分，不按销量和均价估算"
        elif code == "002982":
            vals = list(map(D, XIANGJIA[year]))
            total, total_cost, live, live_cost, ice, ice_cost, egg, egg_cost = vals
            other = total - live - ice - egg
            other_cost = total_cost - live_cost - ice_cost - egg_cost
            strict_lo = expanded_lo = live + egg
            strict_hi = expanded_hi = strict_lo + other
            strict_cost_lo = expanded_cost_lo = live_cost + egg_cost
            strict_cost_hi = expanded_cost_hi = strict_cost_lo + other_cost
            excluded_revenue, excluded_cost = ice, ice_cost
            mixed_revenue, mixed_cost = other, other_cost
            strict_business = "活禽+商品蛋；产品“其他”性质混合，仅作上界"
            expanded_business = "同严格口径；冰鲜屠宰品排除，产品“其他”仅作上界"
            formula = f"下界=活禽{live:.2f}+商品蛋{egg:.2f}={strict_lo:.2f}；上界=下界+产品其他{other:.2f}={strict_hi:.2f}"
            overlap = "活禽、冰鲜、商品蛋、其他为同一产品维度互斥项目；不叠加行业、地区及销售模式"
            reason = "活禽和商品蛋属于直接畜禽养殖，冰鲜属于屠宰产品排除；产品“其他”未拆鸡苗、生物肥、柑橘等性质，只作上界。"
            pending = "产品“其他”未拆直接农业、农业投入品及非涉农项目；上下界不改变本年门槛结论。"
            cost_note = f"活禽+商品蛋成本={strict_cost_lo:.2f}；产品其他残差成本={other_cost:.2f}；冰鲜成本{ice_cost:.2f}排除"
            excluded_label = "冰鲜禽肉等屠宰产品"
            if year == 2021:
                extra = (
                    "采用2021原年报产品口径：冰鲜1825737636.94、其他226516325.61。"
                    "2022年报将2021比较数重分类为冰鲜1887324404.11、其他164929558.44；"
                    "两项合计不变，当前上下界仍处30%—50%，边界结论不变。商品蛋由自产蛋禽形成，纳入直接养殖。"
                )
            else:
                extra = "产品行合计与合并营业收入一致；商品蛋由自产蛋禽形成，纳入直接养殖"
        else:
            vals = list(map(D, TIANMA[year]))
            total, farm, farm_cost, special, special_cost, livestock_feed, livestock_feed_cost, vet, vet_cost = vals
            strict_lo = strict_hi = farm
            expanded_base = farm + special + livestock_feed + vet
            expanded_cost_base = farm_cost + special_cost + livestock_feed_cost + vet_cost
            if year == 2022:
                elimination_revenue, elimination_cost = D("282245559.03"), D("239982326.65")
                strict_lo = max(D("0"), farm - elimination_revenue)
                strict_hi = farm
                strict_cost_lo = max(D("0"), farm_cost - elimination_cost)
                strict_cost_hi = farm_cost
                expanded_lo = expanded_base - elimination_revenue
                expanded_hi = expanded_base
                expanded_cost_lo = expanded_cost_base - elimination_cost
                expanded_cost_hi = expanded_cost_base
            else:
                expanded_lo = expanded_hi = expanded_base
                strict_cost_lo = strict_cost_hi = farm_cost
                expanded_cost_lo = expanded_cost_hi = expanded_cost_base
            excluded_revenue, excluded_cost = map(D, TIANMA_EXCLUDED_WATER_FOOD[year])
            strict_business = "畜禽/鳗鲡养殖销售（直接养殖）" if year >= 2019 else "未单列直接养殖对外收入"
            expanded_business = "严格养殖+特水饲料+畜禽饲料+动保产品"
            if year == 2022:
                strict_formula = f"下界=养殖{farm:.2f}-全部内部抵消{elimination_revenue:.2f}={strict_lo:.2f}；上界=养殖{farm:.2f}"
                expanded_formula = f"下界=养殖+特水饲料+畜禽饲料+动保{expanded_base:.2f}-全部内部抵消{elimination_revenue:.2f}={expanded_lo:.2f}；上界={expanded_base:.2f}"
            else:
                strict_formula = f"下界=上界=单列养殖收入{farm:.2f}"
                expanded_formula = f"下界=上界=养殖{farm:.2f}+特水饲料{special:.2f}+畜禽饲料{livestock_feed:.2f}+动保{vet:.2f}={expanded_base:.2f}"
            overlap = "只在同一产品维度求和；原料贸易和水产品/食品销售排除；2022内部交易抵消不明分属，整体扣减构造保守下界"
            reason = "养殖进入严格口径；饲料和动保进入扩展口径；原料销售、水产品贸易及烤鳗/食品销售排除。"
            pending = "2022内部抵消无法在饲料、养殖、食品间精确分配，使用上下界；行业分类仍待核实。" if year == 2022 else "无影响门槛结论的待核实收入项。"
            cost_note = f"严格成本区间{strict_cost_lo:.2f}—{strict_cost_hi:.2f}；扩展成本区间{expanded_cost_lo:.2f}—{expanded_cost_hi:.2f}，只作收入项目反向核对"
            excluded_label = "水产品贸易/烤鳗食品（金额单列如下）；原料贸易亦排除但未计入下列金额"
            extra = "2018饲料销售未拆特水/畜禽但整体属于扩展农业投入品；2021养殖含畜禽与鳗鲡，均属严格口径"
            formula = ""

            # Lock the classification: excluded water/food evidence cannot
            # enter either numerator. Expanded scope is farming+feed+vet only.
            assert mixed_revenue == D("0") and mixed_cost == D("0")
            assert expanded_base == farm + special + livestock_feed + vet
            assert excluded_revenue not in (strict_lo, strict_hi, expanded_lo, expanded_hi)

        if code != "603668":
            strict_formula = expanded_formula = formula
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
            "严格口径成本下界_元_反向证据": f"{strict_cost_lo:.2f}",
            "严格口径成本上界_元_反向证据": f"{strict_cost_hi:.2f}",
            "扩展口径成本下界_元_反向证据": f"{expanded_cost_lo:.2f}",
            "扩展口径成本上界_元_反向证据": f"{expanded_cost_hi:.2f}",
            "混合或未拆收入_元_上界证据": f"{mixed_revenue:.2f}" if mixed_revenue else "",
            "混合或未拆成本_元_反向证据": f"{mixed_cost:.2f}" if mixed_cost else "",
            "明确排除类别": excluded_label,
            "明确排除收入_元_反向证据": f"{excluded_revenue:.2f}" if excluded_revenue else "",
            "明确排除成本_元_反向证据": f"{excluded_cost:.2f}" if excluded_cost else "",
            "内部交易抵消收入_元": f"{elimination_revenue:.2f}" if elimination_revenue else "",
            "内部交易抵消成本_元": f"{elimination_cost:.2f}" if elimination_cost else "",
            "收入成本判别": cost_note,
            "严格样本结论": threshold(sr_lo, sr_hi),
            "扩展样本结论": threshold(er_lo, er_hi),
            "边界样本结论": boundary(er_lo, er_hi),
            "是否存在分部收入重叠": overlap,
            "纳入或剔除理由": reason,
            "待核实点": pending,
            "年报主营业务证据PDF页序号": src["年报主营业务候选PDF页序号"],
            "公司营业收入证据PDF页序号": src["利润表PDF页序号"],
            "补充证据说明": extra,
            "年报链接": src["年报链接"],
            "2022行业字段处理": "沿用v27原值；待核实字段不插值、不复制相邻年份",
            "记录类型": "跨年快速复核第十八批T组（未合并）",
            "复核状态": "已人工复核（第十八批T组；主表未合并）",
            "复核日期": "2026-08-11",
        })

    out = pd.DataFrame(rows)
    assert len(out) == 11 and not out.duplicated(["股票代码", "年份"]).any()
    assert out["严格样本结论"].value_counts().to_dict() == {"否": 8, "待核实": 3}
    assert out["扩展样本结论"].value_counts().to_dict() == {"是": 5, "否": 3, "待核实": 3}
    assert out["边界样本结论"].value_counts().to_dict() == {"否": 6, "待核实": 3, "是": 2}
    tj = out[out["股票代码"] == "603668"].set_index("年份")
    assert tj.loc[2022, "扩展口径收入下界_元"] == "6657429203.38"
    assert tj.loc[2022, "扩展口径收入上界_元"] == "6939674762.41"
    assert tj["混合或未拆收入_元_上界证据"].eq("").all()
    assert tj["明确排除收入_元_反向证据"].to_dict() == {
        2018: "108364855.68",
        2019: "311308765.88",
        2020: "186039113.95",
        2021: "259792639.58",
        2022: "225351227.48",
    }
    xj = out[out["股票代码"] == "002982"].set_index("年份")
    assert xj.loc[2021, "严格口径收入下界_元"] == "953253360.71"
    assert xj.loc[2022, "严格口径收入上界_元"] == "1430523674.47"
    assert "重分类为冰鲜1887324404.11、其他164929558.44" in xj.loc[2021, "补充证据说明"]
    assert out.loc[out["年份"].eq(2022), "行业分类代码"].eq("待核实").all()
    assert out.loc[out["年份"].eq(2022), "行业分类名称"].eq("待核实").all()
    assert out["年报链接"].str.startswith("https://static.cninfo.com.cn/").all()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("batch18-T rows=11; strict no=8 pending=3; expanded yes=5 no=3 pending=3; boundary yes=2 pending=3 no=6; not merged")


if __name__ == "__main__":
    main()
