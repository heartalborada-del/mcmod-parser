# mcmod-parser

解析 Minecraft mod 元数据（modId, version, displayName 等）的 Python 库与 CLI 工具。

支持加载器: **Forge**, **NeoForge**, **Fabric**, **Quilt**

## 安装

```bash
pip install mcmod-parser
```

## CLI 使用

### parse — 解析单个文件

```bash
mcmod-parser parse jei-1.20.1-15.2.0.27.jar             # 从 JAR
mcmod-parser parse META-INF/mods.toml                     # 从元数据文件
mcmod-parser parse jei.jar -o table                       # 表格输出
mcmod-parser parse mod.jar -o csv -f info.csv             # 导出 CSV
```

### scan — 批量扫描目录

```bash
mcmod-parser scan ./mods/                                 # JSON 输出
mcmod-parser scan ./mods/ -o table                        # 表格
mcmod-parser scan ./mods/ -o csv                          # CSV
mcmod-parser scan ./mods/ -o csv -f mods.csv              # 导出到文件
mcmod-parser scan ./mods/ -o csv -f                       # -f 自动命名
mcmod-parser scan ./mods/ -r -l fabric                    # 递归 + 仅 Fabric
```

### diff — 比较两个目录

```bash
mcmod-parser diff old_mods/ new_mods/                     # 彩色差异
mcmod-parser diff old_mods/ new_mods/ --no-color          # 无颜色
mcmod-parser diff old_mods/ new_mods/ -r -f diff.txt      # 递归 + 导出
mcmod-parser diff old_mods/ new_mods/ -l forge            # 只比较 Forge
```

**输出格式：** `json` | `table` | `text` | `csv`

**通用选项：**

| 选项 | 简写 | 说明 |
|------|------|------|
| `--output` | `-o` | 输出格式（parse/scan） |
| `--output-file` | `-f` | 导出到文件；`-f` 单独使用自动命名 |
| `--loader` | `-l` | 按加载器过滤 |
| `--recursive` | `-r` | 递归扫描子目录（scan/diff） |
| `--no-color` | | 禁用颜色输出（diff） |

## API 使用

```python
from mcmod_parser import parse_jar, scan_directory, ModInfo, LoaderType

# 解析单个 JAR
mods = parse_jar("jei-1.20.1-15.2.0.27.jar")
for mod in mods:
    print(mod.mod_id, mod.version)

# 扫描目录
results = scan_directory("./mods/")
for mod in results:
    print(f"{mod.loader_type.value}: {mod.mod_id}@{mod.version}")

# 访问元数据
mod = results[0]
print(mod.display_name)       # 显示名称
print(mod.description)        # 描述
print(mod.authors)            # 作者列表
print(mod.license)            # 许可证
print(mod.dependencies)       # 依赖列表
print(mod.to_json_dict())     # JSON 序列化
```

## ModInfo 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `mod_id` | `str` | mod 唯一标识 |
| `version` | `str` | 版本号（占位符自动回退到文件名） |
| `loader_type` | `LoaderType` | forge / neoforge / fabric / quilt |
| `display_name` | `str` | 显示名称 |
| `description` | `str` | 描述文本 |
| `authors` | `Authors` | 作者列表（统一格式化） |
| `license` | `str` | 许可证 |
| `dependencies` | `list[DependencyInfo]` | 依赖项 |
