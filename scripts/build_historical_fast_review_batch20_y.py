#!/usr/bin/env python3
"""Build standalone batch 20-Y from fixed v31 (exactly 20 company-years).

Rules: fresh self-grown mushrooms are strict; dehydrated self-grown mushrooms
and fruit/vegetable sorting, grading, pre-cooling and packing are expanded
primary processing. Pharmaceuticals, condiments, cheese and other deeply
processed foods are excluded. Unsplit other business and mixed disclosures are
upper bounds only. Costs are reverse evidence, never allocation keys.
"""
from decimal import Decimal, getcontext
from pathlib import Path

import pandas as pd

getcontext().prec = 60
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v31_跨年快速复核第十九批.csv"
OUTPUT = ROOT / "outputs" / "跨年快速复核第二十批_Y组_6家公司.csv"

# total, direct/primary eligible revenue, related cost, mixed/other revenue, cost
DATA = {
    "300143": {
        2013: ("254837544.23", "233908854.82", "218947205.75", "39339.98", "19993.03"),
        2014: ("307842534.93", "307172426.53", "263650980.76", "307358.66", "16537.70"),
        2015: ("280137234.37", "279891189.94", "192514923.51", "213377.66", "226566.87"),
        2016: ("432454072.41", "242792614.12", "190057905.71", "114241.96", "56757.77"),
    },
    "300158": {
        2019: ("4398753603.80", "239305543.67", "229679276.76", "21983426.35", "13609028.60"),
        2020: ("4847833214.47", "417994714.83", "458977732.20", "69713674.25", "78544059.87"),
        2021: ("5093776334.20", "586281432.12", "830303278.55", "66095540.34", "22309755.68"),
        2022: ("3728555341.19", "457163977.22", "693605969.75", "63980572.10", "36568205.23"),
    },
    "300908": {
        2020: ("726669232.06", "724211065.50", "425995261.03", "2458166.56", "752865.07"),
        2021: ("806241308.44", "800212446.50", "488518516.74", "6028861.94", "3479605.08"),
        2022: ("881654879.35", "879101647.35", "556255109.17", "2553232.00", "214243.89"),
    },
    "600285": {
        2020: ("2331577446.95", "2328138065.05", "537146634.29", "3439381.90", "1256149.55"),
        2021: ("2693510918.29", "2690027819.01", "692240882.62", "3483099.28", "752460.04"),
        2022: ("3001862213.98", "2998418581.89", "831562320.69", "3443632.09", "551493.28"),
    },
    "600882": {
        2020: ("2846807171.16", "2845144078.47", "1822773679.70", "1663092.69", "1726791.38"),
        2021: ("4478305561.69", "4468872906.63", "2764594677.97", "9432655.06", "2678269.41"),
        2022: ("4829537951.87", "4817598944.98", "3175155788.45", "11939006.89", "5008494.71"),
    },
    "603336": {
        2020: ("964036408.96", "962731777.56", "842938735.80", "1304631.40", "862074.83"),
        2021: ("974260744.47", "943037467.03", "842341130.45", "24513488.48", "21680101.29"),
        2022: ("1132815675.94", "975174851.37", "885435622.96", "7994573.56", "6502844.83"),
    },
}


def D(x): return Decimal(x)
def ratio(n, d): return format(n / d, "f")


def threshold(lo, hi):
    if lo / D("1") >= D("0.5"): return "是"
    if hi < D("0.5"): return "否"
    return "待核实"


def boundary(lo, hi):
    if lo >= D("0.5") or hi < D("0.3"): return "否"
    if lo >= D("0.3") and hi < D("0.5"): return "是"
    return "待核实"


def profit_page(code, year, original):
    """Keep the consolidated income-statement page, not audit/summary pages."""
    fixes = {
        ("300143", 2015): "63",
        ("603336", 2020): "77",
        ("603336", 2021): "76",
    }
    return fixes.get((code, year), original)


def main():
    src = pd.read_csv(SOURCE, dtype=str, keep_default_na=False)
    wanted = {(c, str(y)) for c, years in DATA.items() for y in years}
    selected = src[src.apply(lambda r: (r["股票代码"], r["年份"]) in wanted, axis=1)].copy()
    assert len(src) == 958 and len(selected) == 20 and not selected.duplicated(["股票代码", "年份"]).any()
    assert selected.groupby("股票代码").size().to_dict() == {"300143": 4, "300158": 4, "300908": 3, "600285": 3, "600882": 3, "603336": 3}
    rows = []
    for _, s in selected.sort_values(["股票代码", "年份"]).iterrows():
        c, y = s["股票代码"], int(s["年份"])
        total, disclosed, disclosed_cost, other, other_cost = map(D, DATA[c][y])
        if c == "300143":
            if y == 2015:
                sl, sh, el, eh = D("0"), disclosed + other, disclosed, disclosed + other
                sb = "自产鲜菇与自产鲜菇脱水干菇未拆，连同其他业务只作严格上界"
                eb = "自产食用菌鲜品及脱水初加工品（剔除经销商品），其他业务只作上界"
                pending = "鲜菇与自产鲜菇脱水形成的干菇收入未拆，严格上下界跨越50%。"
            else:
                sl = el = disclosed; sh = eh = disclosed + other
                sb = "工厂化自产鲜品食用菌（剔除经销菌类商品），其他业务只作上界"
                eb = "自产食用菌鲜品，其他业务只作扩展上界"
                pending = "审计其他业务未拆，只作上界。"
            excluded = "经销商品；2016年医疗设备及医疗服务"
            reason = "自产鲜品食用菌属于直接农业；2015年干菇为自产鲜菇脱水初加工，仅进入扩展下界；经销商品及医疗业务排除。"
            overlap = "产品项目互斥；不叠加行业、地区维度，审计其他业务仅作上界"
            costnote = f"食用菌相关成本{disclosed_cost:.2f}仅反向核对；2015混合成本不用于拆分鲜菇/干菇"
        elif c == "300158":
            sl = el = D("0"); sh = eh = disclosed + other
            sb = "药材种植、收购、产地加工及销售混合披露，只作严格上界"
            eb = "药材种植与产地初加工混合深加工/流通，只作扩展上界"
            excluded = "中成药、化学药等药品深加工；未拆药材流通和深加工"
            reason = "“药材种植行业”未拆自产种植、外购药材、初加工与深加工/销售，不能整体认定；即使连同其他业务，上界仍低于30%。"
            pending = "药材种植行业内部收入性质未拆；上下界均不改变剔除结论。"
            overlap = "药材种植为行业/分部口径，其他业务为互斥审计层级；不与医药产品维度叠加"
            costnote = f"中药材种植报告分部成本{disclosed_cost:.2f}含分部内部交易影响，仅作反向证据"
        elif c in ("300908", "600285", "600882"):
            sl = el = D("0"); sh = eh = other
            if c == "300908":
                excluded = "调味食品、调味配料等食品深加工"
                reason = "香菇酱、辣椒酱及调味配料均为食品深加工，不能因原料涉农纳入；审计其他业务只作上界。"
            elif c == "600285":
                excluded = "贴膏剂、片剂、胶囊剂、软膏剂等药品制造"
                reason = "主营为药品研发制造销售，采购中药材不形成农业生产收入；审计其他业务只作上界。"
            else:
                excluded = "奶酪、液态奶加工及乳制品贸易"
                reason = "奶酪为深加工，乳制品贸易不属于农业生产或初加工；液态奶未拆基础乳与调制/发酵品，亦无自产原奶外销收入。"
            sb = "未披露可确认的直接农业收入；审计其他业务只作上界"
            eb = "未披露可确认的农业初加工收入；审计其他业务只作上界"
            pending = "审计其他业务性质未拆，但上界远低于30%。"
            overlap = "主营业务明确排除；其他业务为互斥审计层级，不叠加行业、产品、地区或销售模式"
            costnote = f"排除类主营成本{disclosed_cost:.2f}及其他业务成本{other_cost:.2f}仅作反向证据"
        else:
            sl = D("0"); sh = other; el = disclosed; eh = disclosed + other
            sb = "公司+基地+农户模式下未单列公司自营种植收入；其他业务只作严格上界"
            eb = "水果蔬菜采后收购、预冷、分级、加工包装等初加工服务收入；其他业务只作上界"
            excluded = "2021粮油/食品；2022食用油、食品、冻肉及供应链管理"
            reason = "果蔬主要向基地/农户采购，未证明公司直接种植外销；采后预冷、预选分级和包装属于扩展口径初加工，深加工和冻肉贸易排除。"
            pending = "其他业务未拆；严格口径无单列自营种植收入。"
            overlap = "水果、蔬菜为互斥产品项目；不叠加果蔬服务行业、地区或销售模式，其他业务仅作上界"
            costnote = f"果蔬产品成本{disclosed_cost:.2f}仅作反向核对，不以毛利率估算收入"

        srlo, srhi, erlo, erhi = sl/total, sh/total, el/total, eh/total
        assert D("0") <= sl <= sh <= total and D("0") <= el <= eh <= total
        rows.append({
            "股票代码": c, "公司全称": s["公司全称"], "年份": y,
            "行业分类代码": s["行业分类代码"], "行业分类名称": s["行业分类名称"],
            "严格口径涉农业务": sb, "严格口径正式涉农收入_元": f"{sl:.2f}" if sl == sh else "",
            "严格口径收入下界_元": f"{sl:.2f}", "严格口径收入上界_元": f"{sh:.2f}",
            "严格口径上下界公式": f"下界={sl:.2f}；上界={sh:.2f}",
            "严格口径下界占比_原始未四舍五入": ratio(sl,total), "严格口径上界占比_原始未四舍五入": ratio(sh,total),
            # A confirmed, non-overlapping lower bound is the formal numerator
            # once that lower bound itself reaches 50%; an unresolved generic
            # other-business upper bound does not erase the confirmed amount.
            "扩展口径涉农业务": eb,
            "扩展口径正式涉农收入_元": f"{el:.2f}" if erlo >= D("0.5") else "",
            "扩展口径收入下界_元": f"{el:.2f}", "扩展口径收入上界_元": f"{eh:.2f}",
            "扩展口径上下界公式": f"下界={el:.2f}；上界={eh:.2f}",
            "扩展口径下界占比_原始未四舍五入": ratio(el,total), "扩展口径上界占比_原始未四舍五入": ratio(eh,total),
            "公司营业收入_元": f"{total:.2f}", "公司营业收入公式": "合并利润表营业收入",
            "主营/混合/初加工披露收入_元": f"{disclosed:.2f}", "对应成本_元_反向证据": f"{disclosed_cost:.2f}",
            "审计其他业务收入_元_上界": f"{other:.2f}", "审计其他业务成本_元_反向证据": f"{other_cost:.2f}",
            "深加工或排除类别": excluded, "收入成本判别": costnote,
            "严格样本结论": threshold(srlo,srhi), "扩展样本结论": threshold(erlo,erhi), "边界样本结论": boundary(erlo,erhi),
            "是否存在分部收入重叠": overlap, "纳入或剔除理由": reason,
            "待核实点": pending + ("2022行业分类字段保持待核实，不插值。" if y == 2022 else ""),
            "年报主营业务证据PDF页序号": s["年报主营业务候选PDF页序号"],
            "公司营业收入证据PDF页序号": profit_page(c, y, s["利润表PDF页序号"]),
            "年报链接": s["年报链接"], "2022行业字段处理": "沿用v31原值；待核实不插值、不复制相邻年份",
            "记录类型": "跨年快速复核第二十批Y组（未合并）", "复核状态": "年报收入/成本、上下界、30%/50%阈值与页码链接已复核",
        })
    out = pd.DataFrame(rows)
    assert len(out) == 20 and not out.duplicated(["股票代码", "年份"]).any()
    assert set(out.loc[out["年份"] == 2022, "行业分类代码"]) == {"待核实"}
    assert out["严格样本结论"].value_counts().to_dict() == {"否": 16, "是": 3, "待核实": 1}
    assert out["扩展样本结论"].value_counts().to_dict() == {"否": 13, "是": 7}
    assert out["边界样本结论"].value_counts().to_dict() == {"否": 20}
    expanded_yes = out[out["扩展样本结论"].eq("是")]
    assert len(expanded_yes) == 7
    assert expanded_yes["扩展口径正式涉农收入_元"].ne("").all()
    assert (expanded_yes["扩展口径正式涉农收入_元"] == expanded_yes["扩展口径收入下界_元"]).all()
    assert out[out["扩展样本结论"].ne("是")]["扩展口径正式涉农收入_元"].eq("").all()
    page_check = out.set_index(["股票代码", "年份"])["公司营业收入证据PDF页序号"]
    assert page_check.loc[("300143", 2015)] == "63"
    assert page_check.loc[("603336", 2020)] == "77"
    assert page_check.loc[("603336", 2021)] == "76"
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print(f"wrote {len(out)} rows -> {OUTPUT}")
    print(out.groupby(["严格样本结论", "扩展样本结论", "边界样本结论"]).size().to_string())


if __name__ == "__main__": main()
