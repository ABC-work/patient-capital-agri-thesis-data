#!/usr/bin/env python3
"""Merge verified 2023 batch 04 into v4 and write the completed industry-entry v5."""
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"outputs"/"涉农候选公司年份_年报主营业务复核工作表_v4.csv"
BATCH=ROOT/"outputs"/"2023年报主营业务人工复核_第四批13家_v1.csv"
OUTPUT=ROOT/"outputs"/"涉农候选公司年份_年报主营业务复核工作表_v5.csv"

def main():
    table=pd.read_csv(SOURCE,dtype={"股票代码":str}); batch=pd.read_csv(BATCH,dtype={"股票代码":str}).set_index(["股票代码","年份"])
    text_cols=["涉农业务名称","是否存在分部收入重叠","严格样本结论","扩展样本结论","边界样本结论","纳入或剔除理由","复核状态","口径提示"]
    table[text_cols]=table[text_cols].astype("object"); updated=0
    for idx,row in table.iterrows():
        key=(row["股票代码"],int(row["年份"]))
        if key not in batch.index: continue
        item=batch.loc[key]
        if item["严格样本结论"]=="是": prefix="严格"
        elif item["扩展样本结论"]=="是": prefix="扩展"
        else: prefix="严格"
        table.at[idx,"涉农业务名称"]=item[f"{prefix}口径涉农业务"]
        table.at[idx,"涉农业务营业收入"]=item[f"{prefix}口径涉农收入_元"]
        table.at[idx,"公司营业收入"]=item["公司营业收入_元"]
        table.at[idx,"涉农收入占比"]=item[f"{prefix}口径涉农收入占比"]
        for col in ["是否存在分部收入重叠","严格样本结论","扩展样本结论","边界样本结论","纳入或剔除理由","复核状态"]: table.at[idx,col]=item[col]
        ss="待核实" if pd.isna(item["严格口径涉农收入占比"]) else item["严格口径涉农收入占比"]
        es="待核实" if pd.isna(item["扩展口径涉农收入占比"]) else item["扩展口径涉农收入占比"]
        table.at[idx,"口径提示"]=f"严格口径占比={ss}；扩展口径占比={es}；两套分子详见2023年报主营业务人工复核_第四批13家_v1.csv"
        updated+=1
    assert updated==13 and len(table)==958 and not table.duplicated(["股票代码","年份"]).any()
    assert table["复核状态"].str.startswith("已人工复核",na=False).sum()==41
    assert table[(table["年份"]==2023)&(table["行业入口候选"]==1)]["复核状态"].str.startswith("已人工复核",na=False).all()
    table.to_csv(OUTPUT,index=False,encoding="utf-8-sig")
    print(f"Wrote {len(table)} rows to {OUTPUT}; all 41 2023 industry-entry records reviewed; v1-v4 untouched.")

if __name__=="__main__": main()
