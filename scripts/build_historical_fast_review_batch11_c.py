#!/usr/bin/env python3
"""Build historical fast-review batch 11 group C from the protected v20 master.

The script writes an independent evidence table only.  It never edits or merges
the v20 master.  Targets: 600097, 600257 and 600506, all still-pending rows.
"""
from decimal import Decimal, ROUND_HALF_UP, getcontext
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v20_跨年快速复核第十批.csv"
OUTPUT = ROOT / "outputs" / "跨年快速复核第十一批_C组_3家公司.csv"

# Ratios are used for 30%/50% threshold tests.  Preserve substantially more
# precision than the eight-decimal display value; the text fields below are
# Decimal high-precision calculation values, not infinite decimal expansions.
getcontext().prec = 50


# Ocean-fishing revenue, separately disclosed deep-processing revenue, total
# revenue, and business-evidence page.  The "食品加工" segment is canned food /
# canned fish sales, so it is retained only as an excluded deep-processing
# evidence item.  Strict and expanded numerators both equal ocean fishing.
# Fish trading, sea transport and canned-food processing are excluded.
KAICHUANG = {
    2013: ("813449172.68", "0", "815560060.18", "10"),
    2014: ("825661377.66", "0", "831010886.69", "8"),
    2015: ("670057033.50", "0", "675047903.11", "9"),
    2016: ("754858422.19", "388390235.18", "1148730870.22", "10|11"),
    2017: ("932636978.11", "691448783.46", "1787457508.80", "11"),
    2018: ("990654889.78", "728133946.58", "1909976199.73", "10"),
    2019: ("1095930981.91", "745070522.65", "2212094888.87", "11"),
    2020: ("954024109.68", "718828219.96", "1968952164.37", "10"),
    2021: ("1122801626.55", "621302350.86", "1980317010.95", "10"),
}


# The annual report's industry segment "农业" is used, consistently with the
# verified 2023 treatment.  It is not added to the overlapping product segment
# "水产品".  Alcohol, medicine/medical services, health products, catering and
# other operations are excluded.
DAHU = {
    2013: ("433439335.24", "623970942.00", "11"),
    2014: ("462151020.71", "676466196.42", "9"),
    2015: ("559827909.56", "808924738.75", "9|10"),
    2016: ("643076222.00", "926193680.67", "9|10"),
    2017: ("683047518.33", "996570641.33", "12"),
    2018: ("674309181.21", "1070087927.39", "10|11"),
    2019: ("781975466.36", "1112490033.62", "10"),
    2020: ("605869922.58", "936517809.75", "12"),
    2021: ("753357255.35", "1292312436.98", "17|18"),
}


# Fruit sales are only an audit upper bound: the annual reports describe both
# own production and purchased-fruit distribution but do not split their
# respective revenue.  No formal strict/expanded numerator is therefore made
# up.  Fruit wine, steel/building materials, cotton, lubricants and chemicals
# are excluded even from this upper bound.
XIANGLI_UPPER = {
    2013: ("91161714.90", "115107898.19", "11"),
    2014: ("105084806.54", "111809729.71", "12"),
    2015: ("51786943.18", "57865834.04", "10|12"),
    2016: ("60325334.56", "68031962.23", "10"),
    2017: ("57973075.68", "65318509.11", "11|12"),
    2018: ("36067770.69", "42555553.09", "10|11"),
    2019: ("15537236.35", "22029368.39", "9|10"),
    2020: ("24540173.32", "118584175.06", "13|14"),
    2021: ("128338572.20", "349536461.22", "13|14"),
}


def raw_share(numerator: str, denominator: str) -> Decimal:
    return Decimal(numerator) / Decimal(denominator)


def rounded_share(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)


def raw_text(value: Decimal) -> str:
    """Return the Decimal high-precision value used for threshold tests."""
    return format(value, "f")


def classify(strict_fraction: Decimal, expanded_fraction: Decimal):
    strict = "是" if strict_fraction >= Decimal("0.50") else "否"
    expanded = "是" if expanded_fraction >= Decimal("0.50") else "否"
    boundary = (
        "是" if Decimal("0.30") <= expanded_fraction < Decimal("0.50") else "否"
    )
    return strict, expanded, boundary


def main() -> None:
    source = pd.read_csv(SOURCE, dtype={"股票代码": str}, keep_default_na=False)
    targets = {"600097", "600257", "600506"}
    selected = source[
        source["股票代码"].isin(targets)
        & ~source["复核状态"].str.startswith("已人工复核", na=False)
    ].sort_values(["股票代码", "年份"])

    assert len(source) == 958
    assert len(selected) == 27
    assert selected.groupby("股票代码").size().to_dict() == {
        "600097": 9, "600257": 9, "600506": 9
    }
    assert selected.groupby("股票代码")["年份"].apply(list).to_dict() == {
        "600097": list(range(2013, 2022)),
        "600257": list(range(2013, 2022)),
        "600506": list(range(2013, 2022)),
    }
    assert not selected.duplicated(["股票代码", "年份"]).any()
    # v20 contains no 2022 row for these companies.  Do not manufacture one or
    # copy an adjacent year's industry classification.
    assert not selected["年份"].eq(2022).any()

    rows = []
    for _, src in selected.iterrows():
        code, year = src["股票代码"], int(src["年份"])
        strict_n = expanded_n = stored_n = ""
        processing_n = ""
        strict_raw = expanded_raw = stored_raw = ""
        strict_round = expanded_round = stored_round = ""
        upper_n = upper_raw = upper_round = ""
        pending = ""
        overlap = "否（只使用同一分行业维度，不与分产品或分地区收入相加）"

        if code == "600097":
            strict_n, processing_n, total, page = KAICHUANG[year]
            expanded_n = strict_n
            sf = raw_share(strict_n, total)
            ef = sf
            strict, expanded, boundary = classify(sf, ef)
            strict_raw, expanded_raw = raw_text(sf), raw_text(ef)
            strict_round, expanded_round = f"{rounded_share(sf):.8f}", f"{rounded_share(ef):.8f}"
            stored_n = strict_n
            stored_fraction = sf
            stored_raw, stored_round = raw_text(stored_fraction), f"{rounded_share(stored_fraction):.8f}"
            business = "海洋捕捞（严格=扩展）；罐头食品/鱼罐头深加工排除"
            formula = (
                "严格=扩展=分行业海洋捕捞；分行业食品加工实为罐头食品/鱼罐头销售，"
                "仅保留为深加工排除项；渔货贸易、海上运输不计入"
            )
            reason = (
                f"严格及扩展Decimal高精度门槛计算值={strict_raw}。"
                f"食品加工深加工排除金额={Decimal(processing_n):.2f}元；"
                "渔货贸易和海上运输亦已排除。"
            )
        elif code == "600257":
            strict_n, total, page = DAHU[year]
            expanded_n = strict_n
            sf = ef = raw_share(strict_n, total)
            strict, expanded, boundary = classify(sf, ef)
            strict_raw = expanded_raw = raw_text(sf)
            strict_round = expanded_round = f"{rounded_share(sf):.8f}"
            stored_n, stored_raw, stored_round = strict_n, strict_raw, strict_round
            business = "水产品养殖（年报分行业‘农业’）"
            formula = (
                "严格=扩展=分行业农业；不与重叠的分产品水产品相加；"
                "白酒、药品/医药贸易、保健品、医疗服务、餐饮及其他不计入"
            )
            reason = (
                f"农业分行业Decimal高精度门槛计算值={strict_raw}；沿用已核实2023年的水产品养殖口径。"
                "非涉农健康产业收入全部排除。"
            )
        else:
            upper_n, total, page = XIANGLI_UPPER[year]
            uf = raw_share(upper_n, total)
            upper_raw, upper_round = raw_text(uf), f"{rounded_share(uf):.8f}"
            business = "果品销售（仅作审计上限，正式分子待拆分自产与外购）"
            formula = (
                "审计上限=分产品果品销售；正式严格/扩展分子=自产果品对应收入（年报未拆分）"
            )
            overlap = "否（果品产品收入仅作上限；未与行业、地区或销售模式收入相加）"
            pending = (
                "年报同时披露自产果品与外购果品购销，但未分别披露收入；"
                "不能把全部果品销售直接视为农业生产或初加工收入。"
            )
            if uf < Decimal("0.30"):
                strict = expanded = boundary = "否"
                reason = (
                    f"果品收入审计上限Decimal高精度门槛计算值={upper_raw}，低于30%；即使全部计入也不达边界。"
                    "果酒、钢材/建材、皮棉、润滑油脂及其他化工产品均排除。"
                )
            elif uf < Decimal("0.50"):
                strict = expanded = "否"
                boundary = "待核实"
                reason = (
                    f"果品收入审计上限Decimal高精度门槛计算值={upper_raw}，低于50%，故严格及扩展均为否；"
                    "自产部分能否达到30%无法由年报拆分。"
                )
            else:
                strict = expanded = boundary = "待核实"
                reason = (
                    f"果品收入审计上限Decimal高精度门槛计算值={upper_raw}；因自产与外购收入未拆分，"
                    "不能据此判定50%或30%门槛。"
                )

        rows.append({
            "股票代码": code,
            "公司全称": src["公司全称"],
            "年份": year,
            "行业分类代码": src["行业分类代码"] if src["行业分类代码"] else "待核实",
            "行业分类名称": src["行业分类名称"] if src["行业分类名称"] else "待核实",
            "涉农业务_保守不重叠口径": business,
            "工作表采用涉农业务营业收入_元": stored_n,
            "严格口径营业收入_元": strict_n,
            "扩展口径营业收入_元": expanded_n,
            "深加工排除项_食品加工营业收入_元": processing_n,
            "仅作审计上限收入_元": upper_n,
            "公司营业收入_元": total,
            "分子公式": formula,
            "工作表采用原始未四舍五入比例": stored_raw,
            "严格口径原始未四舍五入比例": strict_raw,
            "扩展口径原始未四舍五入比例": expanded_raw,
            "审计上限原始未四舍五入比例": upper_raw,
            "比例精度说明": "比例门槛采用Decimal 50位精度计算；文本值为高精度计算值，不表示无限精度小数",
            "工作表采用涉农收入占比_8位": stored_round,
            "严格口径收入占比_8位": strict_round,
            "扩展口径收入占比_8位": expanded_round,
            "审计上限收入占比_8位": upper_round,
            "严格样本结论": strict,
            "扩展样本结论": expanded,
            "边界样本结论": boundary,
            "是否存在分部收入重叠": overlap,
            "复核说明": reason,
            "待核实点": pending,
            "年报主营业务证据PDF页序号": page,
            "公司营业收入证据PDF页序号": src["利润表PDF页序号"],
            "年报链接": src["年报链接"],
            "2022行业字段处理": "v20无该公司2022公司—年份行；未新增、未插值、未复制相邻年份",
            "记录类型": "第十一批C组新增跨年快速复核（未合并）",
            "复核日期": "2026-08-11",
        })

    output = pd.DataFrame(rows)
    assert len(output) == 27
    assert not output.duplicated(["股票代码", "年份"]).any()
    assert output["严格样本结论"].value_counts().to_dict() == {
        "是": 16, "待核实": 7, "否": 4
    }
    assert output["扩展样本结论"].value_counts().to_dict() == {
        "是": 16, "待核实": 7, "否": 4
    }
    assert output["边界样本结论"].value_counts().to_dict() == {
        "否": 17, "待核实": 8, "是": 2
    }
    unresolved = output[output["股票代码"].eq("600506") & output["年份"].ne(2020)]
    assert unresolved["工作表采用涉农业务营业收入_元"].eq("").all()
    assert unresolved["工作表采用涉农收入占比_8位"].eq("").all()
    output.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print(
        "batch11-C rows=27; strict yes/no/pending=16/4/7; "
        "expanded yes/no/pending=16/4/7; boundary yes/no/pending=2/17/8; not merged"
    )


if __name__ == "__main__":
    main()
