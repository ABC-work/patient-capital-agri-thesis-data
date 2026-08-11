#!/usr/bin/env python3
"""Build batch 14-H evidence for three issuers from the fixed v23 table.

This script creates an independent review CSV.  It does not edit or merge v23.
All threshold decisions use Decimal bounds before any displayed rounding.
"""
from decimal import Decimal, getcontext
from pathlib import Path

import pandas as pd


getcontext().prec = 60
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v23_跨年快速复核第十三批.csv"
OUTPUT = ROOT / "outputs" / "跨年快速复核第十四批_H组_3家公司.csv"


# Nongfa: the conservative lower bound is built only from clearly eligible
# product rows (fertiliser, pesticide and named seed products).  The industry
# rows for farm-input trade and seed sales are never used as a lower bound:
# any positive amount not explained by the eligible product rows is retained
# only as an upper-bound increment.  This avoids subtracting marble (or any
# other product) across the industry/product dimensions.
NONGFA = {
    2015: ("2705845160.97", "2659540958.28", "690365642.49", "524641884.90", "271795.87", "238192.67", "3772977948.58", "10|11"),
    2016: ("3192228288.06", "3086896900.51", "786037744.64", "602650357.95", "1376357.62", "1352986.80", "4414501117.90", "13|14"),
    2017: ("2888860039.79", "2832459563.39", "602561251.00", "487836745.88", "0", "0", "3866695067.04", "12|13"),
    2018: ("2337062026.14", "2264682694.40", "635716423.15", "500644537.65", "0", "0", "3446395314.76", "13|14"),
    2019: ("4119079773.41", "4019270095.45", "604832994.77", "468950287.02", "0", "0", "5135725233.60", "13|14"),
    2020: ("2579173582.14", "2488832930.01", "616785564.82", "484976891.48", "0", "0", "3662548774.43", "13|14"),
    2021: ("2270837807.90", "2158112606.96", "877744222.59", "694107118.97", "0", "0", "3764392752.13", "15"),
}


# name, product revenue, product cost.  Flour-processing outputs (bran, gluten
# powder, starch, flour and yellow powder), commodity grain, alcohol grain,
# marble, nuclear-radiation services and ambiguous "other" products are not in
# this table.  Crop rows are included only where the report identifies them as
# seed products (explicitly in the name or through the product cost category).
NONGFA_ELIGIBLE_PRODUCTS = {
    2015: (
        ("小麦种", "293504919.14", "251964009.18"), ("玉米种", "134991162.71", "83049045.58"),
        ("其他经济作物种子", "18576351.15", "16460713.77"), ("马铃薯种", "43187667.85", "23461163.16"),
        ("豆类种", "4809935.81", "3686418.49"), ("水稻种", "120386633.35", "83601591.71"),
        ("化肥", "2530701608.66", "2510107891.52"), ("棉花种", "1831757.25", "1283018.23"),
        ("油菜种", "8341484.96", "5470816.46"), ("芝麻种", "533169.60", "317133.09"),
        ("甘蔗种", "7245589.00", "5610110.18"), ("农药", "149208619.66", "123277094.19"),
        ("蔬菜种", "3039025.02", "3034670.68"), ("谷种", "79708.50", "44246.80"),
        ("花生种", "13016557.40", "12724436.87"),
    ),
    2016: (
        ("小麦种", "339536553.48", "295114286.56"), ("玉米种", "166262449.71", "105971744.20"),
        ("其他经济作物种子", "10836071.87", "9593824.96"), ("马铃薯种", "66582656.70", "41579560.26"),
        ("豆类种", "10100000.76", "8920643.86"), ("水稻种", "148318695.30", "103114982.00"),
        ("化肥", "2784265086.04", "2765161658.54"), ("棉花种", "1857123.98", "2759360.48"),
        ("油菜种", "8502205.62", "4688263.32"), ("芝麻种", "455070.34", "309306.21"),
        ("甘蔗种", "5998421.50", "3921687.24"), ("农药", "407063959.93", "320726508.08"),
        ("蔬菜种", "8685728.08", "7203603.57"), ("谷种", "7372.00", "4416.67"),
        ("花生种", "21813315.53", "19326393.51"),
    ),
    2017: (
        ("小麦种", "307846630.47", "264324676.80"), ("玉米种", "124991185.45", "93182660.60"),
        ("其他经济作物种子", "3182423.89", "2656924.31"), ("马铃薯种", "11190346.00", "10180356.50"),
        ("豆类种", "12137342.86", "12264111.49"), ("水稻种", "123011158.36", "90275624.32"),
        ("化肥", "2501366822.68", "2479248501.49"), ("棉花种", "1899004.04", "2026769.12"),
        ("油菜种", "5824366.14", "3243669.24"), ("芝麻种", "230545.69", "189365.37"),
        ("甘蔗种", "3157453.92", "2859924.38"), ("农药", "387493217.11", "353211061.90"),
        ("蔬菜种", "1360843.42", "644146.02"), ("谷种", "7558.00", "5540.64"),
        ("花生种", "12698406.80", "11303095.88"), ("草籽", "8595468.16", "8064686.12"),
    ),
    2018: (
        ("小麦种", "325954310.13", "272677234.80"), ("玉米种", "158099992.06", "110520715.91"),
        ("其他经济作物种子", "7977348.69", "6750927.50"), ("马铃薯种", "1151643.00", "1024478.00"),
        ("豆类种", "19105307.04", "16674622.57"), ("水稻种", "100552934.59", "74306924.18"),
        ("化肥", "1937006272.41", "1914780003.44"), ("棉花种", "3609149.98", "3546981.23"),
        ("油菜种", "10313428.50", "6173239.79"), ("芝麻种", "425185.02", "258460.37"),
        ("甘蔗种", "3006888.99", "3296813.54"), ("农药", "403551799.65", "353068480.28"),
        ("蔬菜种", "42615.00", "96305.20"), ("谷种", "7239.00", "5219.19"),
        ("花生种", "7498318.38", "6344438.26"), ("草籽", "11645373.16", "10695791.53"),
    ),
    2019: (
        ("小麦种", "294770346.82", "251042398.07"), ("玉米种", "159931721.55", "107111995.46"),
        ("其他经济作物种子", "13735650.18", "11982427.06"), ("豆类种", "4727804.35", "4821526.37"),
        ("水稻种", "109604857.74", "80269451.53"), ("化肥", "3794145890.80", "3765580774.38"),
        ("棉花种", "3385335.33", "3319045.94"), ("油菜种", "14735657.60", "8802321.99"),
        ("农药", "324933882.61", "253689321.07"), ("花生种", "11074986.46", "9479303.74"),
        ("草籽", "7605004.10", "6996264.01"),
    ),
    2020: (
        ("小麦种", "354328757.02", "305180217.25"), ("玉米种", "142757118.58", "98127977.56"),
        ("水稻种", "111843727.45", "81526933.48"), ("化肥", "2293549686.28", "2266617145.58"),
        ("农药", "289882540.90", "226025135.24"), ("花生种", "11143070.26", "9963672.73"),
    ),
    2021: (
        ("小麦种", "522207949.66", "443269591.41"), ("玉米种", "218475628.58", "150888540.28"),
        ("水稻种", "129256290.47", "93213616.21"), ("化肥", "1833379155.06", "1805780145.05"),
        ("农药", "437458652.84", "352332461.91"), ("花生种", "7804353.88", "6735371.07"),
    ),
}


# Tongwei: strict_upper is the most specific available aquaculture-containing
# row.  expanded_lower is separately disclosed feed/veterinary-input revenue;
# expanded_upper is the whole agricultural-business row when food processing,
# aquaculture, feed and related activities cannot be separated.  From 2020 the
# report combines feed, food and related business, so the lower bound is zero.
TONGWEI = {
    2014: dict(strict_upper="1028553560.74", strict_cost="976754887.90", expanded_lower="14278265338.47", expanded_lower_cost="12618698291.07", expanded_upper="15306818900.21", expanded_upper_cost="13595453178.97", total="15408930605.22", page="12"),
    2015: dict(strict_upper="821974904.61", strict_cost="747748538.70", expanded_lower="13169213948.65", expanded_lower_cost="11388166244.77", expanded_upper="13991188853.26", expanded_upper_cost="12135914783.47", total="14079246514.03", page="10|11"),
    2018: dict(strict_upper="1397308146.26", strict_cost="1328683345.24", expanded_lower="15236344953.40", expanded_lower_cost="13011260056.56", expanded_upper="16815847549.06", expanded_upper_cost="14452638713.47", total="27535170274.25", page="13|14"),
    2019: dict(strict_upper="1904814158.29", strict_cost="1803130447.37", expanded_lower="16688719548.83", expanded_lower_cost="14460739581.77", expanded_upper="18698931318.22", expanded_upper_cost="16349337602.88", total="37555118255.70", page="13|14"),
    2020: dict(strict_upper="20850972852.84", strict_cost="18660128240.51", expanded_lower="0", expanded_lower_cost="0", expanded_upper="20935749897.11", expanded_upper_cost="18699941643.52", total="44200270334.23", page="15|16"),
    2021: dict(strict_upper="24590256728.92", strict_cost="22258698101.39", expanded_lower="0", expanded_lower_cost="0", expanded_upper="24590256728.92", expanded_upper_cost="22258698101.39", total="63491070520.12", page="17|18"),
    2022: dict(strict_upper="31646055679.69", strict_cost="29147668534.83", expanded_lower="0", expanded_lower_cost="0", expanded_upper="31646055679.69", expanded_upper_cost="29147668534.83", total="142422517994.99", page="19|20"),
}


# Guannong: sugar, cotton initial-processing and fruit/vegetable processing are
# mutually exclusive industry rows, but each can contain deep processing and/or
# purchased-product trade.  Their sum is therefore only an expanded upper bound;
# no eligible lower bound is inferred.  No feed revenue was separately reported
# in these pending years (the 2022 feed project was still in trial production).
GUANNONG = {
    2014: (("113291400.00", "493580600.00", "519064200.00"), ("96136000.00", "473078400.00", "414454200.00"), "1153597824.53", "14"),
    2015: (("209361703.10", "384187836.30", "883411209.28"), ("183503648.47", "368399311.55", "741253795.65"), "1531678351.45", "12"),
    2018: (("225600063.54", "703291712.90", "341845746.96"), ("182690378.09", "687421716.23", "282784308.32"), "2174777459.60", "11|12"),
    2019: (("278473369.28", "727893984.37", "302975275.01"), ("243308545.52", "679448499.46", "235447921.83"), "3256880896.35", "12"),
    2020: (("190201170.61", "252396504.53", "577695212.54"), ("147749918.49", "218232073.77", "458198479.79"), "2769325551.73", "11|12"),
    2021: (("130434894.20", "728193566.38", "514145822.26"), ("114560585.27", "690459139.43", "429233424.77"), "3903478371.59", "12"),
    2022: (("106723514.67", "845095330.13", "765774319.98"), ("90750121.54", "907868249.81", "574916256.08"), "2412985493.75", "12"),
}


def D(value) -> Decimal:
    return Decimal(str(value))


def sum_d(values) -> Decimal:
    return sum((D(value) for value in values), D("0"))


def ratio(numerator: Decimal, denominator: Decimal) -> str:
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
        source["股票代码"].isin(["600313", "600438", "600251"])
        & ~source["复核状态"].str.startswith("已人工复核", na=False)
    ].sort_values(["股票代码", "年份"])
    assert len(source) == 958
    assert len(selected) == 21
    assert selected.groupby("股票代码").size().to_dict() == {"600251": 7, "600313": 7, "600438": 7}
    assert not selected.duplicated(["股票代码", "年份"]).any()

    rows = []
    for _, src in selected.iterrows():
        code, year = src["股票代码"], int(src["年份"])
        strict_lo = D("0")
        strict_cost_lo = D("0")
        locator_note = ""

        if code == "600313":
            farm, farm_cost, seed, seed_cost, marble, marble_cost, total_raw, pages = NONGFA[year]
            total = D(total_raw)
            strict_hi = D("0")
            strict_cost_hi = D("0")
            eligible = NONGFA_ELIGIBLE_PRODUCTS[year]
            expanded_lo = sum_d(item[1] for item in eligible)
            expanded_cost_lo = sum_d(item[2] for item in eligible)
            input_revenue = sum_d(item[1] for item in eligible if item[0] in {"化肥", "农药"})
            input_cost = sum_d(item[2] for item in eligible if item[0] in {"化肥", "农药"})
            seed_revenue = expanded_lo - input_revenue
            seed_product_cost = expanded_cost_lo - input_cost
            farm_upper_increment = max(D("0"), D(farm) - input_revenue)
            seed_upper_increment = max(D("0"), D(seed) - seed_revenue)
            farm_cost_upper_increment = max(D("0"), D(farm_cost) - input_cost)
            seed_cost_upper_increment = max(D("0"), D(seed_cost) - seed_product_cost)
            expanded_hi = expanded_lo + farm_upper_increment + seed_upper_increment
            expanded_cost_hi = expanded_cost_lo + farm_cost_upper_increment + seed_cost_upper_increment
            strict_business = "无单列直接农业生产收入"
            strict_formula = "下界=上界=0"
            expanded_business = "同一产品层级明确的化肥、农药及各类种子"
            product_formula = "+".join(f"{name}{D(revenue):.2f}" for name, revenue, _ in eligible)
            expanded_formula = (
                f"下界={product_formula}={expanded_lo:.2f}；"
                f"上界=下界+农资贸易行业未解释增量{farm_upper_increment:.2f}"
                f"+种子销售行业未解释增量{seed_upper_increment:.2f}={expanded_hi:.2f}"
            )
            audit_note = (
                "下界只加总同一分产品层级明确的化肥、农药及种子；农资贸易/种子销售行业行只用于"
                "识别正的未解释上界增量。大理石、粮食贸易、麸皮、谷朊粉、淀粉、面粉、黄粉、"
                "核辐及其他不明确产品均不进下界。"
            )
            cost_formula = (
                f"明确产品成本下界={expanded_cost_lo:.2f}；行业未解释成本增量上界="
                f"{farm_cost_upper_increment + seed_cost_upper_increment:.2f}；扩展成本上界={expanded_cost_hi:.2f}；"
                "成本仅作收入列反核"
            )
            overlap = "否（下界仅采用同一分产品层级；行业行只贡献正的未解释上界增量）"
            assert expanded_lo == input_revenue + seed_revenue
            assert expanded_hi >= expanded_lo
            assert not any(name in {"麸皮", "谷朊粉", "淀粉", "面粉", "黄粉", "大理石", "核辐", "其他"} for name, _, _ in eligible)
        elif code == "600438":
            v = TONGWEI[year]
            total = D(v["total"])
            strict_hi = D(v["strict_upper"])
            strict_cost_hi = D(v["strict_cost"])
            expanded_lo = D(v["expanded_lower"])
            expanded_hi = D(v["expanded_upper"])
            expanded_cost_lo = D(v["expanded_lower_cost"])
            expanded_cost_hi = D(v["expanded_upper_cost"])
            strict_business = "水产养殖收入未从食品加工或饲料相关混合项拆出"
            if year <= 2019:
                strict_formula = f"下界=0；上界=食品加工及养殖{v['strict_upper']}"
                expanded_business = "饲料及兽药（下界）；农牧业务（上界）"
                expanded_formula = f"下界=单列饲料/兽药{v['expanded_lower']}；上界=农牧相关{v['expanded_upper']}"
                audit_note = "水产养殖可属严格口径，但与食品加工混合，故仅作严格上界；光伏、能源及化工全部排除。"
            else:
                strict_formula = f"下界=0；上界=饲料、食品及相关农牧业务{v['strict_upper']}"
                expanded_business = "饲料、食品及相关农牧业务混合项（仅作扩展上界）"
                expanded_formula = f"下界=0；上界=农牧业务{v['expanded_upper']}"
                audit_note = "2020起饲料与食品/养殖未拆，不能把整项作为饲料收入；光伏、能源及化工全部排除。"
            cost_formula = (
                f"严格成本上界={strict_cost_hi:.2f}；扩展成本下界={expanded_cost_lo:.2f}，"
                f"上界={expanded_cost_hi:.2f}；成本未作收入"
            )
            overlap = "否（同一产品/行业层级设上下界，不跨维度重复相加）"
            pages = v["page"]
            if year == 2014:
                locator_note = "v23主营业务页55为公司概况误命中；本批回到官方年报主营业务表PDF页12核值。"
        else:
            revenues, costs, total_raw, pages = GUANNONG[year]
            total = D(total_raw)
            strict_hi = D("0")
            strict_cost_hi = D("0")
            expanded_lo = D("0")
            expanded_hi = sum_d(revenues)
            expanded_cost_lo = D("0")
            expanded_cost_hi = sum_d(costs)
            strict_business = "无单列直接农业生产收入"
            strict_formula = "下界=上界=0"
            expanded_business = "糖业+棉花初加工+果蔬加工业（均仅作混合上界）"
            expanded_formula = "+".join(revenues) + f"={expanded_hi:.2f}（下界=0）"
            cost_formula = "+".join(costs) + f"={expanded_cost_hi:.2f}（上界项目成本反核）"
            audit_note = (
                "糖、番茄、棉花行业行互斥，但分别混有深加工和/或外购贸易；"
                "未拆分前不形成扩展下界。2022饲料项目处于试生产且无单列收入。"
            )
            overlap = "否（仅加总互斥分行业行；未与分产品行交叉相加）"

        denominator_note = "合并利润表‘营业收入’"
        profit_pages = src["利润表PDF页序号"]
        if code == "600251" and year == 2022:
            # v23's saved excerpt contains the preceding accounting-error tables
            # rather than the current P&L, although its locator also records page
            # 68.  The official PDF page 68 gives 2,412,985,493.75; the business
            # section independently reports the rounded 241,298.55万元.
            assert "241298.55万元" in compact(src["主营业务表原文摘录"])
            profit_pages = "68"
            denominator_note += "；官方年报PDF页68，主营业务段241,298.55万元交叉核对"
            locator_note = "v23利润表摘录落在前期差错更正页；本批按其候选定位中的官方年报PDF页68核对当期合并利润表。"
        else:
            assert compact(format(total, "f")) in compact(src["利润表原文摘录"]), (code, year, "P&L denominator")
        assert D("0") <= strict_lo <= strict_hi <= total
        assert D("0") <= expanded_lo <= expanded_hi <= total
        assert strict_cost_lo <= strict_cost_hi
        assert expanded_cost_lo <= expanded_cost_hi
        if strict_cost_hi:
            assert strict_hi != strict_cost_hi
        if expanded_cost_hi:
            assert expanded_hi != expanded_cost_hi

        strict_conclusion = threshold(strict_lo / total, strict_hi / total)
        expanded_conclusion = threshold(expanded_lo / total, expanded_hi / total)
        boundary_conclusion = boundary(expanded_lo / total, expanded_hi / total)
        rows.append({
            "股票代码": code,
            "公司全称": src["公司全称"],
            "年份": year,
            "行业分类代码": src["行业分类代码"] or "待核实",
            "行业分类名称": src["行业分类名称"] or "待核实",
            "严格口径涉农业务": strict_business,
            "严格口径收入下界_元": f"{strict_lo:.2f}",
            "严格口径收入上界_元": f"{strict_hi:.2f}",
            "严格口径上下界公式": strict_formula,
            "严格口径下界占比_原始未四舍五入": ratio(strict_lo, total),
            "严格口径上界占比_原始未四舍五入": ratio(strict_hi, total),
            "扩展口径涉农业务": expanded_business,
            "扩展口径正式涉农收入_元": f"{expanded_lo:.2f}" if expanded_conclusion == "是" else "",
            "扩展口径收入下界_元": f"{expanded_lo:.2f}",
            "扩展口径收入上界_元": f"{expanded_hi:.2f}",
            "扩展口径上下界公式": expanded_formula,
            "扩展口径下界占比_原始未四舍五入": ratio(expanded_lo, total),
            "扩展口径上界占比_原始未四舍五入": ratio(expanded_hi, total),
            "公司营业收入_元": f"{total:.2f}",
            "公司营业收入公式": denominator_note,
            "严格口径成本下界_元_反向证据": f"{strict_cost_lo:.2f}",
            "严格口径成本上界_元_反向证据": f"{strict_cost_hi:.2f}",
            "扩展口径成本下界_元_反向证据": f"{expanded_cost_lo:.2f}",
            "扩展口径成本上界_元_反向证据": f"{expanded_cost_hi:.2f}",
            "收入成本反核说明": cost_formula,
            "严格样本结论": strict_conclusion,
            "扩展样本结论": expanded_conclusion,
            "边界样本结论": boundary_conclusion,
            "是否存在分部收入重叠": overlap,
            "纳入或剔除理由": (
                f"严格区间[{ratio(strict_lo,total)}, {ratio(strict_hi,total)}]；"
                f"扩展区间[{ratio(expanded_lo,total)}, {ratio(expanded_hi,total)}]。{audit_note}"
            ),
            "待核实点": "混合加工/养殖/贸易项目需取得分部明细后才能写入正式分子；无法拆分时不估算。",
            "收入分项证据PDF页序号": pages,
            "公司营业收入证据PDF页序号": profit_pages,
            "证据定位更正说明": locator_note,
            "年报链接": src["年报链接"],
            "2022行业字段处理": "沿用v23原值；待核实时不插值、不复制相邻年份",
            "记录类型": "跨年快速复核第十四批H组（未合并）",
            "复核状态": "已人工复核（第十四批H组；主表未合并）",
            "复核日期": "2026-08-11",
        })

    out = pd.DataFrame(rows)
    assert len(out) == 21 and not out.duplicated(["股票代码", "年份"]).any()
    assert out["严格样本结论"].value_counts().to_dict() == {"否": 21}
    assert out["扩展样本结论"].value_counts().to_dict() == {"是": 10, "否": 7, "待核实": 4}
    assert out["边界样本结论"].value_counts().to_dict() == {"否": 11, "待核实": 9, "是": 1}
    assert out.loc[out["年份"].eq(2022), "行业分类代码"].eq("待核实").all()
    assert out.loc[out["扩展样本结论"].ne("是"), "扩展口径正式涉农收入_元"].eq("").all()
    assert out["年报链接"].str.startswith("https://static.cninfo.com.cn/").all()
    nongfa = out[out["股票代码"].eq("600313")].set_index("年份")
    assert nongfa["扩展样本结论"].eq("是").all()
    assert nongfa["扩展口径收入下界_元"].to_dict() == {
        2015: "3329454190.06", 2016: "3980284710.84", 2017: "3504992772.99",
        2018: "2989947805.60", 2019: "4738651137.54", 2020: "3203504900.49",
        2021: "3148582030.49",
    }
    assert nongfa["扩展口径收入上界_元"].to_dict() == {
        2015: "3396210803.46", 2016: "3981183952.93", 2017: "3504992772.99",
        2018: "2989947805.60", 2019: "4738651137.54", 2020: "3203504900.49",
        2021: "3148582030.49",
    }
    assert all(
        D(upper) >= D(lower)
        for lower, upper in zip(nongfa["扩展口径收入下界_元"], nongfa["扩展口径收入上界_元"])
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("batch14-H rows=21; strict no=21; expanded yes/no/pending=10/7/4; boundary no/pending/yes=11/9/1; not merged")


if __name__ == "__main__":
    main()
