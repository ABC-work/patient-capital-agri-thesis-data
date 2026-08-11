#!/usr/bin/env python3
"""Build batch 11-B without modifying the v20 master worktable.

Scope: every still-pending 2013--2021 company-year for 002069, 002086 and
002299 in the fixed v20 master.  Numerators are taken only from the annual
report's revenue column.  Cost-column values are retained solely as guards
against accidental transcription.
"""
from decimal import Decimal, getcontext
from pathlib import Path

import pandas as pd


getcontext().prec = 50
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v20_跨年快速复核第十批.csv"
OUTPUT = ROOT / "outputs" / "跨年快速复核第十一批_B组_3家公司.csv"

# All monetary values are yuan.  `direct` is directly disclosed aquaculture;
# `processing` is the annual-report processing category admitted only to the
# expanded numerator; `combined` is Saint Farm's inseparable raising/slaughter
# category.  Deep-processing and trade are recorded but never added.
VERIFIED = {
    "002069": {
        2013: dict(direct="1235655454.98", processing="728913598.04", trade="571179089.12", total="2620857768.13", page="17", direct_cost="860111192.54", processing_cost="565605786.33"),
        2014: dict(direct="933096131.50", processing="740819392.64", trade="869209494.60", total="2662211458.16", page="14", direct_cost="765007912.31", processing_cost="622151704.91"),
        2015: dict(direct="901856929.95", processing="909953687.63", trade="805999885.55", total="2726780243.72", page="17", direct_cost="767343018.10", processing_cost="800401900.06"),
        2016: dict(direct="901031340.59", processing="957374692.04", trade="1116086374.69", total="3052101909.49", page="20", direct_cost="651868784.47", processing_cost="826742841.56"),
        2017: dict(direct="831008499.42", processing="1093219458.21", trade="1232490530.12", total="3205845988.90", page="22", direct_cost="603227305.02", processing_cost="920579753.30"),
        2018: dict(direct="577521823.69", processing="1113242890.98", trade="1045773057.57", total="2797997387.81", page="22", direct_cost="342594582.62", processing_cost="951988817.82"),
        2019: dict(direct="632859886.94", processing="966450217.64", trade="1040661912.14", total="2728869245.41", page="26", direct_cost="484339062.67", processing_cost="816314289.77"),
        2020: dict(direct="541933116.87", processing="705899288.35", trade="617624143.06", total="1926660963.71", page="16", direct_cost="381039962.75", processing_cost="588540073.58"),
        2021: dict(direct="567571068.91", processing="674780016.53", trade="798087788.63", total="2082837515.23", page="13", direct_cost="415865374.48", processing_cost="559426353.38"),
    },
    "002086": {
        2013: dict(direct="215515003.62", processing="385728129.74", trade="21071023.94", total="615510337.66", page="19", direct_cost="108935856.46", processing_cost="338764052.54"),
        2014: dict(direct="256217790.83", processing="332082423.59", trade="14958029.08", total="604504765.46", page="15", direct_cost="148766723.23", processing_cost="302514635.71"),
        2015: dict(direct="333083799.84", processing="323525836.01", trade="20250672.98", total="674606421.29", page="16", direct_cost="196165677.90", processing_cost="299490700.35"),
        2016: dict(direct="274963705.52", processing="332802489.72", trade="25028662.37", total="706710877.50", page="20", direct_cost="195332022.81", processing_cost="299409463.92"),
        2017: dict(direct="300023195.89", processing="377465852.07", trade="20609378.90", total="779407279.46", page="21", direct_cost="183744085.42", processing_cost="353951521.24"),
        2018: dict(direct="287991672.69", processing="366412004.24", trade="22656902.90", total="725034292.17", page="17", direct_cost="167371520.44", processing_cost="339878476.68"),
        2019: dict(direct="186180806.53", processing="316216821.06", trade="49095282.26", total="585575782.24", page="18", direct_cost="191933757.87", processing_cost="285020440.07"),
        2020: dict(direct="104713134.71", processing="186034010.90", trade="64026641.98", total="427984778.72", page="19", direct_cost="160868388.96", processing_cost="186305323.48"),
        2021: dict(direct="100063087.87", processing="138151270.05", trade="30971700.17", total="388969421.15", page="18|19", direct_cost="158821450.56", processing_cost="145089676.16"),
    },
    "002299": {
        2013: dict(combined="4500397751.55", deep="", total="4708227702.10", page="19", combined_cost="4425186145.64"),
        2014: dict(combined="6077965627.47", deep="", total="6436059894.41", page="18", combined_cost="5616506799.72"),
        2015: dict(combined="6571799379.43", deep="", total="6939825279.22", page="15", combined_cost="6605815918.09"),
        2016: dict(combined="7989406799.90", deep="", total="8340420528.35", page="15", combined_cost="7034479795.03"),
        2017: dict(combined="7562392031.83", deep="2166793728.96", total="10158794866.30", page="17", combined_cost="7071410512.49", deep_cost="1617540340.34"),
        2018: dict(combined="8135082912.64", deep="2889950558.61", total="11547228731.64", page="17", combined_cost="6601357788.80", deep_cost="2194650253.37"),
        2019: dict(combined="9532849891.11", deep="3944622268.14", total="14558436761.99", page="17", combined_cost="6334794244.25", deep_cost="2580296215.86"),
        2020: dict(combined="8871897956.83", deep="4077372033.95", total="13744599499.34", page="16", combined_cost="7286220670.31", deep_cost="2957690556.41"),
        2021: dict(combined="8927877297.88", deep="4645555339.39", total="14478196536.20", page="24", combined_cost="8506670686.22", deep_cost="3873479676.14"),
    },
}


def raw_ratio(numerator: Decimal, denominator: Decimal) -> str:
    """Return a high-precision, unquantized decimal representation."""
    return format(numerator / denominator, "f")


def compact_number(value: str) -> str:
    return value.replace(",", "").replace(" ", "").replace("\n", "")


def main() -> None:
    source = pd.read_csv(SOURCE, dtype={"股票代码": str})
    pending = source[
        source["股票代码"].isin(VERIFIED)
        & source["复核状态"].str.startswith("年报及业务表已定位", na=False)
    ].copy()
    keys = {(code, year) for code, years in VERIFIED.items() for year in years}
    assert len(keys) == 27
    assert set(zip(pending["股票代码"], pending["年份"].astype(int))) == keys
    assert not pending.duplicated(["股票代码", "年份"]).any()
    assert 2022 not in set(pending["年份"].astype(int))  # v20 has no 2022 rows; never infer them.

    rows = []
    for _, src in pending.sort_values(["股票代码", "年份"]).iterrows():
        code, year = src["股票代码"], int(src["年份"])
        v = VERIFIED[code][year]
        total = Decimal(v["total"])

        # Denominator must be the consolidated income-statement revenue.
        pnl_text = compact_number(str(src["利润表原文摘录"]))
        assert v["total"] in pnl_text, (code, year, "P&L total missing")

        if code == "002299":
            combined = Decimal(v["combined"])
            expanded_n = combined
            expanded_raw = raw_ratio(expanded_n, total)
            expanded_lower = expanded_upper = v["combined"]
            expanded_lower_raw = expanded_upper_raw = expanded_raw
            expanded_bounds_formula = f"下界=上界={v['combined']}（家禽饲养加工合并披露）"
            strict_n = strict_raw = ""
            strict_conclusion = "待核实"
            expanded_conclusion = "是" if expanded_n / total >= Decimal("0.50") else "否"
            boundary = "是" if Decimal("0.30") <= expanded_n / total < Decimal("0.50") else "否"
            assert combined != Decimal(v["combined_cost"]), (code, year, "revenue equals cost guard")
            if v["deep"]:
                assert Decimal(v["deep"]) != Decimal(v["deep_cost"]), (code, year, "deep revenue equals cost")
            direct_amount = ""
            processing_amount = v["combined"]
            deep_amount = v["deep"]
            trade_amount = ""
            strict_business = "家禽养殖（与屠宰初加工合并披露，无法可靠拆分）"
            expanded_business = "家禽饲养加工行业（合并披露）"
            overlap = "合并披露风险：自产养殖与屠宰初加工无法可靠拆分；未估算严格分子"
            formula_s = "待核实：年报未拆分家禽养殖收入"
            formula_e = f"{v['combined']} / {v['total']}"
            deep_note = (
                "食品加工行业属于深加工，已单列但不进入分子"
                if v["deep"] else
                "年报未单列深加工收入，未将其他业务估算为深加工"
            )
            unresolved = (
                f"严格口径待核实；家禽饲养加工收入只用于扩展口径。{deep_note}；"
                "贸易未单列，未估算。"
            )
            reason = f"家禽饲养加工合并收入原始占比{expanded_raw}，扩展口径达标；严格口径不估算。"
        else:
            direct = Decimal(v["direct"])
            processing = Decimal(v["processing"])
            expanded_upper_n = direct + processing
            strict_raw = raw_ratio(direct, total)
            expanded_lower_raw = raw_ratio(direct, total)
            expanded_upper_raw = raw_ratio(expanded_upper_n, total)
            expanded_n = expanded_raw = ""
            expanded_lower = v["direct"]
            expanded_upper = f"{expanded_upper_n:.2f}"
            expanded_bounds_formula = (
                f"下界={v['direct']}（养殖）；上界={v['direct']}+{v['processing']}"
                "（养殖+未拆初加工/深加工的全部水产品加工）"
            )
            strict_n = v["direct"]
            strict_conclusion = "是" if direct / total >= Decimal("0.50") else "否"
            expanded_conclusion = "待核实"
            boundary = "待核实"
            assert direct != Decimal(v["direct_cost"]), (code, year, "direct revenue equals cost")
            assert processing != Decimal(v["processing_cost"]), (code, year, "processing revenue equals cost")
            direct_amount = v["direct"]
            processing_amount = v["processing"]
            deep_amount = ""
            trade_amount = v["trade"]
            strict_business = "水产养殖业" if code == "002069" else "海水养殖"
            expanded_business = f"{strict_business}；水产品加工仅作上下界（初加工与深加工不可拆分）"
            overlap = "加工合并披露风险：水产品加工整类无法拆分初加工与罐头/即食/调理/预制等深加工"
            formula_s = f"{v['direct']} / {v['total']}"
            formula_e = ""
            unresolved = (
                "年报水产品加工整类同时包含初加工与罐头/即食/调理/预制等深加工，无法可靠拆分；"
                "因此扩展正式分子、比例与结论不作估算，以养殖为下界、养殖加全部加工为上界。"
                "贸易收入仅作排除项记录。"
            )
            if code == "002086" and year == 2020:
                unresolved += " 年报10%以上业务表列186,034,010.00元，与营业收入构成表相差0.90元；采用后者186,034,010.90元。"
            reason = (
                f"严格原始占比{strict_raw}，未达50%；扩展下界占比{expanded_lower_raw}、"
                f"上界占比{expanded_upper_raw}，因加工深浅层级不可拆分而待核实；贸易及其他业务未计入。"
            )

        rows.append({
            "股票代码": code,
            "公司全称": src["公司全称"],
            "年份": year,
            "行业分类代码": src["行业分类代码"],
            "行业分类名称": src["行业分类名称"],
            "行业字段状态": "v20当年字段已提供",
            "严格口径涉农业务": strict_business,
            "严格口径涉农收入_元": strict_n,
            "严格口径比例公式": formula_s,
            "严格口径收入占比_原始未四舍五入": strict_raw,
            "扩展口径涉农业务": expanded_business,
            "扩展口径涉农收入_元": f"{expanded_n:.2f}" if isinstance(expanded_n, Decimal) else "",
            "扩展口径比例公式": formula_e,
            "扩展口径收入占比_原始未四舍五入": expanded_raw,
            "扩展口径收入下界_元": expanded_lower,
            "扩展口径收入上界_元": expanded_upper,
            "扩展口径下界占比_原始未四舍五入": expanded_lower_raw,
            "扩展口径上界占比_原始未四舍五入": expanded_upper_raw,
            "扩展口径上下界公式": expanded_bounds_formula,
            "公司营业收入_元": v["total"],
            "公司营业收入公式": "合并利润表营业收入（营业总收入）",
            "自产养殖捕捞收入_元": direct_amount,
            "自产养殖捕捞收入证据PDF页序号": v["page"] if direct_amount else "",
            "初加工或年报加工类收入_元": processing_amount,
            "初加工或年报加工类收入证据PDF页序号": v["page"] if processing_amount else "",
            "深加工收入_元_排除项": deep_amount,
            "深加工收入证据PDF页序号": v["page"] if deep_amount else "",
            "贸易收入_元_排除项": trade_amount,
            "贸易收入证据PDF页序号": v["page"] if trade_amount else "",
            "收入分项证据PDF页序号": v["page"],
            "公司营业收入证据PDF页序号": src["利润表PDF页序号"],
            "收入列口径": "分行业营业收入/主营业务收入列（禁止使用营业成本列）",
            "是否存在分部收入重叠": overlap,
            "严格样本结论": strict_conclusion,
            "扩展样本结论": expanded_conclusion,
            "边界样本结论": boundary,
            "纳入或剔除理由": reason,
            "待核实点": unresolved,
            "2022行业分类提示": "v20无该公司2022公司年；行业分类仍待核实，不得用相邻年份外推",
            "年报链接": src["年报链接"],
            "记录类型": "跨年快速复核第十一批B组",
            "复核状态": "已人工复核（第十一批B组；主表未合并）",
            "复核日期": "2026-08-11",
        })

    out = pd.DataFrame(rows)
    assert len(out) == 27
    assert out["股票代码"].value_counts().to_dict() == {"002069": 9, "002086": 9, "002299": 9}
    assert not out.duplicated(["股票代码", "年份"]).any()
    assert (out["收入列口径"] == "分行业营业收入/主营业务收入列（禁止使用营业成本列）").all()
    assert out["严格样本结论"].value_counts().to_dict() == {"否": 18, "待核实": 9}
    assert out["扩展样本结论"].value_counts().to_dict() == {"待核实": 18, "是": 9}
    assert out["边界样本结论"].value_counts().to_dict() == {"待核实": 18, "否": 9}
    aquatic = out["股票代码"].isin(["002069", "002086"])
    assert out.loc[aquatic, "扩展口径涉农收入_元"].eq("").all()
    assert out.loc[aquatic, "扩展口径收入占比_原始未四舍五入"].eq("").all()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("batch11-B rows=27; strict no=18/pending=9; expanded yes=9/pending=18; boundary no=9/pending=18")


if __name__ == "__main__":
    main()
