#!/usr/bin/env python3
"""Build the fourth manually verified 2023 annual-report business review batch."""

from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
WORKTABLE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v1.csv"
OUTPUT = ROOT / "outputs" / "2023年报主营业务人工复核_第四批13家_v1.csv"

RECORDS = [
 dict(code="600097",total="2014553819.25",sn="海洋捕捞",s="792886976.02",en="海洋捕捞、食品加工",e="1699323763.28",sc="否",ec="是",bc="否",reason="海洋捕捞严格口径39.36%；加入水产品初加工后扩展口径84.35%，渔货贸易未计入。"),
 dict(code="600108",total="4005115417.62",sn="农业种植",s="3113117945.76",en="农业种植",e="3113117945.76",sc="是",ec="是",bc="否",reason="农业分行业收入占77.73%，达到严格门槛。"),
 dict(code="600257",total="1193454619.46",sn="水产品养殖",s="627113773.53",en="水产品养殖",e="627113773.53",sc="是",ec="是",bc="否",reason="农业水产品收入占52.55%，达到严格门槛；白酒、药品等未计入。"),
 dict(code="600354",total="1157762417.27",sn="种子",s="875670812.45",en="种子",e="875670812.45",sc="是",ec="是",bc="否",reason="种子收入占75.63%，达到严格门槛；食品、贸易、棉花未用于放大严格分子。"),
 dict(code="600359",total="548470528.13",sn="粮种、棉种、苗木、鲜奶、育肥牛",s="171969968.87",en="农业分行业（含棉花初加工等）",e="353610347.54",sc="否",ec="是",bc="否",reason="可直接识别的种苗和畜牧收入占31.35%，未达严格门槛；农业板块含初加工后占64.47%，扩展口径达标。"),
 dict(code="600371",total="319298968.77",sn="玉米杂交种",s="300692394.38",en="玉米杂交种、化肥",e="313067804.89",sc="是",ec="是",bc="否",reason="玉米杂交种收入占94.17%，达到严格门槛；加入化肥后扩展口径98.05%。"),
 dict(code="600467",total="1563804509.83",sn="海水养殖、海洋捕捞",s="862527464.45",en="海水养殖、海洋捕捞、食品加工",e="1527451310.30",sc="是",ec="是",bc="否",reason="养殖与捕捞合计占55.16%，达到严格门槛；加入水产品加工后扩展口径97.68%。"),
 dict(code="600540",total="971635206.65",sn="未单独披露直接种植收入",s="0",en="棉花及棉籽初加工",e="811843141.93",sc="否",ec="是",bc="否",reason="年报未单列直接种植收入，严格口径按可核实值为0；棉花、棉籽等农业初加工板块占83.55%，扩展口径达标。"),
 dict(code="600598",total="5044443383.20",sn="农业土地承包及农产品经营",s="3590194105.74",en="农业土地承包及农产品经营",e="3590194105.74",sc="是",ec="是",bc="否",reason="土地承包及农产品经营直接服务农业生产，合计占71.17%，按A05直接相关业务计入严格口径。"),
 dict(code="600975",total="5631944572.42",sn="畜牧业（生猪）",s="3754975937.03",en="畜牧业（生猪）、饲料加工",e="3891680097.83",sc="是",ec="是",bc="否",reason="畜牧业收入占66.67%，达到严格门槛；加入饲料后扩展口径69.10%，批发零售未计入。"),
 dict(code="601118",total="37687250562.10",sn="自产天然橡胶",s=None,en="天然橡胶种植及初加工",e=None,sc="待核实",ec="待核实",bc="待核实",reason="公司同时从事种植、初加工和大规模第三方橡胶贸易；年报仅披露自产销量而未披露对应收入，无法从372.74亿元农业收入中可靠剔除贸易，严格和扩展口径均待核实。"),
 dict(code="603477",total="4040713360.73",sn="畜禽养殖",s="3946820977.02",en="畜禽养殖",e="3946820977.02",sc="是",ec="是",bc="否",reason="畜禽养殖收入占97.68%，达到严格门槛；皮革业务未计入。"),
 dict(code="605296",total="3891278625.20",sn="畜牧养殖",s="2094682094.43",en="畜牧养殖、饲料加工",e="2593072772.24",sc="是",ec="是",bc="否",reason="畜牧养殖收入占53.83%，达到严格门槛；加入饲料后扩展口径66.64%，为避免内部交易重叠未叠加屠宰收入。"),
]

def calc(v, total):
    return None if v is None else (Decimal(v)/Decimal(total)).quantize(Decimal("0.00000001"),rounding=ROUND_HALF_UP)

def main():
    src=pd.read_csv(WORKTABLE,dtype={"股票代码":str})
    src=src[(src["年份"]==2023)&src["股票代码"].isin([r["code"] for r in RECORDS])].set_index("股票代码")
    assert len(src)==13
    rows=[]
    for r in RECORDS:
        x=src.loc[r["code"]]; sr=calc(r["s"],r["total"]); er=calc(r["e"],r["total"])
        if sr is None or er is None:
            assert r["sc"]==r["ec"]==r["bc"]=="待核实"
            eligibility="待核实（收入无法可靠拆分）"
        else:
            assert Decimal(r["s"])<=Decimal(r["e"])<=Decimal(r["total"])
            assert (sr>=Decimal("0.5"))==(r["sc"]=="是")
            assert (er>=Decimal("0.5"))==(r["ec"]=="是")
            assert ((Decimal("0.3")<=er<Decimal("0.5"))==(r["bc"]=="是"))
            eligibility="是（严格样本）" if r["sc"]=="是" else "是（扩展样本）" if r["ec"]=="是" else "否"
        rows.append({"股票代码":r["code"],"公司全称":x["公司全称"],"年份":2023,"公司营业收入_元":r["total"],
          "严格口径涉农业务":r["sn"],"严格口径涉农收入_元":r["s"] or "","严格口径涉农收入占比":"" if sr is None else f"{sr:.8f}",
          "扩展口径涉农业务":r["en"],"扩展口径涉农收入_元":r["e"] or "","扩展口径涉农收入占比":"" if er is None else f"{er:.8f}",
          "是否存在分部收入重叠":"已按同一拆分维度处理；无法拆分时保持待核实","严格样本结论":r["sc"],"扩展样本结论":r["ec"],"边界样本结论":r["bc"],
          "当年曾ST_已核实":"是" if x["当年曾ST_已核实"]=="是" else "否","最终回归样本资格_当前规则":eligibility,"纳入或剔除理由":r["reason"],
          "主营业务证据PDF页序号":int(x["年报主营业务表PDF页序号"]),"营业收入证据PDF页序号":int(x["利润表PDF页序号"]),"年报链接":x["年报链接"],
          "复核状态":"已人工复核（第四批）","复核日期":"2026-08-06"})
    out=pd.DataFrame(rows); assert not out.duplicated(["股票代码","年份"]).any()
    out.to_csv(OUTPUT,index=False,encoding="utf-8-sig")
    print(f"Wrote {len(out)} rows to {OUTPUT}")
    print(out[["股票代码","严格口径涉农收入占比","扩展口径涉农收入占比","严格样本结论","扩展样本结论","最终回归样本资格_当前规则"]].to_string(index=False))

if __name__=="__main__": main()
