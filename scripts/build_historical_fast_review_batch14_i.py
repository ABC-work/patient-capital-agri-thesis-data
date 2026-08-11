#!/usr/bin/env python3
"""Build batch 14-I deep-processing exclusions from the fixed v23 table.

This script reads v23 but never edits or merges it.  Pickled vegetables,
frozen surimi/meat products, and vinegar/condiments are downstream food
processing.  Agricultural raw-material origin alone is not eligibility.
"""
from decimal import Decimal, getcontext
from pathlib import Path

import pandas as pd


getcontext().prec = 50
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v23_跨年快速复核第十三批.csv"
OUTPUT = ROOT / "outputs" / "跨年快速复核第十四批_I组_3家公司.csv"

# year: disclosed downstream-processing revenue, corresponding cost,
# consolidated operating revenue, evidence label.  Amounts are yuan.
FULING = {
    2014: ("904417167.22", "519771953.77", "906428723.56", "食品加工（榨菜、佐餐开胃菜及榨菜酱油）"),
    2015: ("928675117.19", "519188612.64", "930658889.10", "食品加工（榨菜、佐餐开味菜、榨菜酱油及泡菜）"),
    2018: ("1912126179.47", "846263093.30", "1914353929.10", "食品加工（榨菜、萝卜/佐餐菜、泡菜等）"),
    2019: ("1986683869.27", "822148847.03", "1989593123.12", "食品加工（榨菜、萝卜、泡菜及其他产品）"),
    2020: ("2270409963.62", "947198331.17", "2272746598.51", "食品加工（榨菜、萝卜、泡菜及其他产品）"),
    2021: ("2516387539.60", "1199647112.57", "2518647389.14", "食品加工（榨菜、萝卜、泡菜及其他产品）"),
    2022: ("2545881409.11", "1193914934.27", "2548315095.90", "食品加工（榨菜、萝卜、泡菜及其他产品）"),
}

HAIXIN = {
    2014: ("851634614.42", "590900211.92", "855278185.61", "食品加工制造业（速冻鱼肉/肉制品等）"),
    2015: ("814742962.36", "568492259.16", "814742962.36", "食品加工制造业（速冻鱼肉/肉制品及休闲制品）"),
    2018: ("1144513008.61", "763655195.30", "1144513008.61", "食品加工制造业（速冻鱼肉/肉制品等）"),
    2019: ("1385183736.59", "983847399.66", "1385183736.59", "食品加工制造业（速冻鱼肉/肉制品等）"),
    2020: ("1605751408.05", "1210068647.01", "1605751408.05", "食品加工制造业（速冻鱼肉/肉制品、米面及菜肴等）"),
    2021: ("1550297708.74", "1252294626.51", "1550297708.74", "食品加工制造业（速冻鱼肉/肉制品、米面及菜肴等）"),
    2022: ("1621397148.78", "1257364590.80", "1621397148.78", "食品加工制造业（速冻鱼肉/肉制品、米面及菜肴等）"),
}

HENGSHUN = {
    2014: ("1036656457.12", "597385240.89", "1207580387.67", "酱醋调味品"),
    2015: ("1138235430.96", "669629072.34", "1305428216.69", "酱醋调味品"),
    2018: ("1528001025.93", "865836658.82", "1693683097.45", "调味品（醋、料酒等）"),
    2019: ("1719951521.57", "919885978.70", "1832193611.14", "调味品（醋、料酒等）"),
    2020: ("1939335492.79", "1150560486.89", "2014309859.11", "调味品（醋、料酒等）"),
    2021: ("1846145958.72", "1163758845.24", "1893347829.74", "调味品（醋、料酒及复合调味料等）"),
    2022: ("2031615552.76", "1340053782.89", "2139020033.23", "调味品（醋、酒、酱系列）"),
}

# These residual/"other" lines are not confirmed eligible revenue.  They are
# retained as conservative *upper bounds* so that an exclusion is never
# represented as an exact zero when the annual report has an unsplit category.
FULING_UNSPLIT_UPPER = {
    2014: "2011556.34", 2015: "1983771.91", 2018: "2227749.63",
    2019: "2909253.85", 2020: "2336634.89", 2021: "2259849.54",
    2022: "2433686.79",
}
HAIXIN_UNSPLIT_UPPER = {
    # 2014 = fish-paste line 268,575.23 + other-products line 3,643,571.19.
    2014: "3912146.42", 2015: "3875056.70", 2018: "6570263.16",
    2019: "8611692.23", 2020: "11940198.04", 2021: "12431304.48",
    2022: "13543983.57",
}
HENGSHUN_UNSPLIT_UPPER = {
    2014: "170923930.55", 2015: "167192785.73", 2018: "165682071.52",
    2019: "112242089.57", 2020: "74974366.32", 2021: "47201871.02",
    2022: "107404480.47",
}


def D(value: str) -> Decimal:
    return Decimal(value)


def compact(value: str) -> str:
    return value.replace(",", "").replace(" ", "").replace("\n", "")


def main() -> None:
    src = pd.read_csv(SOURCE, dtype={"股票代码": str}, keep_default_na=False)
    codes = {"002507", "002702", "600305"}
    target = src[
        src["股票代码"].isin(codes)
        & src["复核状态"].str.startswith("年报及业务表已定位", na=False)
    ].sort_values(["股票代码", "年份"])
    assert len(src) == 958
    assert len(target) == 21
    assert target.groupby("股票代码").size().to_dict() == {"002507": 7, "002702": 7, "600305": 7}
    assert not target.duplicated(["股票代码", "年份"]).any()

    rows = []
    for _, s in target.iterrows():
        code, year = s["股票代码"], int(s["年份"])
        if code == "002507":
            deep, deep_cost, total, deep_label = FULING[year]
            unsplit = FULING_UNSPLIT_UPPER[year]
            excluded = "榨菜、萝卜/佐餐菜、泡菜、榨菜酱油等均为腌制或调味食品深加工"
            reason = "公司采购青菜头等农产品并加工销售；原料来自农业不等于公司取得直接农业或初加工收入。"
            evidence_keyword = "榨菜"
            upper_label = "其他业务收入（未拆分，可能包含非涉农项目）"
            upper_formula = f"0—其他业务收入{D(unsplit):.2f}"
            pending = "其他业务收入未拆分，正式分子留空；须取得明细后才能确认其中是否存在直接农业或初加工收入。"
        elif code == "002702":
            deep, deep_cost, total, deep_label = HAIXIN[year]
            unsplit = HAIXIN_UNSPLIT_UPPER[year]
            excluded = "速冻鱼肉制品、速冻肉制品、常温休闲制品、速冻米面及菜肴均为食品深加工"
            reason = "鱼糜或鱼浆是生产原料/中间材料；年报未单列公司外售原料鱼、初加工水产品或农业投入品收入。"
            evidence_keyword = "速冻"
            upper_label = "鱼糜/其他产品未拆候选项" if year == 2014 else "其他产品未拆候选项"
            upper_formula = (
                "0—（鱼糜268575.23+其他产品3643571.19）=3912146.42"
                if year == 2014 else f"0—其他产品{D(unsplit):.2f}"
            )
            pending = "其他产品未拆分；2014年鱼糜亦可能属于初加工候选。正式分子留空，须取得产品性质及外销明细后确认。"
        else:
            deep, deep_cost, total, deep_label = HENGSHUN[year]
            unsplit = HENGSHUN_UNSPLIT_UPPER[year]
            excluded = "食醋、料酒、酱及复合调味料均为发酵或调味食品深加工"
            reason = "粮食等农产品仅为酿造原料；年报未单列种植、初加工农产品或农业投入品收入。"
            evidence_keyword = "调味品"
            upper_label = "非调味品剩余收入（含米业、茶庄、饲料残渣等未拆项目）"
            upper_formula = f"0—（营业收入-调味品收入）={D(unsplit):.2f}"
            pending = "非调味品剩余收入混合米业、茶庄、饲料残渣等项目，正式分子留空；须取得业务明细后确认可纳入口径。"

        deep_n, cost_n, total_n, upper_n = D(deep), D(deep_cost), D(total), D(unsplit)
        assert D("0") < cost_n < deep_n <= total_n
        assert D("0") < upper_n < total_n * D("0.30")
        excerpt = compact(s["主营业务表原文摘录"])
        pnl_excerpt = compact(s["利润表原文摘录"])
        # v23 stores selected candidate pages rather than every adjacent page;
        # exact revenue/cost pairs above were checked against the linked official
        # annual-report tables.  The fixed excerpt must at least retain the
        # downstream category evidence and the P&L denominator.
        assert evidence_keyword in excerpt, (code, year, "downstream category missing")
        assert compact(total) in pnl_excerpt, (code, year, "P&L revenue missing")

        rows.append({
            "股票代码": code,
            "公司全称": s["公司全称"],
            "年份": year,
            "行业分类代码": s["行业分类代码"] or "待核实",
            "行业分类名称": s["行业分类名称"] or "待核实",
            "严格口径涉农业务": f"未确认；以{upper_label}作保守上界",
            "严格口径正式涉农收入_元": "",
            "严格口径收入下界_元": "0.00",
            "严格口径收入上界_元": f"{upper_n:.2f}",
            "严格口径上下界公式": upper_formula,
            "严格口径下界占比_原始未四舍五入": "0",
            "严格口径上界占比_原始未四舍五入": format(upper_n / total_n, "f"),
            "扩展口径涉农业务": f"未确认；以{upper_label}作保守上界",
            "扩展口径正式涉农收入_元": "",
            "扩展口径收入下界_元": "0.00",
            "扩展口径收入上界_元": f"{upper_n:.2f}",
            "扩展口径上下界公式": upper_formula,
            "扩展口径下界占比_原始未四舍五入": "0",
            "扩展口径上界占比_原始未四舍五入": format(upper_n / total_n, "f"),
            "公司营业收入_元": f"{total_n:.2f}",
            "公司营业收入公式": "合并利润表营业收入",
            "未拆候选收入上界_元": f"{upper_n:.2f}",
            "未拆候选上界公式": upper_formula,
            "深加工排除类别": deep_label,
            "深加工收入_元_反向证据": f"{deep_n:.2f}",
            "深加工成本_元_反向证据": f"{cost_n:.2f}",
            "收入成本判别": "深加工收入取营业收入列；对应营业成本仅作反向证据，未进入涉农分子",
            "严格样本结论": "否",
            "扩展样本结论": "否",
            "边界样本结论": "否",
            "是否存在分部收入重叠": "待核实（未拆候选项只作整体上界，不与深加工类别相加）",
            "排除业务说明": excluded,
            "纳入或剔除理由": reason,
            "待核实点": pending + " 因上界仍低于30%，不影响三类样本结论。",
            "年报主营业务证据PDF页序号": s["年报主营业务候选PDF页序号"],
            "公司营业收入证据PDF页序号": s["利润表PDF页序号"],
            "年报链接": s["年报链接"],
            "2022行业字段处理": "沿用v23原值；待核实字段不插值、不复制相邻年份",
            "记录类型": "跨年快速复核第十四批I组（未合并）",
            "复核状态": "已人工复核（第十四批I组；主表未合并）",
            "复核日期": "2026-08-11",
        })

    out = pd.DataFrame(rows)
    assert len(out) == 21 and not out.duplicated(["股票代码", "年份"]).any()
    assert out["严格样本结论"].value_counts().to_dict() == {"否": 21}
    assert out["扩展样本结论"].value_counts().to_dict() == {"否": 21}
    assert out["边界样本结论"].value_counts().to_dict() == {"否": 21}
    assert out["严格口径正式涉农收入_元"].eq("").all()
    assert out["扩展口径正式涉农收入_元"].eq("").all()
    assert (pd.to_numeric(out["严格口径收入上界_元"]) > 0).all()
    assert (pd.to_numeric(out["扩展口径上界占比_原始未四舍五入"]) < 0.30).all()
    assert out.loc[out["年份"].eq(2022), "行业分类代码"].eq("待核实").all()
    assert out.loc[out["年份"].eq(2022), "行业分类名称"].eq("待核实").all()
    assert out["年报链接"].str.startswith("https://static.cninfo.com.cn/").all()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("batch14-I rows=21; strict no=21; expanded no=21; boundary no=21; not merged")


if __name__ == "__main__":
    main()
