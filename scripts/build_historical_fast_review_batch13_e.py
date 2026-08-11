#!/usr/bin/env python3
"""Build historical fast-review batch 13 group E from the protected v20 table.

The output is an independent evidence table.  It never edits or merges v20.
Targets every still-pending row for 300498, 002567 and 002688.
"""
from decimal import Decimal, ROUND_HALF_UP, getcontext
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs" / "涉农候选公司年份_年报主营业务复核工作表_v20_跨年快速复核第十批.csv"
OUTPUT = ROOT / "outputs" / "跨年快速复核第十三批_E组_3家公司.csv"
getcontext().prec = 50


# year: farming revenue, broiler-category revenue, veterinary-input revenue,
# mixed meat-processing revenue, mixed raw-milk/dairy revenue, farming cost
# (reverse column check), total, pages.  From 2017 onward the annual reports say
# that the broiler category includes chilled/fresh chicken, so the whole farming
# industry amount cannot be used as an exact strict numerator.
WENS = {
    2015: ("46627670134.90", "", "702878261.36", "523289636.54", "333931641.43", "37287562325.23", "48237369754.91", "18|19"),
    2016: ("57557623514.21", "", "481646009.75", "782570361.91", "390034084.93", "41191772615.54", "59355237219.15", "24|25"),
    2017: ("54060357192.70", "17564233528.25", "487342419.90", "186226896.12", "489593371.33", "43162391244.37", "55657160144.30", "24|25"),
    2018: ("55463643419.41", "19956314785.12", "500089537.92", "232701333.35", "591907207.19", "46195918701.57", "57235997041.92", "32|34"),
    2019: ("70687031000.96", "26785916568.47", "624793036.73", "297540415.47", "728299016.31", "51093681786.93", "73120412619.72", "23|24"),
    2020: ("72686675695.28", "24294126609.40", "751380461.70", "364568516.63", "840296798.63", "58632493185.51", "74923760203.84", "19|20"),
    2021: ("62545041681.99", "30327589215.31", "716154534.16", "401125950.86", "1062338063.04", "68694804948.38", "64954064169.73", "22|23"),
    2022: ("81242414814.58", "35581599764.62", "703127857.65", "448541829.67", "1015689430.76", "68753086760.13", "83708187230.99", "22|23"),
}


# year: feed revenue, farming revenue, veterinary-input revenue, mixed
# slaughter/meat revenue, reverse-check eligible costs, total, pages
TANG = {
    2014: ("9524401935.68", "83731858.89", "8340865.96", "381765499.83", "8655434767.61+118550694.72+6594082.64", "10069486005.19", "16"),
    2015: ("8834554268.51", "124345753.86", "17065484.59", "436695981.97", "8014631593.69+62822929.28+10175782.83", "9412661488.93", "13|14"),
    2018: ("14285747633.95", "546089245.53", "9543636.71", "564136553.16", "13097805497.62+530419411.37+4740871.21", "15405517069.35", "18|19"),
    2019: ("13550599496.74", "803191595.93", "13347555.92", "975724206.30", "12501954367.37+510460636.89+6245872.96", "15342862854.89", "17|18"),
    2020: ("15347625302.74", "2452984024.61", "21250548.39", "691816180.78", "14257195699.99+1196229904.84+12019363.06", "18513676056.52", "20|21"),
    2021: ("17506913337.44", "3473845871.18", "24789469.41", "736645564.64", "16199224802.97+3560840714.42+15430136.53", "21742194242.67", "17|18|19"),
    2022: ("20354975598.47", "4866355212.41", "20436858.12", "1296812492.48", "19129530837.45+4122957707.43+12233301.77", "26538580161.48", "25|26"),
}


# year: eligible veterinary-input revenue components, their corresponding
# costs, mixed starch/co-product processing revenue, total, pages.
JINHE = {
    2014: (("707674875.37",), ("451099680.34",), "129952415.24", "839805806.69", "19"),
    2015: (("1124166517.50",), ("768812381.07",), "108114673.36", "1250468533.75", "16|17"),
    2018: (("1042127013.04", "123606095.22", "33283470.09"), ("563465194.92", "51859468.82", "24847837.21"), "331745086.79", "1628890098.36", "17|18"),
    2019: (("1060415186.97", "86526906.29", "31949527.40"), ("526819824.32", "49826118.35", "23688699.59"), "471607564.44", "1782364081.84", "19|20"),
    2020: (("935075133.24", "268427474.37", "34256028.97"), ("569172220.41", "87551436.77", "25825984.44"), "456087077.09", "1814638965.54", "19|20"),
    2021: (("1066088143.18", "291685464.31", "32285275.03"), ("708058291.16", "79865908.93", "28083175.74"), "511220557.45", "2077988730.16", "19|20"),
    2022: (("983933447.02", "330166810.59", "19558574.68"), ("707751261.96", "107095582.84", "17279288.13"), "566237431.43", "2122705317.42", "18|19|20"),
}


def D(value) -> Decimal:
    return Decimal(str(value))


def sum_formula(formula: str) -> Decimal:
    return sum((D(part) for part in formula.split("+")), D("0"))


def share(numerator: Decimal, denominator: Decimal) -> Decimal:
    return numerator / denominator


def text(value: Decimal) -> str:
    return format(value, "f")


def shown(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.00000001'), rounding=ROUND_HALF_UP):.8f}"


def classify(strict_lower_fraction: Decimal, strict_upper_fraction: Decimal, expanded_fraction: Decimal):
    if strict_lower_fraction >= D("0.50"):
        strict = "是"
    elif strict_upper_fraction < D("0.50"):
        strict = "否"
    else:
        strict = "待核实"
    expanded = "是" if expanded_fraction >= D("0.50") else "否"
    boundary = "是" if D("0.30") <= expanded_fraction < D("0.50") else "否"
    return strict, expanded, boundary


def base(src: pd.Series, code: str, year: int, pages: str) -> dict:
    return {
        "股票代码": code,
        "公司全称": src["公司全称"],
        "年份": year,
        "行业分类代码": src["行业分类代码"] or "待核实",
        "行业分类名称": src["行业分类名称"] or "待核实",
        "年报主营业务证据PDF页序号": pages,
        "公司营业收入证据PDF页序号": src["利润表PDF页序号"],
        "年报链接": src["年报链接"],
        "记录类型": "第十三批E组新增跨年快速复核（未合并）",
        "复核日期": "2026-08-11",
    }


def main() -> None:
    source = pd.read_csv(SOURCE, dtype={"股票代码": str}, keep_default_na=False)
    targets = {"300498", "002567", "002688"}
    selected = source[
        source["股票代码"].isin(targets)
        & ~source["复核状态"].str.startswith("已人工复核", na=False)
    ].sort_values(["股票代码", "年份"])
    assert len(source) == 958
    assert len(selected) == 22
    assert selected.groupby("股票代码").size().to_dict() == {"002567": 7, "002688": 7, "300498": 8}
    assert not selected.duplicated(["股票代码", "年份"]).any()

    rows = []
    for _, src in selected.iterrows():
        code, year = src["股票代码"], int(src["年份"])
        if code == "300498":
            farming, broiler, vet, meat, dairy, farming_cost, total_raw, pages = WENS[year]
            farming_n = D(farming)
            broiler_n = D(broiler) if broiler else D("0")
            strict_n = farming_n - broiler_n
            strict_upper_n = farming_n
            expanded_n = strict_n + D(vet)
            mixed_n = D(meat) + D(dairy)
            upper_n = strict_upper_n + D(vet) + mixed_n
            total = D(total_raw)
            cost_n = D(farming_cost)
            if broiler:
                strict_formula = (
                    f"下界=养殖行业{farming_n:,.2f}-肉鸡类{broiler_n:,.2f}={strict_n:,.2f}；"
                    f"上界=养殖行业{strict_upper_n:,.2f}"
                )
                expanded_formula = (
                    f"下界=严格下界{strict_n:,.2f}+兽药投入品{D(vet):,.2f}；"
                    f"上界=养殖行业{strict_upper_n:,.2f}+兽药投入品{D(vet):,.2f}+加工混合项"
                )
            else:
                strict_formula = f"养殖行业{strict_n:,.2f}（按当年证据作为严格口径）"
                expanded_formula = f"养殖行业{strict_n:,.2f}+兽药投入品{D(vet):,.2f}"
            mixed_formula = f"肉制品加工{D(meat):,.2f}+原奶及乳制品{D(dairy):,.2f}"
            cost_formula = f"同一分行业养殖营业成本{cost_n:,.2f}（反向核对，不作收入分子）"
            business = "养殖行业扣除肉鸡类（严格下界）；养殖严格下界+兽药投入品（扩展下界）" if broiler else "养殖（严格）；养殖+兽药投入品（扩展下界）"
            pending = (
                "2017年起肉鸡类含冰鲜鸡/鲜品，故养殖行业仅作严格上界；严格下界扣除整个肉鸡类。"
                "肉制品加工及‘原奶及乳制品’含初/深加工未拆分，仅作扩展上界。"
                if broiler else
                "肉制品加工及‘原奶及乳制品’含初/深加工未拆分，仅作上界；下界已超过50%，不影响纳入结论。"
            )
            overlap = "否（采用互斥分行业/分产品项目；加工混合项只作上界）"
            special_note = (
                "2017年报说明冰鲜鸡由肉制品加工调整至肉鸡类，且冰鲜鸡收入低于肉鸡类收入5%；"
                "2017年起不能把含鲜品的肉鸡类整项计入严格分子，采用‘养殖行业减肉鸡类’的保守下界。"
                if year >= 2017 else ""
            )
        elif code == "002567":
            feed, farming, vet, meat, cost_formula_raw, total_raw, pages = TANG[year]
            strict_n = D(farming)
            strict_upper_n = strict_n
            expanded_n = D(feed) + strict_n + D(vet)
            mixed_n = D(meat)
            upper_n = expanded_n + mixed_n
            total = D(total_raw)
            cost_n = sum_formula(cost_formula_raw)
            strict_formula = f"养殖/牲猪{strict_n:,.2f}"
            expanded_formula = f"饲料{D(feed):,.2f}+养殖/牲猪{strict_n:,.2f}+兽药/动物保健{D(vet):,.2f}"
            mixed_formula = f"屠宰及肉类/肉类{mixed_n:,.2f}"
            cost_formula = cost_formula_raw.replace("+", "+") + f"={cost_n:,.2f}（对应收入项目的营业成本反核）"
            business = "养殖（严格）；饲料+养殖+兽药/动物保健（扩展下界）"
            pending = "屠宰及肉类大类含初加工与肉制品深加工且未拆分，仅作上界；扩展下界已超过50%。"
            overlap = "否（同一分行业维度加总；屠宰及肉类仅作上界）"
            special_note = {
                2014: "采用2014年报当期主营业务表；2015年报对2014饲料比较数有重列，本表不倒替当期披露。",
                2020: "采用2020年报当期合并利润表营业收入及收入构成；后续比较口径不倒替当期披露。",
            }.get(year, "")
        else:
            revenues, costs, processing, total_raw, pages = JINHE[year]
            strict_n = D("0")
            strict_upper_n = strict_n
            expanded_n = sum((D(v) for v in revenues), D("0"))
            mixed_n = D(processing)
            upper_n = expanded_n + mixed_n
            total = D(total_raw)
            cost_n = sum((D(v) for v in costs), D("0"))
            labels = "药物饲料添加剂" if len(revenues) == 1 else "兽用化学药品+兽用生物制品/疫苗+药物饲料添加剂"
            strict_formula = "0（无直接农业生产收入）"
            expanded_formula = "+".join(revenues) + f"={expanded_n:,.2f}（{labels}）"
            mixed_formula = f"淀粉及联产品/农产品加工业{mixed_n:,.2f}"
            cost_formula = "+".join(costs) + f"={cost_n:,.2f}（对应兽药投入品营业成本反核）"
            business = "兽药、兽用疫苗及药物饲料添加剂（扩展下界）"
            pending = "淀粉及联产品/农产品加工业可能含初加工与深加工，未拆分，仅作上界；环保及其他非农业用途排除。"
            overlap = "否（兽药投入品使用互斥行业项目；农产品加工仅作上界）"
            special_note = (
                "2020年起按农业农村部公告第194号，部分原‘药物饲料添加剂’产品改列‘兽用化学药品’；"
                "本表按各年年报当期分类加总互斥兽药投入品项目。"
                if year >= 2020 else ""
            )

        assert D("0") <= strict_n <= strict_upper_n <= upper_n <= total
        assert strict_n <= expanded_n <= upper_n
        sf, suf, ef, uf = share(strict_n, total), share(strict_upper_n, total), share(expanded_n, total), share(upper_n, total)
        strict, expanded, boundary = classify(sf, suf, ef)
        adopted_n = strict_n if strict == "是" else expanded_n
        adopted_f = sf if strict == "是" else ef
        rows.append({
            **base(src, code, year, pages),
            "涉农业务_保守不重叠口径": business,
            "工作表采用涉农业务营业收入_元": f"{adopted_n:.2f}",
            "严格口径营业收入_元": f"{strict_n:.2f}" if strict != "待核实" else "",
            "严格口径收入下界_元": f"{strict_n:.2f}",
            "严格口径收入上界_元": f"{strict_upper_n:.2f}",
            "严格口径收入公式": strict_formula,
            "扩展口径营业收入_元": f"{expanded_n:.2f}",
            "扩展口径收入公式": expanded_formula,
            "扩展口径收入下界_元": f"{expanded_n:.2f}",
            "加工混合项审计上限增量_元": f"{mixed_n:.2f}",
            "加工混合项公式": mixed_formula,
            "扩展口径收入上界_元": f"{upper_n:.2f}",
            "公司营业收入_元": f"{total:.2f}",
            "公司营业收入公式": "合并利润表‘营业收入’（非营业总收入）",
            "营业成本反向证据_元": f"{cost_n:.2f}",
            "营业成本反向证据公式": cost_formula,
            "收入成本列反核结论": "收入分子取营业收入列；成本证据仅用于反向核对，未误作收入",
            "工作表采用Decimal高精度门槛计算值": text(adopted_f),
            "严格口径Decimal高精度门槛计算值": text(sf),
            "严格口径上界Decimal高精度门槛计算值": text(suf),
            "扩展口径Decimal高精度门槛计算值": text(ef),
            "扩展上界Decimal高精度门槛计算值": text(uf),
            "工作表采用涉农收入占比_8位": shown(adopted_f),
            "严格口径收入占比_8位": shown(sf),
            "严格口径上界收入占比_8位": shown(suf),
            "扩展口径收入占比_8位": shown(ef),
            "扩展上界收入占比_8位": shown(uf),
            "严格样本结论": strict,
            "扩展样本结论": expanded,
            "边界样本结论": boundary,
            "是否存在分部收入重叠": overlap,
            "复核说明": f"严格区间=[{shown(sf)}, {shown(suf)}]，扩展下界={shown(ef)}，含全部加工混合项的审计上界={shown(uf)}。",
            "口径变更或比较数说明": special_note,
            "待核实点": pending,
            "2022行业字段处理": "沿用v20原值；为待核实时不插值、不复制相邻年份",
            "比例精度说明": "门槛采用Decimal 50位精度计算；8位值仅供显示",
        })

    output = pd.DataFrame(rows)
    assert len(output) == 22
    assert not output.duplicated(["股票代码", "年份"]).any()
    assert output["严格样本结论"].value_counts().to_dict() == {"否": 14, "是": 7, "待核实": 1}
    assert output["扩展样本结论"].value_counts().to_dict() == {"是": 22}
    assert output["边界样本结论"].value_counts().to_dict() == {"否": 22}
    assert (output["营业成本反向证据_元"].astype(float) > 0).all()
    assert output.loc[output["年份"].eq(2022), "行业分类代码"].eq("待核实").all()
    output.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    wens_2021 = output[(output["股票代码"] == "300498") & (output["年份"] == 2021)].iloc[0]
    assert wens_2021["严格样本结论"] == "待核实"
    assert wens_2021["严格口径营业收入_元"] == ""
    assert wens_2021["严格口径收入占比_8位"] == "0.49600364"
    assert wens_2021["严格口径上界收入占比_8位"] == "0.96291191"
    print("batch13-E rows=22; strict yes/pending/no=7/1/14; expanded yes=22; boundary no=22; not merged")


if __name__ == "__main__":
    main()
