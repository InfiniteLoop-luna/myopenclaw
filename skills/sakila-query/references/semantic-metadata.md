# Sakila OSM 语义能力视图

## 可用 KPI

| KPI ID | 名称 | 宿主实体 | 需要时间 | 允许的过滤字段 |
|--------|------|----------|----------|----------------|
| store_revenue | 门店收入 | Store | ✅ | store_id, district, city, country |
| total_revenue | 总收入 | Store | ✅ | store_id, city, country |
| revenue_growth | 门店收入增长率 | Store | ✅ | store_id, city, country |
| avg_payment_amount | 平均支付金额 | Store | ✅ | store_id, customer_id |
| total_rentals | 租赁总数 | Store | ✅ | store_id, customer_id, film_id, category_id |
| avg_rental_duration | 平均租赁时长 | Store | ✅ | store_id, film_id |
| overdue_rentals | 逾期未还数 | Store | ❌ | store_id |
| active_customers | 活跃客户数 | Store | ❌ | store_id |
| customer_lifetime_value | 客户终身价值 | Customer | ❌ | store_id |
| revenue_per_customer | 客均收入 | Store | ✅ | store_id |
| film_rental_count | 电影租赁次数 | Film | ❌ | category_id, rating, store_id |
| category_revenue | 分类收入 | Category | ✅ | store_id, category_id |
| inventory_utilization | 库存利用率 | Store | ❌ | store_id |
| staff_revenue | 员工收入贡献 | Staff | ✅ | store_id, staff_id |
| staff_rental_count | 员工租赁处理数 | Staff | ✅ | store_id, staff_id |

## 实体

Actor, Address, Category, City, Country, Customer, Film, FilmActor, FilmCategory, FilmText, Inventory, Language, Payment, Rental, Staff, Store, User

## 时间粒度

day, week, month, quarter, year

## IR 结构

```json
{
  "version": "1.0",
  "kpi": "<kpi_id>",
  "host": {
    "entity": "<Entity>",
    "ids": null
  },
  "time": {
    "grain": "month",
    "range": {
      "type": "relative",
      "value": "last_12_months"
    }
  },
  "filters": [
    {"field": "<field>", "operator": "=", "value": "<value>"}
  ],
  "ranking": {
    "order_by": "<kpi_id>",
    "limit": 10,
    "direction": "desc"
  },
  "options": {
    "limit": 1000
  }
}
```

## 时间范围值

relative: last_7_days, last_30_days, last_3_months, last_6_months, last_12_months, last_1_year, ytd, mtd
absolute: "2025-01-01/2025-12-31"

## filter operator

=, >, <, >=, <=, in, like
