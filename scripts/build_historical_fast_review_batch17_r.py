#!/usr/bin/env python3
"""Build standalone historical fast-review batch 17-R from fixed v26.

Traditional Chinese medicines, pharmaceutical products and plant extracts are
deep processing. Only separately disclosed external revenue from herb planting,
primary processing or agricultural inputs can be included. Bases, biological
assets, tax exemptions and business scopes do not replace external revenue.
"""
from decimal import Decimal, getcontext
from pathlib import Path

import pandas as pd


getcontext().prec = 60
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v26_跨年快速复核第十五批第二组.csv"
OUTPUT = ROOT / "outputs" / "跨年快速复核第十七批_R组_3家公司.csv"

# Total revenue; mixed ginseng-category revenue/cost; product "other"
# revenue/cost. The two product lines are mutually exclusive in the product
# dimension, but neither can be separated into eligible and deep processing.
YISHENG = {
    2014: ("787894295.06", "88580624.61", "71244241.32", "66360231.28", "19416130.15"),
    2015: ("819598117.29", "38173020.91", "18391107.11", "63008863.79", "21116864.86"),
    2018: ("975088200.72", "47282341.15", "20045088.30", "99370079.86", "35920488.88"),
    2019: ("1012748483.99", "63406775.66", "33238123.81", "73616186.92", "29514751.27"),
    2020: ("842589907.04", "68072833.83", "31567445.40", "52439783.10", "22898414.25"),
    2021: ("877929541.89", "77423738.94", "30220404.19", "52879890.38", "22525759.17"),
    2022: ("830041323.93", "52161798.63", "23204099.97", "55978770.81", "23597912.93"),
}

# Total revenue; excluded main plant-extract revenue/cost; and other-business
# plant-extract/manufacturing revenue/cost used only as a conservative upper
# bound because possible seedling/agricultural sales are not separately stated.
LAYN = {
    2014: ("660404253.78", "294182146.57", "238268815.30", "9914073.13", "6523201.72"),
    2015: ("514471244.30", "283635326.69", "214993427.46", "3680433.51", "2760401.64"),
    2018: ("619556202.78", "408424096.80", "304711266.24", "4662651.01", "2746046.39"),
    2019: ("741402631.26", "518608608.14", "375255184.92", "10555551.43", "4742718.94"),
    2020: ("783671413.74", "623335249.85", "469267274.91", "28982594.00", "12753484.40"),
    2021: ("1053235426.39", "986375138.60", "709189279.78", "28880909.08", "17009072.06"),
    2022: ("1400737343.44", "1267821212.48", "906324060.77", "61531743.93", "35656243.61"),
}

# Total revenue; mixed processing/other main-business revenue/cost; audited
# other-business revenue/cost. The first and second revenue dimensions are
# mutually exclusive, so they may be added only as an upper-bound calculation.
TIBET = {
    2014: ("1668036041.63", "956845.22", "647771.84", "6754098.46", "2016299.72"),
    2015: ("1382755815.61", "1242624.95", "1340348.42", "7029457.31", "2863431.68"),
    2018: ("1027879210.33", "811323.41", "1022969.54", "6237492.79", "2150567.13"),
    2019: ("1256021957.79", "802596.59", "837052.66", "6998005.74", "2022308.05"),
    2020: ("1373105105.65", "466800.00", "531000.00", "11492078.50", "6309774.43"),
    2021: ("2138586552.67", "592100.00", "658400.00", "12055061.42", "9391477.69"),
    2022: ("2554609066.22", "1105200.00", "1403000.00", "9690830.48", "5182138.20"),
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
        source["股票代码"].isin(["002166", "002566", "600211"])
        & source["复核状态"].str.startswith("年报及业务表已定位", na=False)
    ].sort_values(["股票代码", "年份"])
    assert len(source) == 958 and len(selected) == 21
    assert selected.groupby("股票代码").size().to_dict() == {"002166": 7, "002566": 7, "600211": 7}
    assert not selected.duplicated(["股票代码", "年份"]).any()

    rows = []
    for _, src in selected.iterrows():
        code, year = src["股票代码"], int(src["年份"])
        mixed_revenue = mixed_cost = other_revenue = other_cost = D("0")
        deep_revenue = deep_cost = D("0")
        excluded_bt_other = D("0")

        if code == "002566":
            total_s, mixed_s, mixed_cost_s, other_s, other_cost_s = YISHENG[year]
            total, mixed_revenue, mixed_cost, other_revenue, other_cost = map(
                D, (total_s, mixed_s, mixed_cost_s, other_s, other_cost_s)
            )
            strict_lo = expanded_lo = D("0")
            strict_hi = expanded_hi = mixed_revenue + other_revenue
            ginseng_label = "人参及相关产品" if year in (2014, 2015) else "人参类产品"
            strict_business = f"未单列中药材种植对外收入；{ginseng_label}及产品“其他”仅作上界"
            expanded_business = f"未单列可确认的中药材初级加工收入；{ginseng_label}及产品“其他”仅作上界"
            strict_formula = expanded_formula = (
                f"下界=0；上界={ginseng_label}{mixed_revenue:.2f}+未拆产品其他{other_revenue:.2f}={strict_hi:.2f}"
            )
            deep_label = f"中成药、针剂、胶囊、饮片、健康食品和化妆品；{ginseng_label}另作上界"
            overlap = f"{ginseng_label}与产品“其他”为同一产品维度互斥项目；不叠加行业、地区或销售模式；种植基地内部供料不另计"
            reason = f"公司披露人参种植基地和全产业链，但未单列种植对外收入；{ginseng_label}混有饮片、红参制品及健康食品等加工品，不能整体纳入。"
            pending = f"{ginseng_label}及产品“其他”未拆中药材种植/初级加工与深加工收入，只作上界；上界仍低于30%。"
            cost_note = f"{ginseng_label}成本{mixed_cost:.2f}+产品其他成本{other_cost:.2f}={mixed_cost + other_cost:.2f}，只作上界反向证据"
            evidence_extra = "2015年管理层明确披露人参深加工产品及红参膏/浓缩液；其他年份人参类亦含饮片、食品等混合品"
        elif code == "002166":
            total_s, deep_s, deep_cost_s, other_s, other_cost_s = LAYN[year]
            total, deep_revenue, deep_cost, other_revenue, other_cost = map(
                D, (total_s, deep_s, deep_cost_s, other_s, other_cost_s)
            )
            strict_lo = expanded_lo = D("0")
            strict_hi = expanded_hi = other_revenue
            excluded_bt_other = D("29124165.28") if year == 2022 else D("0")
            strict_business = "种苗/农副产品外销金额未单列；其他业务-植物提取/制造业仅作上界"
            expanded_business = "农产品初级加工或农业投入品收入未单列；其他业务-植物提取/制造业仅作上界"
            strict_formula = expanded_formula = f"下界=0；上界=排除BT后的其他业务-植物提取/制造业{other_revenue:.2f}"
            deep_label = "罗汉果、甜叶菊、茶叶及工业大麻等植物提取物"
            overlap = "主营植物提取和BT业务明确排除；其他业务植物提取/制造业作上界，不与地区维度或BT其他业务相加"
            reason = "植物提取属于深加工；莱茵农业承担种苗研发培育，2021年还披露优惠价格对外提供种苗，但金额未单列，故不能把未单列直接认定为零。"
            pending = "种苗或农副产品外销金额未拆，不估算；2022行业分类字段仍按v26保留待核实。" if year == 2022 else "种苗或农副产品外销金额未拆，不估算。"
            cost_note = f"主营植物提取收入{deep_revenue:.2f}、成本{deep_cost:.2f}，均为深加工排除项；上界类别成本{other_cost:.2f}只作反向证据"
            evidence_extra = "2021年报称以低于市场的优惠价格向合作社提供自研种苗160万株；2022年免费发放种苗，莱茵神果源业务范围含农副产品销售，均未单列收入。" if year in (2021, 2022) else "种苗研发培育或原料基地事实不替代外销收入；未拆其他制造业只作保守上界"
        else:
            total_s, mixed_s, mixed_cost_s, other_s, other_cost_s = TIBET[year]
            total, mixed_revenue, mixed_cost, other_revenue, other_cost = map(
                D, (total_s, mixed_s, mixed_cost_s, other_s, other_cost_s)
            )
            strict_lo = expanded_lo = D("0")
            strict_hi = expanded_hi = mixed_revenue + other_revenue
            processing_label = (
                "加工类" if year in (2014, 2015)
                else "药品加工及其他" if year in (2018, 2019)
                else "外加工类"
            )
            strict_business = f"未单列藏药材/中药材种植对外收入；{processing_label}、其他业务只作上界"
            expanded_business = "未单列中药材初级加工或农业投入品收入；未拆项目只作上界"
            strict_formula = expanded_formula = (
                f"下界=0；上界=未拆{processing_label}{mixed_revenue:.2f}+审计其他业务{other_revenue:.2f}={strict_hi:.2f}"
            )
            deep_label = "生物制药、藏药、中药、化学药及医药商业贸易"
            overlap = "加工及其他属于主营产品维度，其他业务属于互斥收入层级，可相加作上界；不叠加行业和地区维度"
            reason = "藏药材种植基地和农业资源子公司证明业务存在，但销售端未单列种植或初加工收入；药品及医药贸易不纳入。"
            precision_note = "；年报以万元列示且保留两位小数，换算为元后的精度至百元" if year >= 2020 else ""
            pending = f"{processing_label}和审计其他业务未拆具体性质，只作上界；上界不足1%。" + ("2022行业分类仍待核实。" if year == 2022 else "")
            cost_note = f"{processing_label}成本{mixed_cost:.2f}+其他业务成本{other_cost:.2f}={mixed_cost + other_cost:.2f}，只作上界反向证据{precision_note}"
            evidence_extra = "公司披露藏药材基地/农业资源子公司，但生产性生物资产未列金额，主营收入仍按药品制造、贸易及加工类披露"

        assert D("0") <= strict_lo <= strict_hi <= total
        assert D("0") <= expanded_lo <= expanded_hi <= total
        sr_lo, sr_hi = strict_lo / total, strict_hi / total
        er_lo, er_hi = expanded_lo / total, expanded_hi / total
        assert compact(total_s) in compact(src["利润表原文摘录"])

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
            "人参类或加工其他混合收入_元_上界": f"{mixed_revenue:.2f}" if mixed_revenue else "",
            "人参类或加工其他混合成本_元_反向证据": f"{mixed_cost:.2f}" if mixed_cost else "",
            "其他业务或产品其他收入_元_上界": f"{other_revenue:.2f}" if other_revenue else "",
            "其他业务或产品其他成本_元_反向证据": f"{other_cost:.2f}" if other_cost else "",
            "BT其他业务收入_元_排除证据": f"{excluded_bt_other:.2f}" if excluded_bt_other else "",
            "深加工或排除类别": deep_label,
            "深加工类别收入_元_反向证据": f"{deep_revenue:.2f}" if deep_revenue else "",
            "深加工类别成本_元_反向证据": f"{deep_cost:.2f}" if deep_cost else "",
            "收入成本判别": cost_note,
            "严格样本结论": threshold(sr_lo, sr_hi),
            "扩展样本结论": threshold(er_lo, er_hi),
            "边界样本结论": boundary(er_lo, er_hi),
            "是否存在分部收入重叠": overlap,
            "纳入或剔除理由": reason,
            "待核实点": pending,
            "年报主营业务证据PDF页序号": src["年报主营业务候选PDF页序号"],
            "公司营业收入证据PDF页序号": src["利润表PDF页序号"],
            "补充证据说明": evidence_extra,
            "年报链接": src["年报链接"],
            "2022行业字段处理": "沿用v26原值；待核实字段不插值、不复制相邻年份",
            "记录类型": "跨年快速复核第十七批R组（未合并）",
            "复核状态": "已人工复核（第十七批R组；主表未合并）",
            "复核日期": "2026-08-11",
        })

    out = pd.DataFrame(rows)
    assert len(out) == 21 and not out.duplicated(["股票代码", "年份"]).any()
    assert out["严格样本结论"].value_counts().to_dict() == {"否": 21}
    assert out["扩展样本结论"].value_counts().to_dict() == {"否": 21}
    assert out["边界样本结论"].value_counts().to_dict() == {"否": 21}
    assert out["严格口径正式涉农收入_元"].eq("").all()
    assert out["扩展口径正式涉农收入_元"].eq("").all()
    ys = out[out["股票代码"] == "002566"].set_index("年份")
    assert ys["人参类或加工其他混合收入_元_上界"].to_dict() == {
        year: values[1] for year, values in YISHENG.items()
    }
    assert ys["人参类或加工其他混合成本_元_反向证据"].to_dict() == {
        year: values[2] for year, values in YISHENG.items()
    }
    assert ys["其他业务或产品其他收入_元_上界"].to_dict() == {
        year: values[3] for year, values in YISHENG.items()
    }
    assert ys["其他业务或产品其他成本_元_反向证据"].to_dict() == {
        year: values[4] for year, values in YISHENG.items()
    }
    assert ys.loc[[2014, 2015], "严格口径上下界公式"].str.contains("人参及相关产品").all()
    assert ys.loc[[2018, 2019, 2020, 2021, 2022], "严格口径上下界公式"].str.contains("人参类产品").all()
    assert ys.loc[2022, "公司营业收入_元"] == "830041323.93"
    assert ys.loc[2022, "严格口径收入上界_元"] == "108140569.44"
    assert ys.loc[2022, "人参类或加工其他混合成本_元_反向证据"] == "23204099.97"
    layn = out[out["股票代码"] == "002166"].set_index("年份")
    assert layn["严格口径收入下界_元"].eq("0.00").all()
    assert layn["严格口径收入上界_元"].to_dict() == {
        year: values[3] for year, values in LAYN.items()
    }
    assert layn["其他业务或产品其他成本_元_反向证据"].to_dict() == {
        year: values[4] for year, values in LAYN.items()
    }
    assert layn["深加工类别收入_元_反向证据"].to_dict() == {
        year: values[1] for year, values in LAYN.items()
    }
    assert layn["深加工类别成本_元_反向证据"].to_dict() == {
        year: values[2] for year, values in LAYN.items()
    }
    assert layn.loc[2022, "BT其他业务收入_元_排除证据"] == "29124165.28"
    assert layn.drop(index=2022)["BT其他业务收入_元_排除证据"].eq("").all()
    layn22 = layn.loc[2022]
    assert layn22["公司营业收入_元"] == "1400737343.44"
    assert layn22["严格口径收入上界_元"] == "61531743.93"
    assert layn22["深加工类别收入_元_反向证据"] == "1267821212.48"
    assert layn22["深加工类别成本_元_反向证据"] == "906324060.77"
    tibet = out[out["股票代码"] == "600211"].set_index("年份")
    assert tibet["人参类或加工其他混合收入_元_上界"].to_dict() == {
        year: values[1] for year, values in TIBET.items()
    }
    assert tibet["人参类或加工其他混合成本_元_反向证据"].to_dict() == {
        year: values[2] for year, values in TIBET.items()
    }
    assert tibet["其他业务或产品其他收入_元_上界"].to_dict() == {
        year: values[3] for year, values in TIBET.items()
    }
    assert tibet["其他业务或产品其他成本_元_反向证据"].to_dict() == {
        year: values[4] for year, values in TIBET.items()
    }
    assert tibet.loc[[2014, 2015], "严格口径上下界公式"].str.contains("加工类").all()
    assert tibet.loc[[2018, 2019], "严格口径上下界公式"].str.contains("药品加工及其他").all()
    assert tibet.loc[[2020, 2021, 2022], "严格口径上下界公式"].str.contains("外加工类").all()
    assert tibet.loc[[2020, 2021, 2022], "收入成本判别"].str.contains("精度至百元").all()
    tibet22 = tibet.loc[2022]
    assert tibet22["公司营业收入_元"] == "2554609066.22"
    assert tibet22["严格口径收入上界_元"] == "10796030.48"
    assert tibet22["人参类或加工其他混合成本_元_反向证据"] == "1403000.00"
    assert tibet22["其他业务或产品其他成本_元_反向证据"] == "5182138.20"
    assert out.loc[out["年份"].eq(2022), "行业分类代码"].eq("待核实").all()
    assert out.loc[out["年份"].eq(2022), "行业分类名称"].eq("待核实").all()
    assert out["年报链接"].str.startswith("https://static.cninfo.com.cn/").all()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("batch17-R rows=21; strict no=21; expanded no=21; boundary no=21; not merged")


if __name__ == "__main__":
    main()
