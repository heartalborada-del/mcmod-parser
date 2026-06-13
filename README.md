# mcmod-parser

解析 Minecraft mod 元数据（modId, version, displayName 等）的 Python 库与 CLI 工具。

支持加载器: **Forge**, **NeoForge**, **Fabric**, **Quilt**

## 安装

```bash
pip install -e .
```

## CLI 使用

```bash
# 解析单个 JAR 文件
mcmod-parser parse jei-1.20.1-15.2.0.27.jar

# 扫描 mods 文件夹
mcmod-parser scan ~/.minecraft/mods/

# 输出为表格
mcmod-parser scan ./mods/ --output table

# 输出为 CSV
mcmod-parser scan ./mods/ --output csv

# 导出到文件
mcmod-parser scan ./mods/ --output csv --output-file mods.csv

# 递归扫描 + JSON 输出到文件
mcmod-parser scan ./mods/ --recursive --output json -f result.json
```

## API 使用

```python
from mcmod_parser import parse_jar, scan_directory

# 解析单个 JAR
mods = parse_jar("jei-1.20.1-15.2.0.27.jar")
for mod in mods:
    print(mod.mod_id, mod.version)

# 扫描目录
results = scan_directory("./mods/")
for mod in results:
    print(f"{mod.loader_type.value}: {mod.mod_id}@{mod.version}")
```
