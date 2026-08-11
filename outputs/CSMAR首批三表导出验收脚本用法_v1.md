# CSMAR首批三表导出验收脚本用法

脚本：`scripts/audit_csmar_first_batch_exports.py`
映射模板：`config/csmar_first_batch_mapping.template.json`

## 使用步骤

1. 原样保留CSMAR导出的资产负债表、利润表和现金流量表CSV/XLSX。
2. 复制映射模板为本次下载专用JSON，根据三个文件的**实际表头**填写逻辑字段对应的列名。不要照抄论文、网页示例或常见CSMAR代码。
3. 执行：

```bash
python3 scripts/audit_csmar_first_batch_exports.py \
  --balance /path/to/balance.csv \
  --income /path/to/income.xlsx \
  --cashflow /path/to/cashflow.csv \
  --mapping /path/to/filled_mapping.json \
  --codes outputs/RESSET候选股票代码146只_每行一个_v1.txt \
  --output-dir analysis/csmar_first_batch_audit
```

支持CSV、TXT、XLSX和XLS。CSV依次尝试UTF-8-SIG和GB18030；分隔符默认自动识别，也可在JSON的各表配置中填写`delimiter`。Excel默认读取第一个工作表，可用`sheet_name`指定表名或从0开始的序号。

## 脚本做什么

- 列出原始表头和行列数；
- 审计会计期间是否在2012-12-31至2023-12-31且均为12月31日；
- 审计证券代码是否为六位数字，统计146只入口代码的覆盖、缺少和意外代码；
- 原样统计报表类型、合并/母公司口径、单位字段的值分布；
- 统计公司—年度重复键并单独输出，但绝不自动删除；
- 只在报告中输出键、计数和分类值，不读取、计算或披露财务数值。

输出包括：

- `audit_report.md`：可读报告；
- `audit_summary.json`：完整结构化结果及分类值分布；
- `audit_checks.csv`：逐项PASS/WARN/FAIL；
- `duplicate_company_year_keys.csv`：重复公司—年键及行数；
- `missing_expected_codes.csv`：每张表缺少的入口代码；
- `unexpected_codes.csv`：格式正确但不在入口池的代码。

退出码为0表示没有FAIL（可能仍有WARN），1表示审计发现FAIL，2表示输入、映射或依赖错误。发现FAIL时原始文件仍不会被修改。

## 表头空表测试

仓库包含无公司、无数值、只有说明性表头的测试夹具。以下命令只验证脚本能读取三种表头并解析映射，不将零行判断为失败：

```bash
python3 scripts/audit_csmar_first_batch_exports.py \
  --balance tests/fixtures/csmar_first_batch_headers/balance_sheet.csv \
  --income tests/fixtures/csmar_first_batch_headers/income_statement.csv \
  --cashflow tests/fixtures/csmar_first_batch_headers/cashflow_statement.csv \
  --mapping tests/fixtures/csmar_first_batch_headers/mapping.json \
  --codes outputs/RESSET候选股票代码146只_每行一个_v1.txt \
  --output-dir /tmp/csmar_header_audit \
  --header-only
```

夹具中的中文列名只是测试脚本映射机制的逻辑名称，不代表CSMAR真实字段代码或本校页面表头。

## 验收边界

脚本不会判断某个“报表类型值”是否等于合并年报，因为数据库实际编码尚未核实。它先完整报告值分布，由研究者结合本次下载的数据字典确认后，再固定允许值。脚本也不会把缺少的代码或空值补成0，不会从公司名称推断证券代码，不会在三表之间自动选择或合并记录。
