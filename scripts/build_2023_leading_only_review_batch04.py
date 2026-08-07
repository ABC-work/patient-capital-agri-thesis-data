#!/usr/bin/env python3
"""Build fourth verified batch of 2023 leading-firm-only candidates."""
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
WORKTABLE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v8.csv"
OUTPUT = ROOT / "outputs" / "2023龙头企业独有候选_年报复核第四批12家_v1.csv"

# s/e are strict/expanded qualifying revenues.  They are taken only from one
# disclosure dimension; exclusions are deliberately conservative.
R = [
    dict(c="002991", t="1847559891.15", sn="无", s="0", en="休闲食品不属于扩展范围", e="0", sc="否", ec="否", bc="否", why="主营青豌豆、瓜子仁、蚕豆和综合果仁等休闲食品，属于进一步食品加工，按既定规则排除。"),
    dict(c="003000", t="2065206610.45", sn="无", s="0", en="休闲鱼制品、豆制品和禽肉制品不属于初加工", e="0", sc="否", ec="否", bc="否", why="主营即食鱼制品、豆制品和禽肉制品等休闲食品，属于进一步食品加工，按既定规则排除。"),
    dict(c="300094", t="4908864488.27", sn="无单列直接养殖收入", s="0", en="可确认的饲料；水产食品中初加工收入未单列", e="263043181.64", sc="否", ec="待核实", bc="待核实", why="饲料收入占5.36%；水产食品合并了初加工、精深加工、预制菜和全球海产精选，无法可靠拆分扩展分子，扩展及边界结论均待核实。"),
    dict(c="300119", t="2248962053.98", sn="无直接农业收入", s="0", en="兽用生物制品、兽用制剂及原料药", e="2183106384.37", sc="否", ec="是", bc="否", why="兽用生物制品、兽用制剂及原料药按同一分行业维度合计占97.07%，属于农业投入品，进入扩展样本。"),
    dict(c="300138", t="6871515007.68", sn="无直接农业收入", s="0", en="棉籽类初加工业务", e="3548421149.37", sc="否", ec="是", bc="否", why="只计棉籽类初加工业务，占51.64%；天然色素、香辛料、营养及药用类产品和其他业务未计入。"),
    dict(c="300158", t="3626016132.88", sn="药材种植、销售（披露合并口径上限）", s="696738222.38", en="药材种植、销售（披露合并口径上限）", e="696738222.38", sc="否", ec="否", bc="否", why="即使将药材种植、销售合并收入全部作为涉农收入，上限也仅占19.21%；医药生产销售不计入，低于30%。"),
    dict(c="300783", t="7114575915.74", sn="无", s="0", en="休闲食品不属于扩展范围", e="0", sc="否", ec="否", bc="否", why="坚果、烘焙、肉制品和果干均按休闲食品口径排除，不能因原料来自农产品而纳入。"),
    dict(c="300871", t="1019758798.36", sn="无直接农业收入", s="0", en="兽用原料药及制剂", e="942217427.49", sc="否", ec="是", bc="否", why="兽用原料药及制剂收入占92.40%，属于农业投入品，进入扩展样本。"),
    dict(c="300898", t="946938152.54", sn="无", s="0", en="浓缩乳制品、椰品及乳品贸易不按原奶初加工计入", e="0", sc="否", ec="否", bc="否", why="主营浓缩乳制品、椰品及乳品贸易；按既定窄口径不属于可计的原奶初加工，且未披露直接农业收入，予以剔除。"),
    dict(c="300908", t="994249429.79", sn="无", s="0", en="调味食品及调味配料不属于扩展范围", e="0", sc="否", ec="否", bc="否", why="主营调味食品和调味配料，属于进一步食品加工；普通调味品按既定规则排除。"),
    dict(c="301116", t="21888226740.90", sn="种禽", s="1257233120.95", en="屠宰、饲料和种禽", e="20579511091.33", sc="否", ec="是", bc="否", why="种禽收入仅占5.74%；屠宰初加工、饲料和种禽按同一分行业维度合计占94.02%，进入扩展样本。"),
    dict(c="301498", t="4326963076.35", sn="无", s="0", en="宠物食品不属于农业生产投入品", e="0", sc="否", ec="否", bc="否", why="主营宠物主粮和零食；宠物饲料不作为农业生产投入品，按普通宠物食品制造排除。"),
]


def q(v, t):
    if v == "":
        return ""
    return (Decimal(v) / Decimal(t)).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)


def page(v):
    return str(int(v)) if isinstance(v, float) and v.is_integer() else str(v)


def main():
    d = pd.read_csv(WORKTABLE, dtype={"股票代码": str})
    d = d[(d.年份 == 2023) & d.股票代码.isin([r["c"] for r in R])].set_index("股票代码")
    assert len(d) == 12
    rows = []
    for r in R:
        x = d.loc[r["c"]]
        sr, er = q(r["s"], r["t"]), q(r["e"], r["t"])
        if sr != "" and r["sc"] in {"是", "否"}:
            assert (sr >= Decimal("0.5")) == (r["sc"] == "是")
        if r["ec"] in {"是", "否"}:
            assert (er >= Decimal("0.5")) == (r["ec"] == "是")
        if r["bc"] in {"是", "否"}:
            assert (Decimal("0.3") <= er < Decimal("0.5")) == (r["bc"] == "是")
        eligibility = (
            "是（严格样本）" if r["sc"] == "是" else
            "是（扩展样本）" if r["ec"] == "是" else
            "否（仅边界稳健性）" if r["bc"] == "是" else
            "待核实" if "待核实" in {r["sc"], r["ec"], r["bc"]} else
            "否（低于30%或不属于扩展范围）"
        )
        rows.append({
            "股票代码": r["c"], "公司全称": x["公司全称"], "年份": int(x["年份"]),
            "公司营业收入_元": r["t"], "严格口径涉农业务": r["sn"],
            "严格口径涉农收入_元": r["s"],
            "严格口径涉农收入占比": "" if sr == "" else f"{sr:.8f}",
            "扩展口径涉农业务": r["en"], "扩展口径涉农收入_元": r["e"],
            "扩展口径涉农收入占比": f"{er:.8f}",
            "是否存在分部收入重叠": r.get("ov", "否（同一披露维度；不符合范围的业务未计入）"),
            "严格样本结论": r["sc"], "扩展样本结论": r["ec"], "边界样本结论": r["bc"],
            "当年曾ST_已核实": "是" if x["当年曾ST_已核实"] == "是" else "否",
            "最终回归样本资格_当前规则": eligibility, "纳入或剔除理由": r["why"],
            "主营业务证据PDF页序号": r.get("bp", page(x["年报主营业务表PDF页序号"])),
            "营业收入证据PDF页序号": page(x["利润表PDF页序号"]), "年报链接": x["年报链接"],
            "复核状态": "已人工复核（龙头独有第四批）", "复核日期": "2026-08-07",
        })
    out = pd.DataFrame(rows)
    assert not out.duplicated(["股票代码", "年份"]).any()
    out.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print(out[["股票代码", "年份", "严格口径涉农收入占比", "扩展口径涉农收入占比", "严格样本结论", "扩展样本结论", "边界样本结论"]].to_string(index=False))


if __name__ == "__main__":
    main()
