#!/usr/bin/env python3
"""Build standalone historical fast-review batch 16-O from fixed v26.

Direct livestock/crop production enters the strict numerator. Feed, veterinary
medicine/vaccines and agricultural production services additionally enter the
expanded numerator. Slaughter, meat/food deep processing, oil processing,
engineering, grain storage/trade and other trade are excluded. No main table is
modified by this script.
"""
from decimal import Decimal, getcontext
from pathlib import Path

import pandas as pd


getcontext().prec = 60
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v26_跨年快速复核第十五批第二组.csv"
OUTPUT = ROOT / "outputs" / "跨年快速复核第十六批_O组_3家公司.csv"


# total, direct-production revenue/cost, excluded slaughter/deep-processing
# revenue/cost, excluded trade revenue/cost.  Values are same-dimension product
# or industry rows and are never added across the two disclosure dimensions.
# For 2017--18, the excluded trade pair is the more complete industry-dimension
# grain/pig-trade evidence; the product-dimension grain amount remains only a
# partial cross-check and is not added to the industry amount.
CHUYING = {
    2013: ("1868073444.02", "1529977889.58", "1133079993.60", "174442648.74", "145038632.75", "133803316.45", "115745450.12", "畜牧养殖业+种植业"),
    2014: ("1761684746.80", "1139069320.79", "1064153312.47", "234683931.73", "216378450.43", "295848094.05", "257563402.83", "畜牧养殖业+种植业"),
    2015: ("3619021187.48", "1519978577.86", "1239105029.45", "1008937025.69", "912669476.23", "773086698.42", "744682746.49", "畜牧养殖业"),
    2016: ("6090172093.70", "2142256779.20", "1146242016.40", "1292908475.32", "1103210353.69", "1032336274.84", "969151548.85", "生猪产品"),
    2017: ("5698204438.99", "1630182448.96", "1372641240.06", "1053534469.50", "893108601.97", "2307368751.33", "2260190777.02", "生猪产品"),
    2018: ("3555829010.32", "1300501788.95", "2082207031.14", "634304317.67", "674927613.70", "1378434490.29", "1342871670.47", "生猪产品"),
}


# total, pig farming rev/cost, feed rev/cost, vaccine rev/cost, food-processing
# rev/cost, engineering/other revenue.  2020/2021 feed cost uses the aligned
# revenue/cost summary table; the detailed manufacturing-cost table is narrower
# in 2018--2021 and is retained only as a documented secondary view.
TIANBANG = {
    2018: ("4518950572.98", "2802294298.68", "2618203540.97", "1372416488.34", "1102271973.38", "106825960.37", "25718372.61", "227277629.82", "237182923.49", "10136195.77"),
    2019: ("6006883384.85", "4444133042.96", "3915593481.76", "1268982950.00", "1020737005.79", "57666777.47", "18342731.29", "219663228.86", "218954972.07", "16437385.56"),
    2020: ("10764148563.64", "8025648099.15", "3765880374.55", "1270059791.01", "1065184984.00", "72410333.57", "26778516.85", "1359034298.69", "1329710390.00", "36996041.22"),
    2021: ("10506630781.93", "6349741310.58", "8483328081.12", "1432680389.36", "1250196842.24", "43836137.40", "7031167.85", "2656595015.06", "2612825328.08", "23777929.53"),
    2022: ("9570942144.13", "6932682024.73", "5527860080.75", "428685387.30", "", "0", "", "2202235568.23", "2229758219.56", "7339163.87"),
}


# total, pig rev/cost, feed rev/cost, vet rev/cost, mixed milk/contract-farming
# or generic-other revenue, excluded slaughter/food rev/cost, excluded oil/corn
# business rev/cost.
TIANKANG = {
    2018: ("5273032350.33", "336076025.03", "304950179.99", "2562068393.17", "2186738157.98", "749858586.07", "307728572.38", "191598103.52", "518705961.44", "418107730.02", "854920766.67", "751093160.83"),
    2019: ("7476316392.02", "481147304.84", "339832886.02", "2930772440.50", "2510935643.16", "555192349.94", "221380398.09", "255283754.06", "1162972818.02", "606772912.14", "2055824820.70", "1735012803.81"),
    2020: ("11986808944.23", "2440937679.41", "1116087605.30", "4215294872.54", "3619768550.88", "846133069.25", "262479498.24", "325128931.13", "1035801253.77", "360721916.10", "3083604242.89", "2576027345.63"),
    # 2021 denominator and veterinary-medicine revenue use the latest restated
    # comparatives disclosed in the 2022 annual report, not the superseded
    # figures in the 2021 annual report.
    2021: ("15710847198.02", "1760854386.22", "2164566352.11", "5135319707.56", "4449762912.54", "946315072.78", "309767057.45", "601620936.12", "1733898332.83", "1667157984.56", "5471308552.65", "5034149377.57"),
    2022: ("16731607636.11", "1061268766.18", "958265932.02", "5531294851.69", "4988797550.30", "927400701.86", "333148653.00", "631447350.85", "3805151670.26", "3453796694.85", "4734883108.37", "4626228946.92"),
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
        source["股票代码"].isin(["002477", "002124", "002100"])
        & source["复核状态"].str.startswith("年报及业务表已定位", na=False)
    ].sort_values(["股票代码", "年份"])
    assert len(source) == 958 and len(selected) == 16
    assert selected.groupby("股票代码").size().to_dict() == {"002100": 5, "002124": 5, "002477": 6}
    assert not selected.duplicated(["股票代码", "年份"]).any()

    rows = []
    for _, src in selected.iterrows():
        code, year = src["股票代码"], int(src["年份"])
        strict_cost = expanded_known_cost = D("0")
        excluded_processing = excluded_processing_cost = D("0")
        excluded_trade = excluded_trade_cost = D("0")
        cost_gap = ""

        if code == "002477":
            total_s, direct_s, direct_cost_s, proc_s, proc_cost_s, trade_s, trade_cost_s, label = CHUYING[year]
            total, direct, strict_cost = D(total_s), D(direct_s), D(direct_cost_s)
            excluded_processing, excluded_processing_cost = D(proc_s), D(proc_cost_s)
            excluded_trade, excluded_trade_cost = D(trade_s), D(trade_cost_s)
            strict_lo = strict_hi = expanded_lo = expanded_hi = direct
            expanded_known_cost = strict_cost
            strict_business = label
            expanded_business = label + "；无另行确认的饲料/兽药/种子对外收入"
            strict_formula = expanded_formula = f"同一分行业/产品维度直接农业{direct:.2f}"
            overlap = "无；2013—15采用养殖/种植行业行，2016—18采用生猪产品行，未跨维度相加"
            reason = "粮食及生猪贸易、屠宰生鲜冻品、熟食深加工、互联网/类金融等均排除。"
            pending = "2013年PDF养殖行业数有双逗号排版瑕疵，按可辨识数字及同行合计核为1,528,769,443.17元。"
            if year != 2013:
                pending = "无；ST/退市状态仅保留标记，不改变本业务口径判断。"
            if year == 2017:
                overlap += "；贸易排除采用分行业粮食/生猪贸易2,307,368,751.33元，分产品粮食1,054,467,021.47元仅为部分证据，二者不相加"
            elif year == 2018:
                overlap += "；贸易排除采用分行业粮食贸易1,378,434,490.29元，分产品粮食678,406,787.18元仅为部分证据，二者不相加"
            # v26's 2013 locator excerpt starts on the following page; the
            # immediately preceding official PDF page was checked separately.
            evidence_keyword = "" if year == 2013 else ("畜牧养殖业" if year <= 2015 else "生猪产品")
        elif code == "002124":
            vals = TIANBANG[year]
            total, pig, strict_cost, feed = map(D, vals[:4])
            feed_cost = D(vals[4]) if vals[4] else None
            vaccine, vaccine_cost = D(vals[5]), (D(vals[6]) if vals[6] else None)
            excluded_processing, excluded_processing_cost, excluded_trade = D(vals[7]), D(vals[8]), D(vals[9])
            strict_lo = strict_hi = pig
            expanded_lo = expanded_hi = pig + feed + vaccine
            known_cost_parts = [strict_cost]
            if feed_cost is not None:
                known_cost_parts.append(feed_cost)
            if vaccine_cost is not None:
                known_cost_parts.append(vaccine_cost)
            expanded_known_cost = sum(known_cost_parts, D("0"))
            strict_business = "生猪养殖"
            expanded_business = "生猪养殖+饲料产品+动物疫苗"
            strict_formula = f"生猪养殖{pig:.2f}"
            expanded_formula = f"生猪养殖{pig:.2f}+饲料{feed:.2f}+动物疫苗{vaccine:.2f}={expanded_lo:.2f}"
            overlap = "无；分行业与分产品金额相同，仅采用一套产品行"
            reason = "养殖属直接农业；饲料和动物疫苗属农业投入品；食品加工、工程环保及其他排除。"
            pending = "无。"
            if year == 2022:
                cost_gap = "2022饲料收入单列但成本表未单列饲料成本；扩展已核实成本仅含养殖成本，不将缺失成本记零。"
                pending = "2022饲料成本待补；不影响收入阈值判断。"
            elif year in {2018, 2019, 2020, 2021}:
                cost_gap = "扩展成本采用与收入对应的主营业务摘要表；制造成本构成小计口径较窄，未替换摘要值。"
            evidence_keyword = "饲料" if year == 2022 else "生猪养殖"
        else:
            vals = TIANKANG[year]
            total, pig, strict_cost, feed, feed_cost, vet, vet_cost, mixed, proc, proc_cost, other_excluded, other_excluded_cost = map(D, vals)
            strict_lo, strict_hi = pig, pig + mixed
            base_expanded = pig + feed + vet
            if year <= 2020:
                # Both components of the explicitly named line are eligible in
                # expanded scope: milk is direct farming and contract raising is
                # an agricultural production service.
                expanded_lo = expanded_hi = base_expanded + mixed
            else:
                expanded_lo, expanded_hi = base_expanded, base_expanded + mixed
            expanded_known_cost = strict_cost + feed_cost + vet_cost
            excluded_processing, excluded_processing_cost = proc, proc_cost
            excluded_trade, excluded_trade_cost = other_excluded, other_excluded_cost
            strict_business = "生猪养殖；牛奶/代养或其他混合项仅作严格上界"
            expanded_business = "生猪养殖+饲料+兽药" + ("+牛奶/代养业务" if year <= 2020 else "；其他混合收入仅作上界")
            strict_formula = f"下界=生猪养殖{pig:.2f}；上界=下界+混合项{mixed:.2f}={strict_hi:.2f}"
            if year <= 2020:
                expanded_formula = f"生猪{pig:.2f}+饲料{feed:.2f}+兽药{vet:.2f}+牛奶/代养{mixed:.2f}={expanded_lo:.2f}"
            else:
                expanded_formula = f"下界=生猪{pig:.2f}+饲料{feed:.2f}+兽药{vet:.2f}={expanded_lo:.2f}；上界再加其他{mixed:.2f}={expanded_hi:.2f}"
            overlap = "无；采用同一分产品维度，食品养殖行业合计未再次加入"
            reason = "饲料、兽药及明确代养服务进入扩展口径；屠宰肉制品、蛋白油脂、玉米收储/加工和担保排除。"
            pending = "混合牛奶/代养未拆，严格正式分子采用生猪养殖下界。"
            if year <= 2020:
                cost_gap = "牛奶/代养业务收入可识别但对应成本未单列；扩展已核实可归属成本仅含生猪、饲料和兽药成本，不称全部对应成本已核。"
            if year >= 2021:
                pending = "其他收入未拆农业与非农业，仅作上界；正式分子采用可确认下界。"
            if year == 2021:
                pending += " 统一采用2022年报最新重列的2021比较口径：营业收入15,710,847,198.02元、兽药收入946,315,072.78元；不再使用2021年报原披露数。"
            evidence_keyword = "饲料" if year == 2022 else "生猪养殖"

        denominator_evidence = src["利润表原文摘录"]
        if code == "002100" and year == 2021:
            denominator_evidence = selected.loc[
                (selected["股票代码"].eq("002100")) & selected["年份"].eq(2022),
                "利润表原文摘录",
            ].iloc[0]
        assert compact(format(total, "f")) in compact(denominator_evidence), (code, year, "denominator")
        assert evidence_keyword in src["主营业务表原文摘录"], (code, year, "business evidence")
        assert D("0") <= strict_lo <= strict_hi <= total
        assert D("0") <= expanded_lo <= expanded_hi <= total
        sr_lo, sr_hi = strict_lo / total, strict_hi / total
        er_lo, er_hi = expanded_lo / total, expanded_hi / total
        strict_result, expanded_result, boundary_result = threshold(sr_lo, sr_hi), threshold(er_lo, er_hi), boundary(er_lo, er_hi)

        report_url = src["年报链接"]
        business_page = src["年报主营业务表PDF页序号"]
        profit_page = src["利润表PDF页序号"]
        if code == "002100" and year == 2021:
            latest = selected.loc[
                (selected["股票代码"].eq("002100")) & selected["年份"].eq(2022)
            ].iloc[0]
            report_url = latest["年报链接"]
            business_page = "16—17"
            profit_page = latest["利润表PDF页序号"]

        rows.append({
            "股票代码": code, "公司全称": src["公司全称"], "年份": year,
            "行业分类代码": src["行业分类代码"] or "待核实", "行业分类名称": src["行业分类名称"] or "待核实",
            "严格口径涉农业务": strict_business,
            "严格口径正式涉农收入_元": f"{strict_lo:.2f}" if strict_lo == strict_hi else "",
            "严格口径收入下界_元": f"{strict_lo:.2f}", "严格口径收入上界_元": f"{strict_hi:.2f}",
            "严格口径上下界公式": strict_formula,
            "严格口径下界占比_原始未四舍五入": ratio(strict_lo, total),
            "严格口径上界占比_原始未四舍五入": ratio(strict_hi, total),
            "扩展口径涉农业务": expanded_business,
            "扩展口径正式涉农收入_元": f"{expanded_lo:.2f}" if expanded_lo == expanded_hi else "",
            "扩展口径收入下界_元": f"{expanded_lo:.2f}", "扩展口径收入上界_元": f"{expanded_hi:.2f}",
            "扩展口径上下界公式": expanded_formula,
            "扩展口径下界占比_原始未四舍五入": ratio(expanded_lo, total),
            "扩展口径上界占比_原始未四舍五入": ratio(expanded_hi, total),
            "公司营业收入_元": f"{total:.2f}", "公司营业收入公式": "合并利润表营业收入",
            "严格口径已核实可归属成本_元": f"{strict_cost:.2f}",
            "扩展口径已核实可归属成本_元": f"{expanded_known_cost:.2f}",
            "成本口径缺口说明": cost_gap or "收入对应成本已核；成本不参与收入阈值判定。",
            "屠宰肉品或食品加工收入_元_排除证据": f"{excluded_processing:.2f}",
            "屠宰肉品或食品加工成本_元_排除证据": f"{excluded_processing_cost:.2f}" if excluded_processing_cost else "",
            "贸易油脂玉米工程等收入_元_排除证据": f"{excluded_trade:.2f}",
            "贸易油脂玉米工程等成本_元_排除证据": f"{excluded_trade_cost:.2f}" if excluded_trade_cost else "",
            "严格样本结论": strict_result, "扩展样本结论": expanded_result, "边界样本结论": boundary_result,
            "是否存在分部收入重叠": overlap,
            "纳入或剔除理由": f"严格区间[{ratio(strict_lo,total)}, {ratio(strict_hi,total)}]；扩展区间[{ratio(expanded_lo,total)}, {ratio(expanded_hi,total)}]。{reason}",
            "待核实点": pending,
            "当年曾ST_已核实": src["当年曾ST_已核实"], "年末ST_已核实": src["年末ST_已核实"],
            "当年退市整理期_已核实": src["当年退市整理期_已核实"],
            "ST退市处理说明": "仅保留状态标记；未用ST或退市状态改变业务分类与收入判定。",
            "年报主营业务证据PDF页序号": business_page,
            "公司营业收入证据PDF页序号": profit_page, "年报链接": report_url,
            "2022行业字段处理": "沿用v26原值；待核实字段不插值、不复制相邻年份",
            "记录类型": "跨年快速复核第十六批O组（未合并）",
            "复核状态": "已人工复核（第十六批O组；主表未合并）", "复核日期": "2026-08-11",
        })

    out = pd.DataFrame(rows)
    assert len(out) == 16 and not out.duplicated(["股票代码", "年份"]).any()
    assert out["严格样本结论"].value_counts().to_dict() == {"否": 9, "是": 7}
    assert out["扩展样本结论"].value_counts().to_dict() == {"是": 10, "否": 5, "待核实": 1}
    assert out["边界样本结论"].value_counts().to_dict() == {"否": 11, "是": 4, "待核实": 1}
    assert out.loc[out["年份"].eq(2022), "行业分类代码"].eq("待核实").all()
    assert out.loc[out["年份"].eq(2022), "行业分类名称"].eq("待核实").all()
    assert out["年报链接"].str.startswith("https://static.cninfo.com.cn/").all()
    assert out.loc[out["股票代码"].eq("002124"), "严格样本结论"].eq("是").all()
    assert out.loc[(out["股票代码"].eq("002100")) & out["年份"].le(2020), "扩展样本结论"].eq("是").all()
    assert out.loc[(out["股票代码"].eq("002100")) & out["年份"].eq(2021), "扩展样本结论"].iloc[0] == "待核实"
    assert out.loc[(out["股票代码"].eq("002100")) & out["年份"].eq(2021), "边界样本结论"].iloc[0] == "待核实"
    tk_2021 = out.loc[(out["股票代码"].eq("002100")) & out["年份"].eq(2021)].iloc[0]
    assert tk_2021["公司营业收入_元"] == "15710847198.02"
    assert tk_2021["扩展口径收入下界_元"] == "7842489166.56"
    assert D(tk_2021["扩展口径下界占比_原始未四舍五入"]) < D("0.50")
    assert D(tk_2021["扩展口径上界占比_原始未四舍五入"]) >= D("0.50")
    assert "统一采用2022年报最新重列" in tk_2021["待核实点"]
    assert out.loc[
        (out["股票代码"].eq("002100")) & out["年份"].between(2018, 2020),
        "成本口径缺口说明",
    ].str.contains("牛奶/代养业务收入可识别但对应成本未单列", regex=False).all()
    assert out.loc[
        (out["股票代码"].eq("002477")) & out["年份"].isin([2017, 2018]),
        "是否存在分部收入重叠",
    ].str.contains("仅为部分证据，二者不相加", regex=False).all()
    assert out.loc[(out["股票代码"].eq("002100")) & out["年份"].eq(2022), "扩展样本结论"].iloc[0] == "否"
    assert out.loc[(out["股票代码"].eq("002477")) & out["年份"].isin([2013, 2014]), "严格样本结论"].eq("是").all()
    assert out.loc[(out["股票代码"].eq("002477")) & out["年份"].ge(2015), "严格样本结论"].eq("否").all()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("batch16-O rows=16; strict yes=7/no=9; expanded yes=10/no=5/pending=1; boundary yes=4/no=11/pending=1; not merged")


if __name__ == "__main__":
    main()
