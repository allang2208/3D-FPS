# 地牢铁门与浅积水

用户于 2026-09-22 要求优化截图中的铁门材质、细节及地面积水，并借鉴已有喷泉项目。

- 配置：`Config/design.json`，沿用现有关卡位置与四处积水中心。
- 制作：Blender 后台执行 `Scripts/author_geometry.py`，输出可编辑源和两份 FBX，不渲染。
- 接入：项目互斥桥执行 `Scripts/install.py`，只替换 `DGN_AV2_MachineGrille` 与 `DGN_AV2_WetPatches` 的网格，不重建整张地图。
- 资产根：`/Game/Dungeons/AtmosphereV2/GateWater/`。
- 材质依赖：已制作的 Services 表面纹理，以及喷泉 V8 原创噪声 `OverflowV8/T_FountainFlowNoiseV8`。不修改共享喷泉资产。
- 整场景源通过工作台组合件的 `Config/surrounding-sources.json` 加入覆盖层；全图重建入口最后运行本轮接入。
- `Scripts/puddle_normal.hlsl` 使用逐像素 WorldPosition、缓慢波纹和按每滩积水分相位的滴水涟漪。
- 水材质不使用户外自发光 Cubemap、白沫或 WPO；近地面透明水膜保持地砖可见。无水面碰撞。

本轮不启动 PIE，不截图、不渲染、不执行游戏或性能测试；材质和近景表现由用户体验。详见 `Docs/Gameplay/dungeon-gate-water-20260922.md`。
