---
name: weekly-report
description: "生成周报/日报。从禅道项目管理系统获取本周/指定时间段解决的 Bug、完成的任务，自动生成 .docx 格式的工作报告。Use when: 用户要求写周报、日报、工作总结、生成工作报告。NOT for: 非工作报告类的文档生成。"
---

# 周报/日报生成

从禅道获取工作数据，生成 .docx 格式的工作报告。

## 前置条件

- 禅道登录信息在 TOOLS.md 中（URL、用户名、密码）
- 需要 python-docx 库（`pip install python-docx`）

## 流程

### 第 1 步：登录禅道

用 browser 工具打开禅道登录页面，输入 TOOLS.md 中的账号密码登录。

### 第 2 步：获取工作数据

登录后导航到「贡献」页面获取数据。

**获取已解决的 Bug：**

1. 导航到 贡献 → Bug → 由我解决
2. 通过浏览器内 JS 调用禅道 JSON 接口获取带解决日期的数据：

```javascript
// 在浏览器内执行，获取由我解决的 Bug 列表（含 resolvedDate）
const resp = await fetch('/biz/my-contribute-bug-resolvedBy-0-id_desc-{recTotal}-100-1.json', {credentials: 'include'});
const data = JSON.parse(await resp.text());
const parsed = JSON.parse(data.data);
const bugs = parsed.bugs || {};
// 按日期过滤
const weekStart = 'YYYY-MM-DD'; // 本周一日期
const thisWeek = [];
for (const [id, bug] of Object.entries(bugs)) {
  if (bug.resolvedDate && bug.resolvedDate >= weekStart) {
    thisWeek.push({id: bug.id, title: bug.title, resolvedDate: bug.resolvedDate, resolution: bug.resolution});
  }
}
```

**获取已完成的任务：**

类似方式，导航到 贡献 → 任务 → 由我完成，用 JSON 接口获取。

### 第 3 步：生成 .docx 报告

调用 `scripts/gen_report.py` 生成报告。

```bash
python <skill_dir>/scripts/gen_report.py --type weekly --date 2026-02-28 --data '<json_data>'
```

参数说明：
- `--type`: weekly（周报）或 daily（日报）
- `--date`: 报告日期，用于文件命名和目录创建
- `--data`: JSON 格式的工作数据

### 第 4 步：输出

报告按日期存放在独立目录中：

```
workspace/reports/
  └── 2026-02-28/
      └── weekly_report_2026-02-28.docx
```

## 注意事项

- 生成报告时按日期创建单独目录存放（`reports/YYYY-MM-DD/`）
- 禅道 JSON 接口路径格式：`/biz/{页面路径}.json`，需要先在浏览器中登录获取 session
- Bug 数据中 `resolvedDate` 字段用于按时间过滤
- 如果数据超过 100 条，需要翻页获取（修改 URL 中的页码参数）
- 周报默认取周一到周五的数据，日报取当天数据
- 设置环境变量 `PYTHONIOENCODING=utf-8`
