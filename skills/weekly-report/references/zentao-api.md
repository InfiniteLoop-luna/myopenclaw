# 禅道数据获取参考

## 登录

浏览器打开禅道 URL，填入用户名密码，点击登录。登录信息在 TOOLS.md 中。

## JSON 接口

禅道页面 URL 末尾加 `.json` 即可获取 JSON 数据。需要先在浏览器中登录获取 session。

### 获取由我解决的 Bug

页面: 贡献 → Bug → 由我解决
URL: `/biz/my-contribute-bug-resolvedBy-0-id_desc-{total}-{perPage}-{page}.json`

返回结构:
```json
{
  "status": "success",
  "data": "{\"bugs\": {\"id\": {\"id\", \"title\", \"resolvedDate\", \"resolution\", \"severity\", \"product\", ...}}}"
}
```

注意: data 字段是二次 JSON 编码的字符串，需要 `JSON.parse(JSON.parse(resp).data)`。

### 获取由我完成的任务

页面: 贡献 → 任务 → 由我完成
URL: `/biz/my-contribute-task-finishedBy-0-id_desc-{total}-{perPage}-{page}.json`

### 按日期过滤

接口不支持日期参数，需要在客户端按 `resolvedDate` / `finishedDate` 字段过滤。

```javascript
const weekStart = '2026-02-24';
for (const [id, bug] of Object.entries(bugs)) {
  if (bug.resolvedDate && bug.resolvedDate >= weekStart) {
    // 本周解决的 bug
  }
}
```

### 翻页

URL 中最后一个数字是页码。如果总数超过 perPage，需要多次请求。
建议 perPage 设为 100 减少请求次数。

## 日期计算

- 周报: 取本周一 ~ 周五
- 日报: 取当天
- 周一 = 当前日期 - (weekday) 天
