#!/usr/bin/env python3
"""Structure official MOA leading-firm lists without modifying inherited files."""

from __future__ import annotations

import csv
import html
import re
import subprocess
from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw_official_sources" / "moa_leading_firms"
WORK = ROOT / "work" / "leading_firms_text"
OUT = ROOT / "outputs" / "农业产业化国家重点龙头企业官方名单_结构化_v1.csv"

TERMINALS = (
    "有限公司", "有限责任公司", "股份公司", "股份有限公司", "集团有限公司",
    "集团有限责任公司", "集团公司", "集团", "公司", "中心", "市场", "总会",
    "原种猪场", "农场", "林场", "茶厂", "药厂", "酒厂", "加工厂", "制品厂",
    "研究所", "研究院", "基地", "合作社", "联合社", "商行", "商贸城", "产业园", "园区",
)

HEADER_LINES = {
    "通知决定", "意见通知", "附件", "附件1", "附件2",
    "中华人民共和国农业农村部公报",
    "第八次监测合格农业产业化国家重点龙头企业名单",
    "第九次监测合格农业产业化国家重点龙头企业名单",
    "监测合格农业产业化国家重点龙头企业名单",
    "递补农业产业化国家重点龙头企业名单",
}


def page_text(pdf: Path, page: int) -> list[str]:
    run = subprocess.run(
        ["pdftotext", "-f", str(page), "-l", str(page), "-raw", str(pdf), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [re.sub(r"\s+", "", line) for line in run.stdout.splitlines()]


def is_terminal(text: str) -> bool:
    return (text.endswith(TERMINALS) or text.endswith("（有限公司）")) and text.count("（") == text.count("）")


def clean_fragments(lines: list[tuple[int, str]]) -> list[tuple[int, str]]:
    cleaned = []
    for page, line in lines:
        if not line or line in HEADER_LINES or line.isdigit():
            continue
        if re.fullmatch(r"(?:\d+)?中华人民共和国农业(?:农村)?部公报(?:\d+)?", line):
            continue
        if line.startswith("注：") or line in {"标注", "“*”", "的为更名企业。"}:
            continue
        cleaned.append((page, line))
    return cleaned


def join_names(lines: list[tuple[int, str]]) -> list[tuple[int, str, str]]:
    """Join pdftotext line wraps and return page, raw name, normalized name."""
    result = []
    buffer = ""
    start_page = None
    for page, fragment in clean_fragments(lines):
        if (
            fragment in {"集团有限公司", "集团有限责任公司", "有限责任公司", "股份有限公司"}
            or fragment.startswith(("（", "("))
        ) and not buffer and result:
            prior_page, prior_raw, _ = result.pop()
            combined = prior_raw + fragment
            normalized = combined.removeprefix("*").replace("(", "（").replace(")", "）")
            result.append((prior_page, combined, normalized))
            continue
        if start_page is None:
            start_page = page
        buffer += fragment
        if is_terminal(buffer):
            raw_name = buffer
            normalized = raw_name.removeprefix("*")
            normalized = normalized.replace("(", "（").replace(")", "）")
            result.append((start_page, raw_name, normalized))
            buffer = ""
            start_page = None
    if buffer:
        raise ValueError(f"Unclosed name fragment from page {start_page}: {buffer}")
    return result


def pdf_section(
    pdf: Path,
    pages: range,
    start_after: str | None = None,
    stop_before: str | None = None,
    start_occurrence: int = 1,
) -> list[tuple[int, str, str]]:
    fragments: list[tuple[int, str]] = []
    started = start_after is None
    stopped = False
    start_hits = 0
    for page in pages:
        for line in page_text(pdf, page):
            if not started:
                if line == start_after:
                    start_hits += 1
                    if start_hits == start_occurrence:
                        started = True
                continue
            if stop_before and line == stop_before:
                stopped = True
                break
            fragments.append((page, line))
        if stopped:
            break
    if not started:
        raise ValueError(f"Start marker not found: {start_after}")
    return join_names(fragments)


def batch7_names(path: Path) -> list[str]:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    body = soup.select_one(".sj_arc_body")
    if body is None:
        raise ValueError("Official batch-7 article body not found")
    texts = []
    started = False
    for p in body.find_all("p"):
        text = re.sub(r"\s+", "", html.unescape(p.get_text("", strip=True)))
        if text == "第七批农业产业化国家重点龙头企业名单":
            started = True
            continue
        if started and text:
            texts.append(text)
    return texts


def add_pdf_rows(
    rows: list[dict[str, str]],
    names: list[tuple[int, str, str]],
    *,
    list_year: str,
    event_type: str,
    list_type: str,
    document_name: str,
    document_number: str,
    document_date: str,
    publication_date: str,
    valid_from_rule: str,
    valid_until_rule: str,
    source_url: str,
    local_filename: str,
) -> None:
    for order, (page, raw_name, normalized) in enumerate(names, 1):
        rows.append({
            "list_year": list_year,
            "event_type": event_type,
            "list_type": list_type,
            "list_order": str(order),
            "official_name_raw": raw_name,
            "official_name_normalized": normalized,
            "rename_mark_in_source": "1" if raw_name.startswith("*") else "0",
            "document_name": document_name,
            "document_number": document_number,
            "document_date": document_date,
            "publication_date": publication_date,
            "valid_from_rule": valid_from_rule,
            "valid_until_rule": valid_until_rule,
            "source_url": source_url,
            "local_filename": local_filename,
            "source_pdf_page": str(page),
            "extraction_status": "程序提取_官方声明数量校验通过_抽样版面复核",
        })


def main() -> None:
    rows: list[dict[str, str]] = []

    names_2014 = pdf_section(
        RAW / "2014_monitor6.pdf", range(15, 29),
        start_after="第六次监测合格农业产业化国家重点龙头企业名单",
        stop_before="注：",
        start_occurrence=2,
    )
    add_pdf_rows(
        rows, names_2014, list_year="2014", event_type="monitor_pass",
        list_type="第六次监测合格名单",
        document_name="农业部关于公布第六次监测合格农业产业化国家重点龙头企业名单的通知",
        document_number="农经发〔2014〕9号", document_date="2014-09-01",
        publication_date="待核实", valid_from_rule="延续既有资格；监测日不是首次取得资格日",
        valid_until_rule="至后续监测、取消或其他正式资格事件更新",
        source_url="https://www.moa.gov.cn/nybgb/2014/shi/201712/P020180104776701107212.pdf",
        local_filename="2014_monitor6.pdf",
    )

    names_2016_replace = pdf_section(
        RAW / "2016_monitor7_replacement.pdf", range(28, 30),
        start_after="递补农业产业化国家重点龙头企业名单（共111家）",
    )
    add_pdf_rows(
        rows, names_2016_replace, list_year="2016", event_type="replacement",
        list_type="第七次监测递补名单（111家）",
        document_name="关于递补111家企业为农业产业化国家重点龙头企业的通知",
        document_number="农经发〔2016〕13号", document_date="2016-10-14",
        publication_date="待核实", valid_from_rule="从递补文件生效日期起取得资格",
        valid_until_rule="至后续监测、取消或其他正式资格事件更新",
        source_url="https://www.moa.gov.cn/nybgb/2016/shiyiqi/201712/P020180624662692968052.pdf",
        local_filename="2016_monitor7_replacement.pdf",
    )

    names_2018 = pdf_section(
        RAW / "2018_monitor8.pdf", range(30, 42),
        start_after="第八次监测合格农业产业化国家重点龙头企业名单",
        stop_before="注：",
    )
    add_pdf_rows(
        rows, names_2018, list_year="2018", event_type="monitor_pass",
        list_type="第八次监测合格名单",
        document_name="农业农村部关于公布第八次监测合格农业产业化国家重点龙头企业名单的通知",
        document_number="农产发〔2018〕1号", document_date="2018-11-29",
        publication_date="2018-12-05", valid_from_rule="延续既有资格；监测日不是首次取得资格日",
        valid_until_rule="至后续监测、取消或其他正式资格事件更新",
        source_url="https://xccys.moa.gov.cn/gzdt/201812/t20181205_6314544.htm",
        local_filename="2018_monitor8.pdf",
    )

    names_2019 = pdf_section(
        RAW / "2019_batch6.pdf", range(14, 19),
        start_after="第六批农业产业化国家重点龙头企业名单",
        start_occurrence=2,
    )
    add_pdf_rows(
        rows, names_2019, list_year="2019", event_type="recognition",
        list_type="第六批新认定名单",
        document_name="关于公布第六批农业产业化国家重点龙头企业名单的通知",
        document_number="农产发〔2019〕3号", document_date="2019-11-26",
        publication_date="2019-12-09",
        valid_from_rule="基准按文件落款日；稳健性按网页公开日或下一完整年度",
        valid_until_rule="有效期到2022年监测结果公布前",
        source_url="https://www.moa.gov.cn/nybgb/2019/201912/202004/P020200410023357640054.pdf",
        local_filename="2019_batch6.pdf",
    )

    names_2020_replace = pdf_section(
        RAW / "2020_monitor9.pdf", range(11, 13),
        start_after="递补农业产业化国家重点龙头企业名单",
    )
    add_pdf_rows(
        rows, names_2020_replace, list_year="2020", event_type="replacement",
        list_type="2020年递补名单（128家）",
        document_name="关于递补128家企业为农业产业化国家重点龙头企业的通知",
        document_number="农产发〔2020〕8号", document_date="2020-11-25", publication_date="待核实",
        valid_from_rule="从递补文件生效日期起取得资格",
        valid_until_rule="至后续监测、取消或其他正式资格事件更新",
        source_url="https://www.moa.gov.cn/nybgb/2020/202012/202102/P020210201587636946140.pdf",
        local_filename="2020_monitor9.pdf",
    )

    names_2020_monitor = pdf_section(
        RAW / "2020_monitor9.pdf", range(24, 40),
        start_after="第九次监测合格农业产业化国家重点龙头企业名单",
        stop_before="注：",
        start_occurrence=2,
    )
    add_pdf_rows(
        rows, names_2020_monitor, list_year="2020", event_type="monitor_pass",
        list_type="第九次监测合格名单",
        document_name="农业农村部关于公布第九次监测合格农业产业化国家重点龙头企业名单的通知",
        document_number="农产发〔2020〕6号", document_date="2020-11-20",
        publication_date="待核实", valid_from_rule="延续既有资格；监测日不是首次取得资格日",
        valid_until_rule="至后续监测、取消或其他正式资格事件更新",
        source_url="https://www.moa.gov.cn/nybgb/2020/202012/202102/P020210201587636946140.pdf",
        local_filename="2020_monitor9.pdf",
    )

    html_names_2021 = batch7_names(WORK / "2021_batch7.html")
    names_2021 = pdf_section(
        RAW / "2021_batch7.pdf", range(92, 98),
        start_after="第七批农业产业化国家重点龙头企业名单",
    )
    web_normalized = [name.replace("(", "（").replace(")", "）") for name in html_names_2021]
    pdf_normalized = [name for _, _, name in names_2021]
    if web_normalized != pdf_normalized:
        raise ValueError("Batch-7 official PDF and official webpage lists do not match in order")
    add_pdf_rows(
        rows, names_2021, list_year="2021", event_type="recognition",
        list_type="第七批新认定名单",
        document_name="关于公布第七批农业产业化国家重点龙头企业名单的通知",
        document_number="农产发〔2021〕4号", document_date="2021-12-22",
        publication_date="2022-01-13",
        valid_from_rule="基准按文件落款日；稳健性按网页公开日或下一完整年度",
        valid_until_rule="有效期到2024年监测结果公布前",
        source_url="https://xccys.moa.gov.cn/gzdt/202201/t20220113_6386872.htm",
        local_filename="2021_batch7.pdf",
    )

    names_2023_monitor = pdf_section(
        RAW / "2023_monitor10.pdf", range(7, 28),
        start_after="监测合格农业产业化国家重点龙头企业名单",
        stop_before="递补农业产业化国家重点龙头企业名单",
    )
    add_pdf_rows(
        rows, names_2023_monitor, list_year="2023", event_type="monitor_pass",
        list_type="第十次监测合格名单",
        document_name="关于公布第十次监测合格和递补农业产业化国家重点龙头企业名单的通知",
        document_number="农产发〔2023〕3号", document_date="2023-05-12",
        publication_date="待核实", valid_from_rule="继续保留资格；监测日不是首次取得资格日",
        valid_until_rule="有效期到下一次监测结果公布前",
        source_url="https://www.moa.gov.cn/nybgb/2023/202306/202307/P020230719348171286633.pdf",
        local_filename="2023_monitor10.pdf",
    )

    names_2023_replace = pdf_section(
        RAW / "2023_monitor10.pdf", range(27, 29),
        start_after="递补农业产业化国家重点龙头企业名单",
    )
    add_pdf_rows(
        rows, names_2023_replace, list_year="2023", event_type="replacement",
        list_type="第十次监测递补名单",
        document_name="关于公布第十次监测合格和递补农业产业化国家重点龙头企业名单的通知",
        document_number="农产发〔2023〕3号", document_date="2023-05-12",
        publication_date="待核实", valid_from_rule="从递补文件生效日期起取得资格",
        valid_until_rule="有效期到下一次监测结果公布前",
        source_url="https://www.moa.gov.cn/nybgb/2023/202306/202307/P020230719348171286633.pdf",
        local_filename="2023_monitor10.pdf",
    )

    expected = {
        "第六次监测合格名单": 1191,
        "第七次监测递补名单（111家）": 111,
        "第八次监测合格名单": 1095,
        "第六批新认定名单": 299,
        "2020年递补名单（128家）": 128,
        "第九次监测合格名单": 1120,
        "第七批新认定名单": 412,
        "第十次监测合格名单": 1429,
        "第十次监测递补名单": 112,
    }
    actual = {key: sum(row["list_type"] == key for row in rows) for key in expected}
    print("counts", actual)
    for key, count in expected.items():
        if actual[key] != count:
            raise ValueError(f"Count mismatch for {key}: expected {count}, got {actual[key]}")

    fields = list(rows[0])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote {len(rows)} rows to {OUT}")
    for key in expected:
        print(key, actual[key])


if __name__ == "__main__":
    main()
