import csv
import glob
import os
import re

import pdfplumber


OUT = "outputs/证监会农林牧渔业年度候选面板_已核实年份.csv"
category_names = {
    "01": "农业",
    "02": "林业",
    "03": "畜牧业",
    "04": "渔业",
    "05": "农林牧渔服务业",
}


def extract_rows(path):
    period = os.path.basename(path).removesuffix(".pdf")
    year = int(period[:4])
    with pdfplumber.open(path) as pdf:
        text = "\n".join((p.extract_text() or "") for p in pdf.pages[:2])

    rows = []
    category = None
    in_agri = False
    for raw in text.splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if "农、林、牧、渔业" in line:
            in_agri = True
        if in_agri and (line.startswith("采矿业") or "采矿业(B)" in line):
            break

        marker = re.search(r"(?:^| )0([1-5]) (农业|林业|畜牧业|渔业|农、林、牧、渔服务业|农、林、牧、渔专业(?:及辅助性活动)?)", line)
        if marker:
            category = "0" + marker.group(1)

        if not in_agri or category is None:
            continue

        match = re.search(r"(?<!\d)([01236]\d{5})\s+(.+)$", line)
        if not match:
            continue
        code, name = match.groups()
        # 研究对象限定沪深A股；200/900开头证券不纳入。
        if code.startswith(("200", "900")):
            continue
        name = name.strip()
        st_flag = "是" if ("ST" in name.upper()) else "否"
        if year >= 2023:
            source_org = "中国上市公司协会"
            standard = "《中国上市公司协会上市公司行业统计分类指引》（2023）"
        else:
            source_org = "中国证监会"
            standard = "《上市公司行业分类指引》（2012年修订）"
        category_label = ("农、林、牧、渔专业及辅助性活动" if year >= 2023 and category == "05"
                          else category_names[category])
        rows.append([year, period, code, name, category, category_label, st_flag,
                     source_org, standard, os.path.basename(path), "候选待年报复核"])
    return rows


paths = sorted(glob.glob("work/csrc_industry/*.pdf"))
all_rows = []
for path in paths:
    all_rows.extend(extract_rows(path))

with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["年份", "来源期次", "股票代码", "证券简称_当期", "行业大类代码", "行业大类名称",
                     "ST标记_当期", "来源机构", "分类标准", "本地原始文件", "样本状态"])
    writer.writerows(all_rows)

print(f"wrote {len(all_rows)} rows to {OUT}")
for year in sorted({row[0] for row in all_rows}):
    print(year, sum(row[0] == year for row in all_rows))
