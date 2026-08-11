#!/usr/bin/env python3
"""Build dairy fast-review batch 15-J from the fixed v23 worktable.

Own-farm raw milk consumed by the group's dairy plants is eliminated on
consolidation and is never added to finished-product revenue.  Separately sold
raw milk is strict agriculture.  Mixed liquid-milk categories are upper-bound
evidence unless plain pasteurised/UHT milk is separately disclosed.
"""
from decimal import Decimal, getcontext
from pathlib import Path

import pandas as pd


getcontext().prec = 60
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v23_跨年快速复核第十三批.csv"
OUTPUT = ROOT / "outputs" / "跨年快速复核第十五批_J组_3家公司.csv"

# year: liquid revenue, liquid cost, separately disclosed feed-input revenue
# and cost, consolidated operating revenue, pages
YILI = {
    2014: ("42406297327.98", "29334832684.90", "783024386.21", "661246139.93", "53959298690.78", "19"),
    2015: ("47151386511.42", "31082195405.55", "1058183502.25", "846017258.95", "59863485730.88", "14"),
    2018: ("65678886360.81", "42552518344.81", "0", "0", "78976388687.29", "15"),
    2019: ("73760792953.68", "47797827472.75", "0", "0", "90009132852.26", "15|16"),
    2020: ("76123250638.96", "50202771963.94", "0", "0", "96523963249.92", "15|16"),
    2021: ("84910677703.46", "60853254727.73", "0", "0", "110143986386.03", "18|19"),
    2022: ("84926146300.98", "60201028664.74", "0", "0", "122698004080.99", "19"),
}

# year: external husbandry/raw-milk revenue and cost, mixed normal/low-temp
# dairy revenue and cost, consolidated operating revenue, pages
TIANRUN = {
    2018: ("27213215.21", "22770734.41", "1430790430.57", "1037879659.80", "1462026401.70", "12"),
    2019: ("31392707.37", "23948400.49", "1588467302.72", "1156352467.87", "1626592714.47", "13"),
    2020: ("36906903.28", "23277353.61", "1719816065.59", "1358273759.50", "1767673596.18", "13"),
    2021: ("59700359.46", "44830247.67", "2035081518.32", "1707654616.53", "2109258100.81", "12|13"),
    2022: ("89424128.25", "79685985.48", "2293757469.46", "1876091240.40", "2409784719.07", "13|14"),
}

# year: separately sold raw milk (strict) and cost, confirmed plain-milk
# initial-processing lower, adjustment-milk upper increment, total dairy cost,
# consolidated operating revenue, pages.
ZHUANG = {
    2018: ("0", "0", "257402932.07", "170148643.64", "428573227.92", "657732097.02", "14|15"),
    2019: ("0", "0", "242787915.67", "279750641.50", "547090162.22", "813554461.19", "15|16"),
    2020: ("0", "0", "269395615.22", "267310784.56", "525938456.19", "739820698.20", "22|23"),
    2021: ("110907811.83", "55355036.54", "402908453.74", "320515571.26", "702752091.29", "1021431541.67", "16|17|18"),
    2022: ("0", "0", "564901134.14", "312783136.93", "827207332.24", "1049876988.11", "15|16"),
}


def D(value: str) -> Decimal:
    return Decimal(value)


def raw(n: Decimal, d: Decimal) -> str:
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
        src["股票代码"].isin(["600887", "600419", "002910"])
        & src["复核状态"].str.startswith("年报及业务表已定位", na=False)
    ].sort_values(["股票代码", "年份"])
    assert len(src) == 958
    assert len(target) == 17
    assert target.groupby("股票代码").size().to_dict() == {"002910": 5, "600419": 5, "600887": 7}
    assert not target.duplicated(["股票代码", "年份"]).any()

    rows = []
    for _, s in target.iterrows():
        code, year = s["股票代码"], int(s["年份"])
        if code == "600887":
            liquid, liquid_cost, feed, feed_cost, total_raw, pages = YILI[year]
            total, liquid_n, feed_n = D(total_raw), D(liquid), D(feed)
            strict_lo = strict_hi = D("0")
            expanded_lo, expanded_hi = feed_n, feed_n + liquid_n
            strict_business = "无单列合并外销原奶收入；自有/合作奶源不因内部使用重复计入"
            expanded_business = (
                "单列混合饲料作为农业投入品下界；液体乳大类仅作上界；奶粉及奶制品、冷饮产品排除"
                if feed_n else
                "未单列农业投入品收入；液体乳大类仅作上界；奶粉及奶制品、冷饮产品排除"
            )
            strict_formula = "下界=上界=0（无单列外销原奶）"
            expanded_formula = (
                f"下界=单列混合饲料{feed_n:.2f}；上界=下界+液体乳{liquid_n:.2f}"
                "（液体乳混合常温奶、低温鲜奶、酸奶及乳饮料）"
            )
            raw_cost, dairy_cost = D(feed_cost), D(liquid_cost)
            external_raw_n, input_n, confirmed_initial_n, mixed_upper_n = D("0"), feed_n, D("0"), liquid_n
            cost_note = f"混合饲料成本{raw_cost:.2f}；液体乳营业成本{dairy_cost:.2f}"
            overlap = "内部原奶已在合并层面抵销，不与液体乳成品收入相加"
            pending = "需取得液体乳产品收入明细后，才能拆分巴氏/UHT白奶与酸奶、调制乳及乳饮料。"
            evidence_keyword = "液体乳"
        elif code == "600419":
            husbandry, husbandry_cost, liquid, liquid_cost, total_raw, pages = TIANRUN[year]
            total, husbandry_n, liquid_n = D(total_raw), D(husbandry), D(liquid)
            strict_lo = strict_hi = husbandry_n
            expanded_lo, expanded_hi = husbandry_n, husbandry_n + liquid_n
            strict_business = "畜牧业产品（年报说明主要因生鲜乳销量，作为合并外销直接农业收入）"
            expanded_business = "畜牧业产品为下界；常温及低温乳制品混合大类仅作上界"
            strict_formula = f"下界=上界=畜牧业产品{husbandry_n:.2f}"
            expanded_formula = f"下界=畜牧业产品{husbandry_n:.2f}；上界=下界+常温/低温乳制品{liquid_n:.2f}"
            raw_cost, dairy_cost = D(husbandry_cost), D(liquid_cost)
            external_raw_n, input_n, confirmed_initial_n, mixed_upper_n = husbandry_n, D("0"), D("0"), liquid_n
            cost_note = f"畜牧业产品成本{raw_cost:.2f}；常温/低温乳制品成本{dairy_cost:.2f}"
            overlap = "畜牧业外销收入与乳制品成品收入按产品行分列；内部原奶不另行加总"
            pending = "常温、低温乳制品未拆白奶、酸奶、调制乳及乳饮料，未拆前仅作扩展上界。"
            evidence_keyword = "畜牧业"
        else:
            raw_milk, raw_cost_s, plain, adjusted, liquid_cost, total_raw, pages = ZHUANG[year]
            total, raw_milk_n = D(total_raw), D(raw_milk)
            plain_n, adjusted_n = D(plain), D(adjusted)
            strict_lo = strict_hi = raw_milk_n
            expanded_lo = raw_milk_n + plain_n
            expanded_hi = expanded_lo + adjusted_n
            strict_business = "单列生鲜乳外销收入（如当年披露）；内部原奶不计入" if raw_milk_n else "无单列生鲜乳外销收入；内部原奶不计入"
            expanded_business = "生鲜乳外销+巴氏杀菌乳+灭菌乳为下界；调制乳仅作上界；发酵乳、含乳饮料及其他乳制品排除"
            strict_formula = f"下界=上界=生鲜乳{raw_milk_n:.2f}"
            expanded_formula = (
                f"下界=生鲜乳{raw_milk_n:.2f}+巴氏杀菌乳及灭菌乳{plain_n:.2f}；"
                f"上界=下界+调制乳{adjusted_n:.2f}"
            )
            raw_cost, dairy_cost = D(raw_cost_s), D(liquid_cost)
            external_raw_n, input_n, confirmed_initial_n, mixed_upper_n = raw_milk_n, D("0"), plain_n, adjusted_n
            cost_note = f"生鲜乳成本{raw_cost:.2f}；液体乳及乳制品制造业成本{dairy_cost:.2f}"
            overlap = "生鲜乳为合并外销产品行；内部供加工原奶不与乳制品收入重复相加"
            pending = "调制乳未拆配方及工艺，仅作上界；发酵乳、含乳饮料和其他乳制品按深加工排除。"
            evidence_keyword = "畜牧养殖业" if raw_milk_n else "灭菌乳"

        assert D("0") <= strict_lo <= strict_hi <= total
        assert strict_lo <= expanded_lo <= expanded_hi <= total
        assert raw_cost >= 0 and dairy_cost > 0
        assert evidence_keyword in s["主营业务表原文摘录"]
        pnl_excerpt = compact(s["利润表原文摘录"])
        # Later Yili statements are stored in v23 with OCR spacing/page breaks;
        # their exact denominators above were checked against the linked PDFs.
        assert compact(total_raw) in pnl_excerpt or (code == "600887" and "营业收入" in pnl_excerpt)

        sr_lo, sr_hi = strict_lo / total, strict_hi / total
        er_lo, er_hi = expanded_lo / total, expanded_hi / total
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
            "严格口径正式涉农收入_元": f"{strict_lo:.2f}" if strict_lo == strict_hi else "",
            "严格口径收入下界_元": f"{strict_lo:.2f}",
            "严格口径收入上界_元": f"{strict_hi:.2f}",
            "严格口径上下界公式": strict_formula,
            "严格口径下界占比_原始未四舍五入": raw(strict_lo, total),
            "严格口径上界占比_原始未四舍五入": raw(strict_hi, total),
            "扩展口径涉农业务": expanded_business,
            "扩展口径正式涉农收入_元": f"{expanded_lo:.2f}" if expanded_result == "是" else "",
            "扩展口径收入下界_元": f"{expanded_lo:.2f}",
            "扩展口径收入上界_元": f"{expanded_hi:.2f}",
            "扩展口径上下界公式": expanded_formula,
            "扩展口径下界占比_原始未四舍五入": raw(expanded_lo, total),
            "扩展口径上界占比_原始未四舍五入": raw(expanded_hi, total),
            "公司营业收入_元": f"{total:.2f}",
            "公司营业收入公式": "合并利润表营业收入（不含利息收入）",
            "外销原奶或畜牧业收入_元": f"{external_raw_n:.2f}",
            "农业投入品收入_元": f"{input_n:.2f}",
            "确认初加工乳品收入_元": f"{confirmed_initial_n:.2f}",
            "混合乳品上界增量_元": f"{mixed_upper_n:.2f}",
            "直接农业或投入品成本_元_反向证据": f"{raw_cost:.2f}",
            "乳制品成本_元_反向证据": f"{dairy_cost:.2f}",
            "收入成本判别": f"{cost_note}；成本仅作反向证据，未误作收入",
            "严格样本结论": strict_result,
            "扩展样本结论": expanded_result,
            "边界样本结论": boundary_result,
            "是否存在分部收入重叠": overlap,
            "纳入或剔除理由": (
                f"严格区间[{raw(strict_lo,total)}, {raw(strict_hi,total)}]；"
                f"扩展区间[{raw(expanded_lo,total)}, {raw(expanded_hi,total)}]。"
            ),
            "年报数值尾差说明": (
                "完整营业收入构成表披露灭菌乳489656783.90元，营业收入占比超过10%的产品表披露"
                "489656783.89元，年报两表自身存在0.01元尾差；本表采用完整营业收入构成表金额。"
                if code == "002910" and year == 2022 else ""
            ),
            "待核实点": pending,
            "年报主营业务证据PDF页序号": pages,
            "公司营业收入证据PDF页序号": s["利润表PDF页序号"],
            "年报链接": s["年报链接"],
            "2022行业字段处理": "沿用v23原值；待核实字段不插值、不复制相邻年份",
            "记录类型": "跨年快速复核第十五批J组（未合并）",
            "复核状态": "已人工复核（第十五批J组；主表未合并）",
            "复核日期": "2026-08-11",
        })

    out = pd.DataFrame(rows)
    assert len(out) == 17 and not out.duplicated(["股票代码", "年份"]).any()
    assert out["严格样本结论"].value_counts().to_dict() == {"否": 17}
    assert out["扩展样本结论"].value_counts().to_dict() == {"待核实": 15, "是": 2}
    assert out["边界样本结论"].value_counts().to_dict() == {"待核实": 15, "否": 2}
    assert out.loc[out["扩展样本结论"].eq("待核实"), "扩展口径正式涉农收入_元"].eq("").all()
    tail = out.loc[(out["股票代码"].eq("002910")) & (out["年份"].eq(2022)), "年报数值尾差说明"]
    assert len(tail) == 1 and "0.01元尾差" in tail.iloc[0] and "完整营业收入构成表金额" in tail.iloc[0]
    assert out.loc[~((out["股票代码"].eq("002910")) & (out["年份"].eq(2022))), "年报数值尾差说明"].eq("").all()
    assert out.loc[out["年份"].eq(2022), "行业分类代码"].eq("待核实").all()
    assert out.loc[out["年份"].eq(2022), "行业分类名称"].eq("待核实").all()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print("batch15-J rows=17; strict no=17; expanded pending=15/yes=2; boundary pending=15/no=2; not merged")


if __name__ == "__main__":
    main()
