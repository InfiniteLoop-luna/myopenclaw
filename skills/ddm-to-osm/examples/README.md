# ddm-to-osm 示例文件

本目录包含示例 DDM 文件和输出示例。

## 文件说明

### sample.ddm
一个简化的示例 DDM 文件，包含 3 个实体：
- `customer` - 客户表
- `order` - 订单表
- `product` - 产品表

### sample_output.yaml
使用 `sample.ddm` 生成的 OSM 输出示例。

## 使用示例

```bash
# 转换示例文件
python ../convert.py sample.ddm sample_output.yaml sample_db

# 查看生成的文件
cat sample_output.yaml
```

## 创建你自己的示例

如果你有 Datablau 工具，可以：

1. 创建一个简单的数据库模型
2. 导出为 DDM 格式
3. 使用本 skill 转换
4. 检查生成的 OSM 文件

## 注意

由于示例 DDM 文件较大，本目录可能不包含实际的 `sample.ddm` 文件。

你可以：
- 使用自己的 DDM 文件测试
- 或从 Datablau 官方获取示例文件
