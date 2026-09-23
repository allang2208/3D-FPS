# 原样板空间扩展返工

后续空间库：用户指出两个相同段落只证明水平拼接。当前扩展工作已转到 `SourceAssets/DungeonRoomShells20260922`，由三个不同用途的房间替换重复 B 段；本目录继续保留 A 段连接边界的作者输入与拼接修复记录。具体地图写入状态以新目录 `Receipts/install.json` 为准。

用户选择保留“原样板整体空间与氛围”。本版本保留整个已认可空间，仅变更显式连接边界。

- 输入母版：`/Game/GameMaps/L_Dungeon_Prototype`。
- 目标候选：`/Game/GameMaps/L_Dungeon_AuthoredExpansion`。
- 配方：`Config/assembly.json`，两段刚体放置与一个 4 米连接，不整体缩放。
- 模型源：`Authored/AuthoredSpace_Connections.blend`。只包含新的边界变体和短连接；原样板源不覆盖。
- 制作：Blender 执行 `Scripts/author_connections.py`。
- 接入：项目批次互斥桥执行 `Scripts/install_expansion.py`。以 `Receipts/assembly.json` 的 `map_saved` 为实际接入完成依据。
- 本次接入已保存：离线阶段完成导入和地图复制后，地图切换因 Python 持有 World 引用中断；释放引用已补入安装脚本。重启后的编辑器通过 `Scripts/resume_expansion.py` 从已有副本继续完成拼接，未覆盖原样板。
- 返工说明：`Docs/Gameplay/dungeon-authored-expansion-rework-20260922.md`。

旧 14 方房版本退回，源快照存 `trash/dungeon-generated-v1-rejected-20260922/`。新候选不沿用旧版封闭房间战斗和终端布置；现有角色与地牢存档不清空。

本次源制作不运行游戏、截图或验收渲染；由用户体验。

入口修改已完成原生编译，日志为 `build-editor-02.log`；编辑器已重开并停在扩展地图。`resume-result-01.txt` 记录本次地图保存结果。编译与保存不代表观感、通行或战斗验收。

## 用户反馈后的接入修复

用户反馈只能看到旧通道后，实际读取发现 B 段被转成了 pitch -90°，并非配方要求的 yaw -90°。两个安装脚本已改用带字段名的 Rotator；`fix_segment_rotation.py` 从未变动的 A 段恢复 B 段姿态，并显式标记、保存其 164 个外部 Actor 包。

原组合网格的体积布尔还会保留门板或引入堵口面。连接件制作改为逐面裁切开口，同时插值保留 UV 和颜色；不对原母版网格应用这一修改。`reimport_connections.py` 只重新导入六个扩展专用网格，不保存其他内容包。

主场景的 `DUNGEON / Authored Expansion` 通往本地图；`DUNGEON / Prototype` 仍是原样板。新连接位于原走廊末端，经过折角、楼梯，上平台后穿过检修门到达第二段。

反馈后的定向检查结果：独立进程重新读取地图，B 段姿态为 pitch 0°、yaw -90°，地面顶面为 94 cm；42 cm 半径／96 cm 半高的 Pawn 胶囊扫掠在三处连接均无阻挡。见 `Receipts/saved-connection-collision.json`。未进行完整走图或视觉、战斗验收。
