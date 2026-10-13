# 检修搜索物源资产

五件检修材料的可编辑模型、PBR、游戏导出和透明背包图标。详见 [交付索引](../../Docs/Art/search-maintenance-models-20261012.md)。

- `Authored`：Blender 分件源文件。
- `Export`：FBX、带材质 GLB。
- `Textures`：BaseColor、ORM、Normal 源图集。
- `Scripts`：模型、纹理、图标制作与目录接入脚本。
- `UEImportHost`：同版本 UE 5.8 后台内容导入工程。
- `Receipts`：导出、导入、安装、接入和必要构建结果。
- `Before`：本次相关文件修改前副本。

`model_manifest.json` 记录模型，`inventory_icons.json` 记录透明图标与占格，`delivery.json` 记录最终状态。当前配方用途仍按 V2 设计表维护；制作消耗和容器搜索池留待对应玩法接入。
