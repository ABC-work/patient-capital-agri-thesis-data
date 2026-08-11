#!/usr/bin/env python3
"""Build the standalone final AB review (16 rows) from fixed read-only v32."""
from decimal import Decimal, getcontext
from pathlib import Path
import pandas as pd

getcontext().prec = 60
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v32_跨年快速复核第二十批.csv"
OUTPUT = ROOT / "outputs" / "跨年快速复核最终批_AB组_11家公司.csv"

# total revenue, total cost, confirmed eligible lower revenue, related cost
# evidence, eligible upper revenue, audited other-business revenue/cost.
ELIGIBLE = {
    ("000998", 2022): ("3688805654.84", "2460124720.07", "3142168147.77", "1811184601.15", "3688805654.84", "78686005.95", "57241155.58"),
    ("002041", 2022): ("1325793968.31", "903053189.15", "1278845750.24", "889060401.87", "1325793968.31", "14593329.69", "13992787.28"),
    ("002772", 2015): ("479520220.22", "282059916.07", "479501961.25", "282059916.07", "479520220.22", "18258.97", "0.00"),
    ("002772", 2022): ("1970274412.53", "1468795318.04", "1970274412.53", "1468795318.04", "1970274412.53", "0.00", "0.00"),
    ("300087", 2022): ("3490544779.30", "2553812024.04", "2337984669.03", "1458950786.21", "3409168118.41", "81376660.89", "54061717.83"),
    ("300189", 2022): ("190563212.64", "129488559.77", "173411692.97", "117904758.81", "187847890.84", "8431567.03", "5102435.37"),
    ("300511", 2022): ("2320432033.82", "2072042190.23", "2291146561.14", "2070480874.18", "2320432033.82", "29285472.68", "1561316.05"),
    ("300970", 2022): ("751593906.93", "628935494.08", "751575782.93", "628917370.08", "751593906.93", "18124.00", "18124.00"),
}

# total revenue/cost, excluded main revenue/cost, other revenue/cost.
EXCLUDED = {
    ("002991", 2021): ("1293996746.68", "839819698.85", "1289430842.19", "839753584.72", "4565904.49", "66114.13"),
    ("002991", 2022): ("1450676103.21", "953624262.98", "1443019563.97", "950621301.84", "7656539.24", "3002961.14"),
    ("003000", 2021): ("1111046928.34", "812962164.73", "1099147462.49", "807096489.60", "11899465.85", "5865675.13"),
    ("003000", 2022): ("1462030708.54", "1087387258.92", "1445296962.79", "1080298068.76", "16733745.75", "7089190.16"),
    ("603896", 2021): ("767137327.36", "126372617.19", "759990342.58", "116154065.03", "7146984.78", "10218552.16"),
    ("603896", 2022): ("829071599.84", "129207399.43", "817672535.73", "116033712.53", "11399064.11", "13173686.90"),
    ("605016", 2021): ("653356099.29", "471677493.26", "638522573.15", "458995698.45", "14833526.14", "12681794.81"),
    ("605016", 2022): ("721893633.69", "493337396.13", "696178670.01", "471929098.41", "25714963.68", "21408297.72"),
}

def D(x): return Decimal(x)
def ratio(n, d): return format(n / d, "f")
def result(lo, hi):
    if lo >= D(".5"): return "是"
    if hi < D(".5"): return "否"
    return "待核实"
def boundary(lo, hi):
    if lo >= D(".5") or hi < D(".3"): return "否"
    if lo >= D(".3") and hi < D(".5"): return "是"
    return "待核实"

def main():
    src = pd.read_csv(SOURCE, dtype=str, keep_default_na=False)
    wanted = set(ELIGIBLE) | set(EXCLUDED)
    q = src[src.apply(lambda r: (r["股票代码"], int(r["年份"])) in wanted, axis=1)].sort_values(["股票代码", "年份"])
    assert len(src) == 958 and len(q) == 16 and q["股票代码"].nunique() == 11
    assert not q.duplicated(["股票代码", "年份"]).any()
    rows = []
    for _, s in q.iterrows():
        code, year = s["股票代码"], int(s["年份"])
        other = other_cost = D("0")
        if (code, year) in ELIGIBLE:
            total, total_cost, lo, lo_cost, hi, other, other_cost = map(D, ELIGIBLE[(code, year)])
            sl, sh, el, eh = lo, hi, lo, hi
            if code in {"000998", "002041", "300087", "300189"}:
                business = "互斥披露的农作物种子产品；未拆农业相关项目仅作上界"
                excluded = "租赁及未拆其他业务；非种子项目不进入保守下界"
                reason = "种子属于农业生产核心产品；仅以明确种子产品合计作保守下界，该下界已超过50%，不依赖混合类别。"
                overlap = "种子产品项目互斥相加；不叠加分行业、地区或销售模式"
                evidence = "种子产品合计"
            elif code == "002772":
                business = "工厂化种植并销售的鲜品食用菌"
                excluded = "未识别的其他业务只作上界" if other else "无"
                reason = "年报明确主营金针菇、双孢菇等鲜品食用菌的工厂化种植和销售，属于直接农业。"
                overlap = "采用农业种植业/主营业务单一维度，不与产品、地区重复相加"
                evidence = "食用菌主营业务"
            elif code == "300511":
                business = "工厂化种植销售的金针菇、真姬菇、杏鲍菇及其他鲜品食用菌"
                excluded = "审计其他业务仅进入上界"
                reason = "年报明确公司主营鲜品食用菌的工厂化种植与销售，其他菇种同属香菇、鹿茸菌等鲜品，故食用菌行业收入整体进入下界。"
                overlap = "采用食用菌行业单一互斥口径；不与分产品、地区相加"
                evidence = "食用菌行业收入"
            else:
                business = "工厂化种植销售的金针菇、真姬菇及其他鲜品食用菌"
                excluded = "审计其他业务仅进入上界"
                reason = "年报明确公司专业从事鲜品食用菌工厂化种植与销售，其他产品包括舞茸、虫草花、鹿茸菇等鲜品，故食用菌行业收入整体进入下界。"
                overlap = "采用食用菌行业单一互斥口径；不与分产品、地区相加"
                evidence = "食用菌行业收入"
            strict_business = business
            expanded_business = business + "（同时符合扩展口径）"
            pending = "上下界均超过50%，未拆上界不影响结论。"
            cost_note = f"对应/相关成本{lo_cost:.2f}仅作反向核对；不以成本比例外推收入"
            disclosed_revenue, disclosed_cost = lo, lo_cost
            bound_formula = f"下界={evidence}{lo:.2f}；上界=含未拆相关项目的保守上界{hi:.2f}"
        else:
            total, total_cost, disclosed_revenue, disclosed_cost, other, other_cost = map(D, EXCLUDED[(code, year)])
            sl = el = D("0"); sh = eh = other
            strict_business = "无可确认直接农业收入；审计其他业务只作上界"
            expanded_business = "无可确认农业初加工或农业投入品收入；审计其他业务只作上界"
            if code == "002991":
                excluded = "青豌豆、蚕豆、瓜子仁、综合果仁等休闲食品"
                reason = "炒制、裹粉等休闲食品属于进一步食品加工，不能仅因农产品原料或公司名称纳入。"
            elif code == "003000":
                excluded = "即食鱼制品、豆制品、禽肉制品等休闲食品"
                reason = "即食鱼、豆和禽肉零食属于进一步食品加工，不属于农产品初加工。"
            elif code == "603896":
                excluded = "灵芝、铁皮石斛中药及保健食品等加工产品"
                reason = "虽有自有种植基地，但未单列合并口径种植外销收入；中药饮片/保健产品加工收入排除。"
            else:
                excluded = "益生元、膳食纤维、淀粉糖醇和甜味剂等食品添加剂/配料"
                reason = "食品添加剂及配料不是农业生产投入品，亦非农产品初加工，不能凭功能或原料纳入。"
            overlap = "排除类主营与审计其他业务互斥；不叠加行业、产品、地区或销售模式"
            pending = "审计其他业务性质未拆，只作上界；上界远低于30%，不影响结论。"
            cost_note = f"排除类主营成本{disclosed_cost:.2f}、其他业务成本{other_cost:.2f}仅作反向证据"
            evidence = "排除类主营业务"
            bound_formula = f"下界=0；上界=审计其他业务{other:.2f}"

        srlo, srhi, erlo, erhi = sl/total, sh/total, el/total, eh/total
        assert D("0") <= sl <= sh <= total and D("0") <= el <= eh <= total
        strict_result, expanded_result = result(srlo,srhi), result(erlo,erhi)
        rows.append({
            "股票代码":code,"公司全称":s["公司全称"],"年份":year,"行业分类代码":s["行业分类代码"],"行业分类名称":s["行业分类名称"],
            "严格口径涉农业务":strict_business,"严格口径正式涉农收入_元":f"{sl:.2f}" if strict_result=="是" else "","严格口径收入下界_元":f"{sl:.2f}","严格口径收入上界_元":f"{sh:.2f}",
            "严格口径上下界公式":bound_formula,"严格口径下界占比_原始未四舍五入":ratio(sl,total),"严格口径上界占比_原始未四舍五入":ratio(sh,total),
            "扩展口径涉农业务":expanded_business,"扩展口径正式涉农收入_元":f"{el:.2f}" if expanded_result=="是" else "","扩展口径收入下界_元":f"{el:.2f}","扩展口径收入上界_元":f"{eh:.2f}",
            "扩展口径上下界公式":bound_formula,"扩展口径下界占比_原始未四舍五入":ratio(el,total),"扩展口径上界占比_原始未四舍五入":ratio(eh,total),
            "公司营业收入_元":f"{total:.2f}","公司营业成本_元_反向证据":f"{total_cost:.2f}","公司营业收入公式":"合并利润表营业收入",
            "确认收入或排除类主营收入_元":f"{disclosed_revenue:.2f}","对应或相关成本_元_反向证据":f"{disclosed_cost:.2f}","审计其他业务收入_元_上界":f"{other:.2f}" if other else "","审计其他业务成本_元_反向证据":f"{other_cost:.2f}" if other else "",
            "深加工或排除类别":excluded,"收入成本判别":cost_note,"严格样本结论":strict_result,"扩展样本结论":expanded_result,"边界样本结论":boundary(erlo,erhi),
            "是否存在分部收入重叠":overlap,"纳入或剔除理由":reason,"待核实点":pending+("2022行业分类保持待核实，不插值。" if year==2022 else ""),
            "年报主营业务证据PDF页序号":s["年报主营业务候选PDF页序号"],
            "公司营业收入证据PDF页序号":"134" if (code,year)==("300511",2022) else s["利润表PDF页序号"],
            "年报链接":s["年报链接"],
            "2022行业字段处理":"沿用v32原值；待核实不插值、不复制相邻年份","记录类型":"跨年快速复核最终批AB组（未合并）","复核状态":"官方年报收入/成本、上下界、正式分子及阈值已复核","复核日期":"2026-08-11",
        })
    out=pd.DataFrame(rows)
    assert len(out)==16 and not out.duplicated(["股票代码","年份"]).any()
    assert out.loc[out["年份"].eq(2022),"行业分类代码"].eq("待核实").all()
    assert out["年报链接"].str.startswith("https://static.cninfo.com.cn/").all()
    strict_yes = out["严格样本结论"].eq("是")
    expanded_yes = out["扩展样本结论"].eq("是")
    assert strict_yes.sum() == 8 and expanded_yes.sum() == 8
    assert out.loc[strict_yes, "严格口径正式涉农收入_元"].eq(out.loc[strict_yes, "严格口径收入下界_元"]).all()
    assert out.loc[expanded_yes, "扩展口径正式涉农收入_元"].eq(out.loc[expanded_yes, "扩展口径收入下界_元"]).all()
    assert out.loc[~strict_yes, "严格口径正式涉农收入_元"].eq("").all()
    assert out.loc[~expanded_yes, "扩展口径正式涉农收入_元"].eq("").all()
    check=out.set_index(["股票代码","年份"])
    assert check.loc[("300511",2022),"严格口径正式涉农收入_元"] == "2291146561.14"
    assert check.loc[("300970",2022),"严格口径正式涉农收入_元"] == "751575782.93"
    assert check.loc[("300511",2022),"公司营业收入证据PDF页序号"] == "134"
    OUTPUT.parent.mkdir(parents=True,exist_ok=True); out.to_csv(OUTPUT,index=False,encoding="utf-8-sig")
    print(f"rows={len(out)} companies={out['股票代码'].nunique()} duplicates=0")
    print("strict",out["严格样本结论"].value_counts().to_dict())
    print("expanded",out["扩展样本结论"].value_counts().to_dict())
    print("boundary",out["边界样本结论"].value_counts().to_dict())

if __name__ == "__main__": main()
