#!/usr/bin/env python3
"""Build an explainable cross-year review triage for verified industry candidates.

This script only routes records for review. It never copies a sample conclusion or
revenue value from an adjacent year.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v10_2023入口复核完成.csv"
MATRIX = ROOT / "outputs" / "行业候选公司跨年业务变更矩阵_v1.csv"
SUMMARY = ROOT / "outputs" / "行业候选公司跨年复核分流汇总_v1.csv"
FAST_QUEUE = ROOT / "outputs" / "行业候选公司跨年快速核对清单_v1.csv"
DEEP_QUEUE = ROOT / "outputs" / "行业候选公司跨年深度复核清单_v1.csv"

CATEGORY_TERMS = {
    "种子": ["种子", "种业"],
    "种植": ["种植", "农作物"],
    "林业": ["林业", "木材", "苗木", "活立木"],
    "生猪": ["生猪", "商品猪", "种猪", "仔猪"],
    "家禽": ["肉鸡", "鸡肉", "鸡苗", "鸭苗", "禽业", "家禽"],
    "畜牧其他": ["畜牧", "肉牛", "羊肉", "牛肉"],
    "水产": ["水产", "海水养殖", "捕捞", "渔业", "鱼苗", "虾"],
    "饲料": ["饲料", "预混料", "浓缩料"],
    "兽药": ["兽药", "动物保健", "动保产品", "疫苗"],
    "农药": ["农药", "农化"],
    "化肥": ["化肥", "复合肥"],
    "粮油初加工": ["大米", "面粉", "食用油", "粮食", "皮棉", "棉籽"],
    "果蔬初加工": ["果汁", "果蔬", "水果", "蔬菜"],
    "乳业": ["乳制品", "液态奶", "牛奶", "原奶", "鲜奶"],
    "屠宰肉制品": ["屠宰", "肉制品"],
    "食品深加工": ["休闲食品", "调味品", "预制菜", "饮料", "酒类"],
    "贸易零售": ["贸易", "零售", "商业"],
    "医药": ["医药", "药品"],
    "地产园林": ["房地产", "园林", "工程"],
}

STOP_PHRASES = [
    "公司主营业务数据统计口径在报告期发生调整的情况下",
    "公司最近年按报告期末口径调整后的主营业务数据",
    "占公司营业收入或营业利润以上的行业产品地区销售模式的情况",
    "相关数据同比发生变动以上的原因说明",
    "适用不适用", "单位元", "年度报告全文", "营业收入比上年同期增减",
    "营业成本比上年同期增减", "毛利率比上年同期增减", "营业收入构成",
    "收入与成本", "分行业", "分产品", "分地区", "分销售模式", "同比增减",
    "营业收入", "营业成本", "毛利率", "金额", "占比", "比重",
]


def categories(text: str) -> set[str]:
    value = str(text)
    return {
        category for category, terms in CATEGORY_TERMS.items()
        if any(term in value for term in terms)
    }


def normalized(text: str) -> str:
    value = re.sub(r"\[PDF页\d+\]", "", str(text))
    value = re.sub(r"[A-Za-z0-9０-９\s\W_]+", "", value)
    for phrase in STOP_PHRASES:
        value = value.replace(phrase, "")
    return value


def trigram_cosine(left: str, right: str) -> float:
    def grams(value: str) -> Counter[str]:
        clean = normalized(value)
        return Counter(clean[index:index + 3] for index in range(len(clean) - 2))

    a, b = grams(left), grams(right)
    denominator = math.sqrt(sum(v * v for v in a.values()) * sum(v * v for v in b.values()))
    if not denominator:
        return 0.0
    return sum(v * b.get(key, 0) for key, v in a.items()) / denominator


def checked_status(text: str, phrase: str) -> str:
    value = re.sub(r"\s+", "", str(text))
    position = value.find(phrase)
    if position < 0:
        return "未定位"
    window = value[position:position + 180]
    yes = window.find("√适用")
    no = window.find("√不适用")
    if yes >= 0 and (no < 0 or yes < no):
        return "适用"
    if no >= 0:
        return "不适用"
    return "勾选状态待核实"


def main() -> None:
    data = pd.read_csv(SOURCE, dtype={"股票代码": str})
    industry = data[data["行业入口候选"].eq(1)].copy()
    industry = industry.sort_values(["股票代码", "年份"])
    assert len(industry) == 419
    assert industry["股票代码"].nunique() == 57
    assert not industry.duplicated(["股票代码", "年份"]).any()

    output = []
    for _, group in industry.groupby("股票代码", sort=True):
        previous = None
        for _, row in group.iterrows():
            current_categories = categories(row["主营业务表原文摘录"])
            base = {
                "股票代码": row["股票代码"], "公司全称": row["公司全称"],
                "年份": int(row["年份"]), "行业分类代码": row["行业分类代码"],
                "行业分类名称": row["行业分类名称"],
                "分类标准口径": "中国上市公司协会2023版" if int(row["年份"]) == 2023 else "证监会2012年修订版",
                "业务类别指纹": "|".join(sorted(current_categories)),
                "口径调整勾选": checked_status(
                    row["主营业务表原文摘录"], "公司主营业务数据统计口径"
                ),
                "业务重大变化勾选": checked_status(
                    row["主营业务表原文摘录"], "业务、产品或服务发生重大变化"
                ),
                "年报链接": row["年报链接"],
                "年报主营业务表PDF页序号": row["年报主营业务表PDF页序号"],
                "当前复核状态": row["复核状态"],
            }
            if previous is None:
                base.update({
                    "上一候选年份": "", "与上一候选年文本相似度": "",
                    "业务类别指纹Jaccard": "", "行业代码是否变化": "首年",
                    "是否跨分类标准": "首年", "公司名称是否变化": "首年", "年份是否连续": "首年",
                    "建议复核路径": "首年锚点复核",
                    "分流原因": "该公司首次进入已核实行业候选，需要建立人工锚点",
                })
            else:
                previous_categories = categories(previous["主营业务表原文摘录"])
                similarity = trigram_cosine(
                    previous["主营业务表原文摘录"], row["主营业务表原文摘录"]
                )
                union = previous_categories | current_categories
                jaccard = len(previous_categories & current_categories) / len(union) if union else 1.0
                code_changed = str(previous["行业分类代码"]) != str(row["行业分类代码"])
                name_changed = previous["公司全称"] != row["公司全称"]
                year_gap = int(row["年份"]) - int(previous["年份"])
                standard_changed = int(previous["年份"]) != 2023 and int(row["年份"]) == 2023
                major_change = base["业务重大变化勾选"] == "适用"

                if code_changed or name_changed or major_change or jaccard < 0.5:
                    route = "深度复核"
                elif similarity >= 0.70 or (similarity >= 0.55 and jaccard >= 0.75):
                    route = "快速表格核对"
                else:
                    route = "标准人工复核"

                reasons = []
                if code_changed:
                    reasons.append("行业代码变化（同时跨分类标准）" if standard_changed else "行业代码变化")
                if name_changed: reasons.append("公司全称变化")
                if major_change: reasons.append("年报勾选业务重大变化适用")
                if jaccard < 0.5: reasons.append("业务类别指纹变化较大")
                if not reasons:
                    reasons.append("文本和业务类别相似度分流")
                if year_gap != 1:
                    reasons.append("候选年份不连续，不能视为插值")

                base.update({
                    "上一候选年份": int(previous["年份"]),
                    "与上一候选年文本相似度": round(similarity, 6),
                    "业务类别指纹Jaccard": round(jaccard, 6),
                    "行业代码是否变化": "是" if code_changed else "否",
                    "是否跨分类标准": "是" if standard_changed else "否",
                    "公司名称是否变化": "是" if name_changed else "否",
                    "年份是否连续": "是" if year_gap == 1 else "否",
                    "建议复核路径": route, "分流原因": "；".join(reasons),
                })
            output.append(base)
            previous = row

    matrix = pd.DataFrame(output)
    assert len(matrix) == 419
    assert not matrix.duplicated(["股票代码", "年份"]).any()
    matrix.to_csv(MATRIX, index=False, encoding="utf-8-sig")

    summary = (
        matrix.groupby(["建议复核路径"], dropna=False).size()
        .rename("公司年份数").reset_index()
    )
    summary["占419条比例"] = (summary["公司年份数"] / len(matrix)).round(6)
    summary.to_csv(SUMMARY, index=False, encoding="utf-8-sig")
    matrix[matrix["建议复核路径"].eq("快速表格核对")].to_csv(
        FAST_QUEUE, index=False, encoding="utf-8-sig"
    )
    matrix[matrix["建议复核路径"].eq("深度复核")].to_csv(
        DEEP_QUEUE, index=False, encoding="utf-8-sig"
    )
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
