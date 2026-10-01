# 三条主题路线：当前制作源

Scripts/author_freight_link.py / import_assets.py 制作货运单向衔接；Config/warehouse-module.json 为认可仓库，Config/catalog.json 为当前目录镜像。Scripts/extend_catalog.py 叠加主题与已安装坡道并限制货运专用资格；安装前需真实本机导入回执。

正式地图为 `/Game/GameMaps/L_Dungeon_Randomized`，旧独立样板已退役。先恢复合法本机模型/纹理/材质依赖；不按日期顺序重跑所有历史迁移脚本，也不伪造安装回执。

公开作者脚本、轻量参数与清单；Blend/FBX、贴图、UE 包、字体、下载源、回执和日志保留本机。`Backup` 旧快照和 `.blend1` 已按清单归档，正式 `.blend` 和仍用作上游输入的早期源保留。

制作记录：[对应房间/阶段](../../Docs/Gameplay/dungeon-themed-routes-20261001.md)；[本轮整理与恢复边界](../../Docs/Gameplay/dungeon-publication-20261002.md)。本次整理没有启动 UE、运行游戏或渲染。
