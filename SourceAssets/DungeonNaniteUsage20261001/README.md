# 既有材质 Nanite 用途修正：当前制作源

Scripts/fix_reported_materials.py 是所报材质的定向修正入口；原材质与本机保存回执仍在本机。对应可复用导入脚本同步保留用途设置。

正式地图为 `/Game/GameMaps/L_Dungeon_Randomized`，旧独立样板已退役。先恢复合法本机模型/纹理/材质依赖；不按日期顺序重跑所有历史迁移脚本，也不伪造安装回执。

公开作者脚本、轻量参数与清单；Blend/FBX、贴图、UE 包、字体、下载源、回执和日志保留本机。`Backup` 旧快照和 `.blend1` 已按清单归档，正式 `.blend` 和仍用作上游输入的早期源保留。

制作记录：[对应房间/阶段](../../Docs/Gameplay/dungeon-publication-20261002.md)；[本轮整理与恢复边界](../../Docs/Gameplay/dungeon-publication-20261002.md)。本次整理没有启动 UE、运行游戏或渲染。
