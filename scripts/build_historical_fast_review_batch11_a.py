#!/usr/bin/env python3
"""Build historical fast-review batch 11 A from the fixed v20 worktable.

Targets every still-pending company-year in v20 for 新赛股份 (600540),
新农开发 (600359) and 西部牧业 (300106).  The script writes an independent
evidence CSV only; it never modifies or merges the master worktable.
"""
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v20_跨年快速复核第十批.csv"
OUTPUT = ROOT / "outputs" / "跨年快速复核第十一批_A组_3家公司.csv"


# 新赛股份：年报未单列直接种植收入，严格分子为可核实的0。扩展分子
# 统一取同一分行业表的“农业”收入，避免分产品皮棉/棉籽混入商贸口径。
XINSAI = {
    2013: ("1020959773.02", "1361014028.79", "农业1,020,959,773.02", "15", ""),
    2014: ("560439246.17", "1103264980.96", "农业560,439,246.17", "15", ""),
    # The source table is disclosed in RMB 10,000; retain that source precision.
    2015: ("465017200.00", "1192420710.73", "农业46,501.72万元×10,000", "14|15", "主营构成表单位为万元，换算为元；来源精度为万元。"),
    2016: ("488300968.46", "1050263247.15", "农业488,300,968.46", "13|14", ""),
    2017: ("595054245.33", "1102602781.42", "农业595,054,245.33", "14|15", ""),
    2018: ("682875124.19", "1283510819.63", "农业682,875,124.19", "16", ""),
    2019: ("1154754982.13", "1380228765.64", "农业1,154,754,982.13", "14", ""),
    2020: ("727596218.98", "1119100056.59", "农业727,596,218.98", "16|18", ""),
    2021: ("895151901.98", "1096901880.13", "农业895,151,901.98", "20|21", "2021总营收取当年合并利润表，不取会计政策调整表中的2020比较数。"),
}


# 新农开发：严格口径加总同一分产品表中的种子、苗木、鲜奶/牛奶和牛。
# 扩展口径使用互斥的农业、畜牧业分行业收入，再加园林绿化行业中单列
# 的苗木产品；年报分行业表证明苗木不在农业/畜牧业收入内。
XINNONG = {
    2013: ("98386590.15", "318201882.33", "868094781.81", "94,912,703.03+1,220,932.12+2,252,955.00", "农业314,727,995.21+畜牧业2,252,955.00+苗木1,220,932.12", "12|13"),
    2014: ("111899109.11", "253023620.44", "667729706.18", "99,982,725.99+10,162,073.12+1,754,310.00", "农业241,107,237.32+畜牧业1,754,310.00+苗木10,162,073.12", "12|13"),
    2015: ("80245040.64", "258468003.63", "631268592.04", "77,493,411.97+2,111,988.67+639,640.00", "农业255,716,374.96+畜牧业639,640.00+苗木2,111,988.67", "11|12"),
    2016: ("96869145.84", "238397115.96", "1562192861.03", "89,170,707.72+5,005,315.01+1,250,633.11+1,442,490.00", "农业235,703,992.85+畜牧业1,442,490.00+苗木1,250,633.11", "10|11"),
    2017: ("50966168.91", "257538087.95", "1084701436.83", "45,356,085.76+3,733,354.93+968,978.22+907,750.00", "农业255,661,359.73+畜牧业907,750.00+苗木968,978.22", "11|12"),
    2018: ("96103875.55", "291358155.00", "626562733.17", "91,177,659.74+3,723,477.08+1,202,738.73", "农业290,155,416.27+苗木1,202,738.73", "10|11"),
    2019: ("94654807.55", "294362078.78", "550803077.66", "68,864,684.11+1,204,668.70+21,949,522.91+2,635,931.83", "农业291,726,146.95+苗木2,635,931.83", "11"),
    2020: ("68751322.84", "238227180.14", "556230065.25", "67,338,743.39+1,403,079.45+9,500.00", "农业238,217,680.14+苗木9,500.00", "10"),
    2021: ("170068429.21", "380463322.60", "685361129.68", "116,224,058.35+1,011,945.50+2,797,806.70+50,034,618.66", "农业377,665,515.90+苗木2,797,806.70", "11|12"),
}


# 西部牧业：乳制品没有拆分出符合“农产品初加工”的收入，早期“其他”
# 也没有拆分饲料。lower为可确认的直接畜牧/饲料收入；upper把所有可能
# 符合但未拆分的乳制品及“其他”计入。上下界跨越门槛时保持待核实。
WESTERN = {
    2013: ("113550272.65", "113550272.65", "413425326.82", "451460275.35", "101,160,700.05+12,389,572.60", "113,550,272.65+214,259,754.25+85,615,299.92", "16"),
    2014: ("75787816.07", "75787816.07", "423328720.89", "771379830.66", "下界=鲜乳75,787,816.07；上界再加自繁与集中采购未拆分的种畜347,540,904.82", "扩展上下界同严格：鲜乳75,787,816.07至鲜乳+种畜423,328,720.89", "17"),
    2015: ("62242497.87", "62242497.87", "554182445.03", "599902012.38", "44,200,297.87+18,042,200.00", "62,242,497.87+352,491,377.82+139,448,569.34", "25|26"),
    2016: ("29333156.30", "29333156.30", "586863366.60", "664584792.47", "26,465,226.47+2,867,929.83", "29,333,156.30+387,551,171.31+169,979,038.99", "29|30|31"),
    2017: ("73753231.66", "73753231.66", "663904125.29", "692557176.69", "11,394,481.08+62,358,750.58", "73,753,231.66+495,627,635.22+94,523,258.41", "27|28"),
    2018: ("76796901.86", "205568563.68", "653427528.44", "677811826.82", "41,276,951.20+35,519,950.66", "下界=严格76,796,901.86+已明确饲料128,771,661.82；上界再加未拆分乳制品447,858,964.76", "27|28|29"),
    2019: ("0.00", "175488269.03", "637712769.96", "649011242.00", "0（已不披露自产乳和种畜收入）", "175,488,269.03+462,224,500.93", "25|26"),
    2020: ("0.00", "190054283.80", "790290683.73", "820327472.41", "0（未披露直接养殖收入）", "190,054,283.80+600,236,399.93", "29|30"),
    2021: ("0.00", "213587100.24", "1078618962.08", "1127956763.43", "0（未披露直接养殖收入）", "213,587,100.24+865,031,861.84", "34|35"),
}


def rounded_ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    return (numerator / denominator).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)


def raw_ratio(numerator: Decimal, denominator: Decimal) -> str:
    return format(numerator / denominator, "f")


def decision(numerator: Decimal, denominator: Decimal) -> tuple[str, str, str]:
    fraction = numerator / denominator
    strict_or_expanded = "是" if fraction >= Decimal("0.50") else "否"
    boundary = "是" if Decimal("0.30") <= fraction < Decimal("0.50") else "否"
    return strict_or_expanded, boundary, f"{rounded_ratio(numerator, denominator):.8f}"


def base_row(src: pd.Series, code: str, year: int, page: str) -> dict:
    return {
        "股票代码": code,
        "公司全称": src["公司全称"],
        "年份": year,
        "行业分类代码": src["行业分类代码"] or "待核实",
        "行业分类名称": src["行业分类名称"] or "待核实",
        "年报主营业务证据PDF页序号": page,
        "公司营业收入证据PDF页序号": src["利润表PDF页序号"],
        "年报链接": src["年报链接"],
        "记录类型": "第十一批A组新增跨年快速复核（未合并）",
        "复核日期": "2026-08-11",
    }


def main() -> None:
    source = pd.read_csv(SOURCE, dtype={"股票代码": str}, keep_default_na=False)
    targets = {"600540", "600359", "300106"}
    selected = source[
        source["股票代码"].isin(targets)
        & ~source["复核状态"].str.startswith("已人工复核", na=False)
    ].sort_values(["股票代码", "年份"])
    assert len(selected) == 27
    assert selected.groupby("股票代码").size().to_dict() == {"300106": 9, "600359": 9, "600540": 9}
    assert not selected.duplicated(["股票代码", "年份"]).any()
    assert set(selected["年份"].astype(int)) == set(range(2013, 2022))

    rows = []
    for _, src in selected.iterrows():
        code, year = src["股票代码"], int(src["年份"])
        if code == "600540":
            expanded_raw, total_raw, expanded_formula, page, precision_note = XINSAI[year]
            strict_n, expanded_n, total = Decimal("0"), Decimal(expanded_raw), Decimal(total_raw)
            strict, _, strict_share = decision(strict_n, total)
            expanded, boundary, expanded_share = decision(expanded_n, total)
            adopted = expanded_n
            row = {
                **base_row(src, code, year, page),
                "涉农业务_保守不重叠口径": "分行业农业收入（扩展口径）",
                "工作表采用涉农业务营业收入_元": f"{adopted:.2f}",
                "工作表采用收入公式": expanded_formula,
                "严格口径营业收入_元": f"{strict_n:.2f}",
                "严格口径收入公式": "0（年报未单列直接种植收入）",
                "严格口径收入下界_元": f"{strict_n:.2f}",
                "严格口径收入上界_元": f"{strict_n:.2f}",
                "严格口径上下界公式": "0（年报未单列直接种植收入）",
                "扩展口径营业收入_元": f"{expanded_n:.2f}",
                "扩展口径收入公式": expanded_formula,
                "可确认扩展口径收入下界_元": f"{expanded_n:.2f}",
                "扩展口径收入下界公式": expanded_formula,
                "扩展口径收入上界_元": f"{expanded_n:.2f}",
                "扩展口径收入上界公式": expanded_formula,
                "公司营业收入_元": f"{total:.2f}",
                "公司营业收入公式": "合并利润表“营业收入”",
                "严格口径原始未四舍五入比例": raw_ratio(strict_n, total),
                "扩展口径原始未四舍五入比例": raw_ratio(expanded_n, total),
                "扩展口径下界原始未四舍五入比例": raw_ratio(expanded_n, total),
                "扩展口径上界原始未四舍五入比例": raw_ratio(expanded_n, total),
                "工作表采用涉农收入占比": expanded_share,
                "严格口径收入占比": strict_share,
                "扩展口径收入占比": expanded_share,
                "严格样本结论": strict,
                "扩展样本结论": expanded,
                "边界样本结论": boundary,
                "是否存在分部收入重叠": "否（扩展分子仅取同一分行业农业收入，不混入分产品或商贸收入）",
                "金额精度或补充证据说明": precision_note,
                "复核说明": f"严格口径0；分行业农业收入占{Decimal(expanded_share)*100:.2f}%。2014年原产品口径48.61%已更正为分行业农业口径50.798245%，避免混入商贸维度。" if year == 2014 else f"严格口径0；分行业农业收入占{Decimal(expanded_share)*100:.2f}%。",
                "待核实点": "2022逐公司行业分类及该公司2022公司—年份入口仍待核实；本批不外推新增。",
            }
        elif code == "600359":
            strict_raw, expanded_raw, total_raw, strict_formula, expanded_formula, page = XINNONG[year]
            strict_n, expanded_n, total = map(Decimal, (strict_raw, expanded_raw, total_raw))
            assert strict_n <= expanded_n <= total
            strict, _, strict_share = decision(strict_n, total)
            expanded, boundary, expanded_share = decision(expanded_n, total)
            adopted = expanded_n
            row = {
                **base_row(src, code, year, page),
                "涉农业务_保守不重叠口径": "种子、苗木、鲜奶/牛（严格）；农业+畜牧业分行业及园林绿化行业内单列苗木（扩展）",
                "工作表采用涉农业务营业收入_元": f"{adopted:.2f}",
                "工作表采用收入公式": expanded_formula,
                "严格口径营业收入_元": f"{strict_n:.2f}",
                "严格口径收入公式": strict_formula,
                "严格口径收入下界_元": f"{strict_n:.2f}",
                "严格口径收入上界_元": f"{strict_n:.2f}",
                "严格口径上下界公式": strict_formula,
                "扩展口径营业收入_元": f"{expanded_n:.2f}",
                "扩展口径收入公式": expanded_formula,
                "可确认扩展口径收入下界_元": f"{expanded_n:.2f}",
                "扩展口径收入下界公式": expanded_formula,
                "扩展口径收入上界_元": f"{expanded_n:.2f}",
                "扩展口径收入上界公式": expanded_formula,
                "公司营业收入_元": f"{total:.2f}",
                "公司营业收入公式": "合并利润表“营业收入”",
                "严格口径原始未四舍五入比例": raw_ratio(strict_n, total),
                "扩展口径原始未四舍五入比例": raw_ratio(expanded_n, total),
                "扩展口径下界原始未四舍五入比例": raw_ratio(expanded_n, total),
                "扩展口径上界原始未四舍五入比例": raw_ratio(expanded_n, total),
                "工作表采用涉农收入占比": expanded_share,
                "严格口径收入占比": strict_share,
                "扩展口径收入占比": expanded_share,
                "严格样本结论": strict,
                "扩展样本结论": expanded,
                "边界样本结论": boundary,
                "是否存在分部收入重叠": "否（农业、畜牧业与园林绿化为互斥分行业；扩展仅从园林绿化中取单列苗木，不计工程施工）",
                "金额精度或补充证据说明": "",
                "复核说明": f"严格口径占{Decimal(strict_share)*100:.2f}%；农业、畜牧业分行业加园林绿化行业内单列苗木的扩展口径占{Decimal(expanded_share)*100:.2f}%。苗木未包含在农业分行业，故相加不重叠。",
                "待核实点": "2022逐公司行业分类及该公司2022公司—年份入口仍待核实；本批不外推新增。",
            }
        else:
            strict_raw, lower_raw, upper_raw, total_raw, strict_formula, upper_formula, page = WESTERN[year]
            strict_n, lower_n, total = map(Decimal, (strict_raw, lower_raw, total_raw))
            strict, _, strict_share = decision(strict_n, total)
            strict_is_bounded = year == 2014
            if strict_is_bounded:
                strict = "待核实"
            if upper_raw:
                upper_n = Decimal(upper_raw)
                assert strict_n <= lower_n <= upper_n <= total
                expanded, boundary = "待核实", "待核实"
                expanded_share = ""
                adopted_n = ""
                expanded_n = ""
                upper_share = raw_ratio(upper_n, total)
                note = (
                    f"可确认扩展下界占{rounded_ratio(lower_n,total)*100:.2f}%，若未拆分乳制品/其他中符合初加工或饲料的部分全部计入，"
                    f"上界占{rounded_ratio(upper_n,total)*100:.2f}%；上下界跨越门槛，不能定论。"
                )
                pending = (
                    "乳制品未拆分符合初加工定义的收入；早期“其他”未拆分饲料收入，禁止估算。"
                    "另：2022逐公司行业分类及该公司2022公司—年份入口仍待核实，本批不外推新增。"
                )
            else:
                upper_n = lower_n
                expanded, boundary, expanded_share = decision(lower_n, total)
                adopted_n = f"{strict_n:.2f}"
                expanded_n = f"{lower_n:.2f}"
                upper_share = raw_ratio(upper_n, total)
                note = "直接畜牧收入本身已超过50%，不依赖乳制品拆分即可纳入严格和扩展样本。"
                pending = "2022逐公司行业分类及该公司2022公司—年份入口仍待核实；本批不外推新增。"
            if year == 2014:
                lower_formula = "鲜乳75,787,816.07"
            elif year == 2018:
                lower_formula = "严格口径76,796,901.86+已明确饲料128,771,661.82"
            elif year <= 2017:
                lower_formula = strict_formula
            else:
                lower_formula = f"饲料{lower_n:,.2f}"
            precision_note = (
                "采用2019年当年年报披露的饲料175,488,269.03元；2020年年报比较栏将2019年饲料重列为156,287,472.28元，保留该后续重列口径差异，不以比较数覆盖当年披露值。"
                if year == 2019 else ""
            )
            row = {
                **base_row(src, code, year, page),
                "涉农业务_保守不重叠口径": "自产生鲜乳、种畜；单列饲料（扩展下界）",
                "工作表采用涉农业务营业收入_元": adopted_n,
                "工作表采用收入公式": "" if upper_raw else strict_formula,
                "严格口径营业收入_元": "" if strict_is_bounded else f"{strict_n:.2f}",
                "严格口径收入公式": "" if strict_is_bounded else strict_formula,
                "严格口径收入下界_元": f"{strict_n:.2f}",
                "严格口径收入上界_元": f"{upper_n:.2f}" if strict_is_bounded else f"{strict_n:.2f}",
                "严格口径上下界公式": strict_formula,
                "扩展口径营业收入_元": expanded_n,
                "扩展口径收入公式": "" if upper_raw else f"{lower_n:.2f}（严格口径已达标）",
                "可确认扩展口径收入下界_元": f"{lower_n:.2f}",
                "扩展口径收入下界公式": lower_formula,
                "扩展口径收入上界_元": f"{upper_n:.2f}",
                "扩展口径收入上界公式": upper_formula,
                "公司营业收入_元": f"{total:.2f}",
                "公司营业收入公式": "合并利润表“营业收入”",
                "严格口径原始未四舍五入比例": "" if strict_is_bounded else raw_ratio(strict_n, total),
                "扩展口径原始未四舍五入比例": "" if upper_raw else raw_ratio(lower_n, total),
                "扩展口径下界原始未四舍五入比例": raw_ratio(lower_n, total),
                "扩展口径上界原始未四舍五入比例": upper_share,
                "工作表采用涉农收入占比": expanded_share,
                "严格口径收入占比": "" if strict_is_bounded else strict_share,
                "扩展口径收入占比": expanded_share,
                "严格样本结论": strict,
                "扩展样本结论": expanded,
                "边界样本结论": boundary,
                "是否存在分部收入重叠": "否（下界用同一分产品维度；上界仅作敏感性边界，不写入正式分子）",
                "金额精度或补充证据说明": precision_note,
                "复核说明": ("鲜乳为严格/扩展下界9.82%；种畜同时含自繁与集中采购且金额未拆分，鲜乳+全部种畜为上界54.88%，三项结论均不能确定。" if year == 2014 else note),
                "待核实点": pending,
            }
        rows.append(row)

    output = pd.DataFrame(rows)
    assert len(output) == 27
    assert not output.duplicated(["股票代码", "年份"]).any()
    assert output["严格样本结论"].value_counts().to_dict() == {"否": 26, "待核实": 1}
    assert output["扩展样本结论"].value_counts().to_dict() == {"待核实": 9, "否": 9, "是": 9}
    assert output["边界样本结论"].value_counts().to_dict() == {"否": 11, "待核实": 9, "是": 7}
    pending = output[output["扩展样本结论"] == "待核实"]
    assert len(pending) == 9
    assert (pending["工作表采用涉农业务营业收入_元"] == "").all()
    assert (pending["扩展口径营业收入_元"] == "").all()
    output.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    assert output.loc[(output["股票代码"] == "600540") & (output["年份"] == 2014), ["扩展样本结论", "边界样本结论"]].iloc[0].tolist() == ["是", "否"]
    assert output.loc[(output["股票代码"] == "300106") & (output["年份"] == 2014), ["严格样本结论", "扩展样本结论", "边界样本结论"]].iloc[0].tolist() == ["待核实", "待核实", "待核实"]
    assert output.loc[(output["股票代码"] == "300106") & (output["年份"] == 2014), ["严格口径营业收入_元", "严格口径收入下界_元", "严格口径收入上界_元"]].iloc[0].tolist() == ["", "75787816.07", "423328720.89"]
    assert output.loc[(output["股票代码"] == "300106") & (output["年份"] == 2018), "可确认扩展口径收入下界_元"].iloc[0] == "205568563.68"
    print("batch11-A rows=27; strict no=26/pending=1; expanded yes=9/no=9/pending=9; boundary yes=7/no=11/pending=9; not merged")


if __name__ == "__main__":
    main()
