#!/usr/bin/env python3
"""Merge leading-only batch 01 into v5 and write v6."""
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"outputs"/"涉农候选公司年份_年报主营业务复核工作表_v5.csv"
BATCH=ROOT/"outputs"/"2023龙头企业独有候选_年报复核第一批12家_v1.csv"
OUTPUT=ROOT/"outputs"/"涉农候选公司年份_年报主营业务复核工作表_v6.csv"
def main():
    table=pd.read_csv(SOURCE,dtype={"股票代码":str}); batch=pd.read_csv(BATCH,dtype={"股票代码":str}).set_index(["股票代码","年份"])
    tc=["涉农业务名称","是否存在分部收入重叠","严格样本结论","扩展样本结论","边界样本结论","纳入或剔除理由","复核状态","口径提示"]; table[tc]=table[tc].astype("object"); n=0
    for i,row in table.iterrows():
        key=(row["股票代码"],int(row["年份"]))
        if key not in batch.index: continue
        x=batch.loc[key]; p="严格" if x["严格样本结论"]=="是" else "扩展"
        table.at[i,"涉农业务名称"]=x[f"{p}口径涉农业务"]; table.at[i,"涉农业务营业收入"]=x[f"{p}口径涉农收入_元"]
        table.at[i,"公司营业收入"]=x["公司营业收入_元"]; table.at[i,"涉农收入占比"]=x[f"{p}口径涉农收入占比"]
        for c in ["是否存在分部收入重叠","严格样本结论","扩展样本结论","边界样本结论","纳入或剔除理由","复核状态"]: table.at[i,c]=x[c]
        table.at[i,"口径提示"]=f"严格口径占比={x['严格口径涉农收入占比']}；扩展口径占比={x['扩展口径涉农收入占比']}；详见2023龙头企业独有候选_年报复核第一批12家_v1.csv"; n+=1
    assert n==12 and len(table)==958 and not table.duplicated(["股票代码","年份"]).any()
    assert table["复核状态"].str.startswith("已人工复核",na=False).sum()==53
    table.to_csv(OUTPUT,index=False,encoding="utf-8-sig"); print("v6 rows=958; cumulative reviewed=53; leading-only reviewed=12/93")
if __name__=="__main__": main()
