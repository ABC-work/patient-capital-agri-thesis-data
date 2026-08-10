#!/usr/bin/env python3
"""Merge the final 45 leading-only reviews into v9 and write completed v10."""
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'outputs'/'涉农候选公司年份_年报主营业务复核工作表_v9.csv'
BATCH=ROOT/'outputs'/'2023龙头企业独有候选_年报复核剩余45家_v1.csv'
OUTPUT=ROOT/'outputs'/'涉农候选公司年份_年报主营业务复核工作表_v10_2023入口复核完成.csv'

def main():
    t=pd.read_csv(SOURCE,dtype={'股票代码':str}); b=pd.read_csv(BATCH,dtype={'股票代码':str}).set_index(['股票代码','年份'])
    cols=['涉农业务名称','是否存在分部收入重叠','严格样本结论','扩展样本结论','边界样本结论','纳入或剔除理由','复核状态','口径提示']; t[cols]=t[cols].astype('object'); n=0
    for i,r in t.iterrows():
        k=(r['股票代码'],int(r['年份']))
        if k not in b.index: continue
        x=b.loc[k]; p='严格' if x['严格样本结论']=='是' else '扩展'
        t.at[i,'涉农业务名称']=x[f'{p}口径涉农业务']; t.at[i,'涉农业务营业收入']=x[f'{p}口径涉农收入_元']; t.at[i,'公司营业收入']=x['公司营业收入_元']; t.at[i,'涉农收入占比']=x[f'{p}口径涉农收入占比']
        for c in ['是否存在分部收入重叠','严格样本结论','扩展样本结论','边界样本结论','纳入或剔除理由','复核状态']: t.at[i,c]=x[c]
        er='待核实' if pd.isna(x['扩展口径涉农收入占比']) else x['扩展口径涉农收入占比']; t.at[i,'口径提示']=f"严格口径占比={x['严格口径涉农收入占比']}；扩展口径占比={er}；详见2023龙头企业独有候选_年报复核剩余45家_v1.csv"; n+=1
    assert n==45 and len(t)==958 and not t.duplicated(['股票代码','年份']).any()
    assert t['复核状态'].str.startswith('已人工复核',na=False).sum()==134
    assert t[(t.年份==2023)&~t['复核状态'].str.startswith('已人工复核',na=False)].empty
    t.to_csv(OUTPUT,index=False,encoding='utf-8-sig'); print('v10 rows=958; 2023 entry reviewed=134/134; leading-only reviewed=93/93')

if __name__=='__main__': main()
