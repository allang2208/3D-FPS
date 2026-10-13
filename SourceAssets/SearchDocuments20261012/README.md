# 文件材料收集品源资产

四件写实收集品的模型、纹理与 UE 资源已制作并安装，正式目录已绑定背包占格和透明图标。详见 [交付索引](../../Docs/Art/search-documents-models-20261012.md)。

- `Authored`：保留分件、倒角与法线修改器的 Blender 源文件。
- `Export`：FBX 游戏网格与带 PBR 材质的 GLB；FBX 包含 UCX 简单碰撞。
- `Textures`：BaseColor、ORM、Normal 原始 PNG 图集。
- `Previews`：用户要求的实际模型预览，共八张图片。
- `inventory_icons.json`：四张透明背包图标和占格；PNG 位于 `Content/ColdSteelData/Icons/SearchDocuments20261012`。
- `Scripts`：纹理制作、模型制作、稀有度修改、UE 导入及安装脚本。
- `UEImportHost`：使用同版本 UE 5.8 的独立内容导入工程。
- `Receipts`：导出、UE 导入、资源安装和必要构建记录。
- `Before`：本任务修改前的相关文件副本。

`model_manifest.json` 描述模型与文件；`delivery.json` 描述实际交付状态。后续重导入请遵循项目后台开发和资产互斥规则；`install_staged.py` 是首次安装脚本，遇到已存在目标会停止，不覆盖主工程资产。
