# 故障排除

## 常见问题和解决方案

### 安装问题

#### 问题：pip install pyyaml 失败

**症状**：
```
ERROR: Could not find a version that satisfies the requirement pyyaml
```

**解决方案**：
1. 检查 Python 版本：`python --version`（需要 >= 3.7）
2. 升级 pip：`python -m pip install --upgrade pip`
3. 使用国内镜像：`pip install pyyaml -i https://pypi.tuna.tsinghua.edu.cn/simple`

#### 问题：Windows 控制台乱码

**症状**：
```
���� DDM �ļ�: sakila.ddm
```

**解决方案**：
已在 `convert.py` 中自动处理，如果仍有问题：
1. 使用 PowerShell 而不是 CMD
2. 设置控制台编码：`chcp 65001`
3. 使用 Git Bash 或 WSL

---

### 解析问题

#### 问题：解析 DDM 文件失败

**症状**：
```
❌ 解析失败: not well-formed (invalid token)
```

**可能原因**：
1. DDM 文件不是有效的 XML 格式
2. 文件编码不是 UTF-8
3. 文件损坏

**解决方案**：
1. 用文本编辑器打开 DDM 文件，检查是否是 XML 格式
2. 检查文件开头是否有 `<?xml version="1.0"?>` 或 `<File>`
3. 尝试用 Datablau 重新导出 DDM 文件

#### 问题：解析到 0 个实体

**症状**：
```
✅ 解析到 0 个实体
```

**可能原因**：
1. DDM 文件格式不是 Datablau LDM
2. DDM 版本不兼容

**解决方案**：
1. 检查 DDM 文件中是否有 `Datablau.LDM.EntityComposite` 对象
2. 运行调试命令：
   ```bash
   python -c "import xml.etree.ElementTree as ET; tree = ET.parse('your.ddm'); root = tree.getroot(); print([obj.get('Type') for obj in root.findall('.//Object')][:10])"
   ```
3. 如果对象类型不同，请联系开发者适配

#### 问题：外键关系解析不正确

**症状**：
```
✅ 解析到 17 个实体
  - customer (客户信息表): 9 个属性, 0 个外键  # 应该有外键
```

**可能原因**：
1. DDM 文件中没有 `RelationshipRelational` 对象
2. 关系定义不完整

**解决方案**：
1. 检查 DDM 文件中是否有关系定义：
   ```bash
   python -c "import xml.etree.ElementTree as ET; tree = ET.parse('your.ddm'); root = tree.getroot(); rels = root.findall('.//Object[@Type=\"Datablau.LDM.RelationshipRelational\"]'); print(f'找到 {len(rels)} 个关系')"
   ```
2. 如果没有关系，在 Datablau 中重新定义外键关系
3. 如果有关系但解析失败，运行 `python scripts/ddm_parser.py your.ddm` 查看详细错误

---

### 生成问题

#### 问题：生成的 OSM 文件中关系为空

**症状**：
```yaml
relations: []
```

**可能原因**：
1. 实体没有外键关系
2. 外键解析失败

**解决方案**：
1. 检查原始 DDM 文件中是否定义了外键
2. 查看转换输出中的"外键数"是否为 0
3. 如果外键数为 0 但实际有外键，参考上面的"外键关系解析不正确"

#### 问题：生成的 KPI 太少

**症状**：
```
✅ 生成完成:
  - KPIs: 3  # 期望更多
```

**原因**：
本 skill 只为有时间字段的实体生成基础 count KPI。

**解决方案**：
1. 这是正常的，基础 KPI 只是起点
2. 手动编辑生成的 YAML 文件，添加业务相关的 KPI
3. 参考 `docs/OSM_CONCEPTS.md` 中的 KPI 定义示例

#### 问题：语义类型推断不准确

**症状**：
```yaml
amount:
  semantic_type: attribute  # 应该是 currency
```

**原因**：
语义类型是基于字段名启发式推断的。

**解决方案**：
1. 手动编辑生成的 YAML 文件，修改 `semantic_type`
2. 如果经常遇到，可以修改 `scripts/osm_generator.py` 中的 `_infer_semantic_type` 方法

---

### 运行问题

#### 问题：ModuleNotFoundError: No module named 'yaml'

**症状**：
```
ModuleNotFoundError: No module named 'yaml'
```

**解决方案**：
```bash
pip install pyyaml
```

#### 问题：Permission denied

**症状**：
```
PermissionError: [Errno 13] Permission denied: 'output.yaml'
```

**解决方案**：
1. 检查输出文件是否被其他程序打开
2. 检查是否有写入权限
3. 尝试输出到其他目录

#### 问题：File not found

**症状**：
```
❌ 错误: DDM 文件不存在: sakila.ddm
```

**解决方案**：
1. 检查文件路径是否正确
2. 使用绝对路径：`python convert.py C:\path\to\file.ddm output.yaml db`
3. 确保文件扩展名是 `.ddm`

---

### 输出问题

#### 问题：生成的 YAML 文件无法被 OSM 编译器读取

**症状**：
```
yaml.scanner.ScannerError: mapping values are not allowed here
```

**可能原因**：
1. YAML 格式错误
2. 特殊字符未正确转义

**解决方案**：
1. 使用 YAML 验证工具检查文件：https://www.yamllint.com/
2. 检查是否有特殊字符（如 `:`, `#`, `|`）在字符串中未加引号
3. 重新生成文件

#### 问题：Join Graph 边数为 0

**症状**：
```
✅ 生成完成:
  - Join Graph 边: 0
```

**原因**：
没有外键关系，因此没有 join 边。

**解决方案**：
1. 参考"外键关系解析不正确"部分
2. 如果确实没有外键，这是正常的

---

### 性能问题

#### 问题：解析大型 DDM 文件很慢

**症状**：
解析超过 1 分钟

**原因**：
DDM 文件很大（>100MB）或实体很多（>1000 个）

**解决方案**：
1. 这是正常的，XML 解析本身较慢
2. 考虑拆分 DDM 文件
3. 使用更快的 XML 解析器（需要修改代码）

---

### 兼容性问题

#### 问题：在 Linux/Mac 上运行失败

**症状**：
路径相关错误

**解决方案**：
1. 使用正斜杠 `/` 而不是反斜杠 `\`
2. 或使用 `pathlib.Path` 处理路径（代码中已使用）

#### 问题：Python 2.x 不兼容

**症状**：
```
SyntaxError: invalid syntax
```

**原因**：
本 skill 需要 Python 3.7+

**解决方案**：
升级到 Python 3.7 或更高版本

---

## 调试技巧

### 1. 启用详细输出

修改 `convert.py`，添加调试信息：
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 2. 单独测试解析器

```bash
python scripts/ddm_parser.py your.ddm
```

### 3. 检查 DDM 文件结构

```bash
python -c "import xml.etree.ElementTree as ET; tree = ET.parse('your.ddm'); root = tree.getroot(); types = set([obj.get('Type') for obj in root.findall('.//Object')]); print('\n'.join(sorted(types)))"
```

### 4. 验证生成的 YAML

```bash
python -c "import yaml; data = yaml.safe_load(open('output.yaml', 'r', encoding='utf-8')); print('✅ YAML 格式正确'); print(f'实体数: {len(data[\"ontology\"][\"entities\"])}')"
```

---

## 获取帮助

如果以上方法都无法解决问题：

1. **检查文档**：
   - `SKILL.md` - 详细使用说明
   - `docs/OSM_CONCEPTS.md` - OSM 概念
   - `docs/DDM_FORMAT.md` - DDM 格式说明

2. **查看示例**：
   - `examples/` - 示例文件
   - `EXAMPLE.md` - 使用示例

3. **运行测试**：
   ```bash
   python test.py
   ```

4. **联系开发者**：
   - 提供 DDM 文件的前 100 行（去除敏感信息）
   - 提供完整的错误信息
   - 说明你的环境（操作系统、Python 版本）

---

## 已知限制

1. **不支持视图**：EntityView 暂不支持
2. **不支持存储过程**：StoredProcedure 暂不支持
3. **复杂关系**：多对多关系需要手动调整
4. **自定义类型**：特殊数据库类型可能映射不准确
5. **大文件**：超大 DDM 文件（>100MB）解析较慢

这些限制将在未来版本中改进。
