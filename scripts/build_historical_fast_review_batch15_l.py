#!/usr/bin/env python3
"""Build batch 15-L for mixed grain/oil, breeding, and juice companies.

The fixed v24 worktable is read-only.  Product and industry dimensions are
never added mechanically.  Mixed grain/oil food is an expanded upper bound;
liquor, slaughter, concentrated juice, trade and real estate are excluded.
"""
from decimal import Decimal, getcontext
from pathlib import Path

import pandas as pd


getcontext().prec = 60
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v24_跨年快速复核第十四批第一组.csv"
OUTPUT = ROOT / "outputs" / "跨年快速复核第十五批_L组_3家公司.csv"

# year: mixed grain/oil-food product revenue and cost, consolidated revenue.
JINJIAN = {
    2014: ("1392025827.24", "1262543497.66", "1680904066.87"),
    2015: ("1302341235.91", "1164091308.12", "2285243577.06"),
    2018: ("1732595858.01", "1554188411.16", "3011223472.35"),
    2019: ("2094441662.37", "1893871011.91", "4108074490.27"),
    2020: ("2620056573.20", "2418914319.21", "5715996407.78"),
    2021: ("3357591083.33", "3180341026.41", "6706482232.32"),
    2022: ("3178213951.61", "3035907220.34", "6412071601.89"),
}
JINJIAN_TRADE = {
    2014: "", 2015: "755218794.35", 2018: "650967772.70",
    2019: "1390917073.60", 2020: "2197583835.28",
    2021: "2006673469.38", 2022: "2948458693.50",
}

# year: breeding revenue, cost (blank when not separately disclosed), total,
# and the PDF pages carrying the exact revenue note/business table.
SHUNXIN = {
    2014: ("276080444.48", "308706514.76", "9480664077.56", "15|131"),
    2015: ("185143506.09", "183851181.06", "9637423354.44", "13|14|131|132"),
    2018: ("102600808.27", "205060643.68", "12074373183.62", "13|132|133"),
    2019: ("189604258.58", "184355898.56", "14900141028.95", "13|154|155"),
    2020: ("427233499.05", "275947780.90", "15511399521.15", "15|16|153|154"),
    2021: ("288810820.79", "247948492.02", "14869379036.69", "14|15|155|156"),
    2022: ("166717765.21", "", "11678338514.50", "15|16|143"),
}
SHUNXIN_EXCLUDED = {
    # year: liquor, slaughter/pork, real estate revenue
    2014: ("4120135214.82", "2610566204.88", "1128579812.30"),
    2015: ("4647901363.69", "2724888567.42", "501241694.94"),
    2018: ("9277559208.42", "2368477510.36", "145256417.06"),
    2019: ("10289345436.30", "3369808280.50", "872949048.98"),
    2020: ("10184967553.62", "4209401402.24", "526884768.73"),
    2021: ("10225475406.19", "3313169997.23", "863942695.23"),
    2022: ("8108857899.91", "2556539071.93", "676073464.16"),
}
SHUNXIN_AG_EXTRAS = {
    # year: vegetable revenue/cost, seed-input revenue/cost
    2014: ("4807723.87", "4095189.42", "19073208.43", "9073299.18"),
    2015: ("3279383.50", "2841898.63", "0", "0"),
}

# year: concentrated-juice revenue/cost, feed revenue/cost, directly sold pig
# revenue/cost, consolidated revenue.  Feed and pig amounts are textually
# disjoint in 2021-22 even though industry/product dimensions otherwise cross.
GUOTOU = {
    2014: ("870539342.21", "731459402.10", "0", "0", "0", "0", "877605229.66"),
    2015: ("1084649808.31", "862029547.16", "0", "0", "0", "0", "1097908222.76"),
    2018: ("943631477.64", "695495533.10", "14178441.29", "12065977.15", "0", "0", "963190630.07"),
    2019: ("1311095137.03", "1049619226.07", "14983665.94", "10950575.58", "0", "0", "1330101539.51"),
    2020: ("1122928781.36", "930919511.79", "8911255.39", "7818121.20", "0", "0", "1147532187.31"),
    2021: ("1438177992.41", "1212063239.99", "2894487.84", "2568090.92", "611555.45", "1171537.05", "1449861160.70"),
    2022: ("1709831490.44", "1331247553.96", "8597903.10", "7665331.01", "146637.80", "469840.66", "1726531019.75"),
}


def D(value: str) -> Decimal:
    return Decimal(value)


def ratio(n: Decimal, d: Decimal) -> str:
    return format(n / d, "f")


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
    src = pd.read_csv(SOURCE, dtype={"股票代码": str}, keep_default_na=False)
    target = src[
        src["股票代码"].isin(["600127", "000860", "600962"])
        & src["复核状态"].str.startswith("年报及业务表已定位", na=False)
    ].sort_values(["股票代码", "年份"])
    assert len(src) == 958
    assert len(target) == 21
    assert target.groupby("股票代码").size().to_dict() == {"000860": 7, "600127": 7, "600962": 7}
    assert not target.duplicated(["股票代码", "年份"]).any()

    rows = []
    for _, s in target.iterrows():
        code, year = s["股票代码"], int(s["年份"])
        if code == "600127":
            mixed_s, mixed_cost_s, total_s = JINJIAN[year]
            mixed, mixed_cost, total = D(mixed_s), D(mixed_cost_s), D(total_s)
            strict_lo = strict_hi = D("0")
            expanded_lo, expanded_hi = D("0"), mixed
            direct, initial, feed, pig = D("0"), D("0"), D("0"), D("0")
            trade_s = JINJIAN_TRADE[year]
            trade = D(trade_s) if trade_s else None
            liquor, slaughter, real_estate = D("0"), D("0"), D("0")
            direct_cost, input_cost = D("0"), D("0")
            residual = D("0")
            strict_business = "未披露合并外销种植或养殖产品收入"
            expanded_business = "粮油食品混合大类（含大米/食用油等初加工候选，也含面制品等深加工）"
            strict_formula = "下界=上界=0（未披露外销直接农业产品）"
            expanded_formula = f"下界=0；上界=粮油食品混合产品{mixed:.2f}"
            reverse_revenue, reverse_cost = mixed, mixed_cost
            reverse_label = "粮油食品混合大类（仅作扩展上界，不作正式分子）"
            overlap = "行业与产品是同一收入的不同维度；仅采用产品维度粮油食品作上界，不跨维度相加"
            reason = "农产品贸易、进出口贸易不纳入；乳品和休闲食品按深加工排除。粮油食品未拆大米/油脂与面制品，不能按成本比例估算。"
            pending = "取得大米、食用油、面制品各自营业收入后，方可形成扩展正式分子。"
            pages = s["年报主营业务候选PDF页序号"]
            cost_note = f"粮油食品营业成本{mixed_cost:.2f}，仅核对对应收入，未按成本结构倒推收入"
        elif code == "000860":
            breeding_s, breeding_cost_s, total_s, pages = SHUNXIN[year]
            breeding, total = D(breeding_s), D(total_s)
            vegetable = vegetable_cost = seed = seed_cost = D("0")
            if year in SHUNXIN_AG_EXTRAS:
                vegetable_s, vegetable_cost_s, seed_s, seed_cost_s = SHUNXIN_AG_EXTRAS[year]
                vegetable, vegetable_cost = D(vegetable_s), D(vegetable_cost_s)
                seed, seed_cost = D(seed_s), D(seed_cost_s)
            strict_lo = strict_hi = breeding + vegetable
            expanded_lo = expanded_hi = strict_lo + seed
            direct, initial, feed, pig = strict_lo, D("0"), seed, D("0")
            direct_cost, input_cost = D(breeding_cost_s) + vegetable_cost if breeding_cost_s else vegetable_cost, seed_cost
            liquor_s, slaughter_s, real_estate_s = SHUNXIN_EXCLUDED[year]
            trade, liquor, slaughter, real_estate = D("0"), D(liquor_s), D(slaughter_s), D(real_estate_s)
            residual = D("0")
            strict_business = "种畜养殖业/种畜及单列蔬菜种植（直接农业生产）"
            expanded_business = "严格口径直接农业；2014年另加单列种子农业投入品；未把屠宰、白酒、食品加工、地产等加入"
            strict_formula = f"下界=上界=种畜{breeding:.2f}+蔬菜种植{vegetable:.2f}={strict_lo:.2f}"
            expanded_formula = f"下界=上界=严格口径{strict_lo:.2f}+种子{seed:.2f}={expanded_lo:.2f}"
            reverse_revenue = D("0")
            reverse_cost = D("0")
            reverse_label = "白酒、屠宰/猪肉、食品加工、房地产、建筑/纸业等排除"
            overlap = "行业与产品表的种畜为同一收入，仅取一次；不与屠宰猪肉收入相加"
            reason = "种猪繁育、生猪养殖及蔬菜种植属于直接农业；种子属于农业投入品。屠宰猪肉按本批口径作为下游深加工排除，白酒、地产等亦排除。"
            pending = "2022年种畜营业成本未在收入相关信息表中单列；不影响以收入计算的样本结论。" if not breeding_cost_s else "无影响结论的收入待拆项。"
            cost_note = (
                f"直接农业成本=种畜{D(breeding_cost_s):.2f}+蔬菜{vegetable_cost:.2f}={direct_cost:.2f}；种子成本{seed_cost:.2f}"
                if breeding_cost_s else "2022年收入表仅列种畜收入，未单列对应成本"
            )
        else:
            juice_s, juice_cost_s, feed_s, feed_cost_s, pig_s, pig_cost_s, total_s = GUOTOU[year]
            juice, juice_cost, feed = D(juice_s), D(juice_cost_s), D(feed_s)
            feed_cost, pig, pig_cost, total = D(feed_cost_s), D(pig_s), D(pig_cost_s), D(total_s)
            disclosed_products = juice + feed
            product_residual = total - disclosed_products
            # In 2021-22 the product-table residual already contains the
            # industry-line fattening-pig sale.  Only the remainder after pig
            # is an unknown increment; never add pig to the full residual.
            residual = product_residual - pig
            assert residual >= 0
            strict_lo, strict_hi = pig, product_residual
            expanded_lo, expanded_hi = pig + feed, product_residual + feed
            direct, initial = pig, D("0")
            trade, liquor, slaughter, real_estate = D("0"), D("0"), D("0"), D("0")
            direct_cost, input_cost = pig_cost, feed_cost
            strict_business = "2021—2022年行业说明明确的产畜肥猪收入" if pig else "未单列直接农业收入；以未拆其他营业收入作保守上界"
            expanded_business = "饲料（农业投入品）及明确的产畜肥猪；未拆其他营业收入作上界"
            strict_formula = f"下界=产畜肥猪{pig:.2f}；上界=产品残差（已含肥猪）{product_residual:.2f}"
            expanded_formula = f"下界=产畜肥猪{pig:.2f}+饲料{feed:.2f}；上界=产品残差（已含肥猪）{product_residual:.2f}+饲料{feed:.2f}={expanded_hi:.2f}"
            reverse_revenue, reverse_cost = juice, juice_cost
            reverse_label = "浓缩果汁、香料及果糖（饮料制造深加工）"
            overlap = (
                "行业说明的产畜肥猪与产品说明的欧洲饲料文字上相互独立；果汁/饲料产品维度不与饮料/饲料行业维度机械相加"
                if pig else "采用产品维度果汁/饲料；不再叠加行业维度饮料制造业/饲料制造业"
            )
            reason = "浓缩苹果汁等按本研究筛选规则属于饮料制造深加工，不按果品初加工纳入；饲料为农业投入品，明确外销产畜肥猪为直接农业。"
            pending = "未拆其他营业收入仅作保守上界，正式分子留空；其上界不影响样本结论。"
            pages = s["年报主营业务候选PDF页序号"]
            cost_note = f"果汁成本{juice_cost:.2f}；饲料成本{feed_cost:.2f}；产畜肥猪成本{pig_cost:.2f}；成本均未误作收入"

        assert D("0") <= strict_lo <= strict_hi <= total
        assert strict_lo <= expanded_lo <= expanded_hi <= total
        sr_lo, sr_hi = strict_lo / total, strict_hi / total
        er_lo, er_hi = expanded_lo / total, expanded_hi / total
        strict_result = threshold(sr_lo, sr_hi)
        expanded_result = threshold(er_lo, er_hi)
        boundary_result = boundary(er_lo, er_hi)
        pnl = compact(s["利润表原文摘录"])
        assert compact(total_s) in pnl or "营业收入" in pnl

        strict_exact = strict_lo == strict_hi
        expanded_exact = expanded_lo == expanded_hi
        rows.append({
            "股票代码": code,
            "公司全称": s["公司全称"],
            "年份": year,
            "行业分类代码": s["行业分类代码"] or "待核实",
            "行业分类名称": s["行业分类名称"] or "待核实",
            "严格口径涉农业务": strict_business,
            "严格口径正式涉农收入_元": f"{strict_lo:.2f}" if strict_exact else "",
            "严格口径收入下界_元": f"{strict_lo:.2f}",
            "严格口径收入上界_元": f"{strict_hi:.2f}",
            "严格口径上下界公式": strict_formula,
            "严格口径下界占比_原始未四舍五入": ratio(strict_lo, total),
            "严格口径上界占比_原始未四舍五入": ratio(strict_hi, total),
            "扩展口径涉农业务": expanded_business,
            "扩展口径正式涉农收入_元": f"{expanded_lo:.2f}" if expanded_exact else "",
            "扩展口径收入下界_元": f"{expanded_lo:.2f}",
            "扩展口径收入上界_元": f"{expanded_hi:.2f}",
            "扩展口径上下界公式": expanded_formula,
            "扩展口径下界占比_原始未四舍五入": ratio(expanded_lo, total),
            "扩展口径上界占比_原始未四舍五入": ratio(expanded_hi, total),
            "公司营业收入_元": f"{total:.2f}",
            "公司营业收入公式": "合并利润表营业收入",
            "直接农业收入_元": f"{direct:.2f}",
            "确认初加工收入_元": f"{initial:.2f}",
            "农业投入品收入_元": f"{feed:.2f}",
            "产畜肥猪收入_元": f"{pig:.2f}" if code == "600962" else "0.00",
            "直接农业成本_元_反向证据": f"{direct_cost:.2f}",
            "农业投入品成本_元_反向证据": f"{input_cost:.2f}",
            "贸易收入_元_排除证据": f"{trade:.2f}" if trade is not None else "",
            "白酒收入_元_排除证据": f"{liquor:.2f}",
            "屠宰或猪肉收入_元_排除证据": f"{slaughter:.2f}",
            "房地产收入_元_排除证据": f"{real_estate:.2f}",
            "未拆其他营业收入上界增量_元": f"{residual:.2f}",
            "深加工或混合类别": reverse_label,
            "深加工或混合类别收入_元_反向证据": f"{reverse_revenue:.2f}",
            "深加工或混合类别成本_元_反向证据": f"{reverse_cost:.2f}",
            "收入成本判别": cost_note,
            "严格样本结论": strict_result,
            "扩展样本结论": expanded_result,
            "边界样本结论": boundary_result,
            "是否存在分部收入重叠": overlap,
            "纳入或剔除理由": reason,
            "待核实点": pending,
            "研究口径与税法差异说明": (
                "浓缩果汁曾被相关税法口径列入农产品初加工范围，不改变本研究按业务实质将其作为饮料制造深加工排除的筛选规则。"
                if code == "600962" else ""
            ),
            "年报主营业务证据PDF页序号": pages,
            "公司营业收入证据PDF页序号": s["利润表PDF页序号"],
            "年报链接": s["年报链接"],
            "2022行业字段处理": "沿用v24原值；待核实字段不插值、不复制相邻年份",
            "记录类型": "跨年快速复核第十五批L组（未合并）",
            "复核状态": "已人工复核（第十五批L组；主表未合并）",
            "复核日期": "2026-08-11",
        })

    out = pd.DataFrame(rows)
    assert len(out) == 21 and not out.duplicated(["股票代码", "年份"]).any()
    assert out["严格样本结论"].value_counts().to_dict() == {"否": 21}
    assert out["扩展样本结论"].value_counts().to_dict() == {"否": 16, "待核实": 5}
    assert out["边界样本结论"].value_counts().to_dict() == {"否": 14, "待核实": 7}
    assert out.loc[out["股票代码"].eq("600127"), "扩展口径正式涉农收入_元"].eq("").all()
    assert out.loc[out["股票代码"].eq("000860"), "严格口径正式涉农收入_元"].ne("").all()
    sx14 = out.loc[(out["股票代码"].eq("000860")) & (out["年份"].eq(2014))].iloc[0]
    sx15 = out.loc[(out["股票代码"].eq("000860")) & (out["年份"].eq(2015))].iloc[0]
    assert sx14["严格口径收入下界_元"] == "280888168.35" and sx14["扩展口径收入下界_元"] == "299961376.78"
    assert sx15["严格口径收入下界_元"] == "188422889.59" and sx15["扩展口径收入下界_元"] == "188422889.59"
    gl21 = out.loc[(out["股票代码"].eq("600962")) & (out["年份"].eq(2021))].iloc[0]
    gl22 = out.loc[(out["股票代码"].eq("600962")) & (out["年份"].eq(2022))].iloc[0]
    assert (gl21["严格口径收入下界_元"], gl21["严格口径收入上界_元"], gl21["扩展口径收入下界_元"], gl21["扩展口径收入上界_元"]) == ("611555.45", "8788680.45", "3506043.29", "11683168.29")
    assert (gl22["严格口径收入下界_元"], gl22["严格口径收入上界_元"], gl22["扩展口径收入下界_元"], gl22["扩展口径收入上界_元"]) == ("146637.80", "8101626.21", "8744540.90", "16699529.31")
    assert out.loc[(out["股票代码"].eq("600127")) & (out["年份"].eq(2014)), "贸易收入_元_排除证据"].iloc[0] == ""
    assert out.loc[out["股票代码"].eq("600962"), "研究口径与税法差异说明"].str.contains("不改变本研究").all()
    assert out.loc[out["年份"].eq(2022), "行业分类代码"].eq("待核实").all()
    assert out.loc[out["年份"].eq(2022), "行业分类名称"].eq("待核实").all()
    assert out["年报链接"].str.startswith("https://static.cninfo.com.cn/").all()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("batch15-L rows=21; strict no=21; expanded no=16/pending=5; boundary no=14/pending=7; not merged")


if __name__ == "__main__":
    main()
