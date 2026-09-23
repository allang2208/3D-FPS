# 起始检修通道与扩建房间的接口过渡

用户指出随机地图入口两侧和顶部漏空。固定 `DGN_Link_A_B` 沿用样板检修通道，净宽 1.32 m、净高 2.38 m；随机 `Threshold` 的中心线宽度为 3 m、墙厚 0.24 m，实际净宽 2.76 m、净高 3.15 m。两段开放截面直接相接导致露出场景外部。

## 本次修改

- 新资产 `/Game/Dungeons/DoorTransitions20260922/Meshes/SM_StartServiceTransition` 保留原连接件前 1.4 m 的几何和 UV，在后 2.6 m 逐步扩宽、抬高到随机连接件的真实内表面。
- 过渡包含有厚度的两侧墙、上方顶板和连续地板，沿墙延续瓷砖与踢脚。保持两端地面同高，不叠放共面的过桥地板。
- 灯具改到保留的前段，对应 `DGN_Link_InspectionLight` 同步移动。
- 只替换随机地图的该连接件和对应灯源；不重排房间，不修改旧通道母版和三房展示地图。
- `author_transition.py` 从随机模块配置读取出口实际宽高；`author_modules.py` 重建随机模块时同步制作此过渡，`integrate_assets.py` 同步导入，`install_routes.py` 同步安装。
- 模块目录补充 Transit/Threshold 的实际净宽、净高及 `start_connection` 配方，区分墙中心线宽度和通行净宽。

## 接入

可编辑源 `Authored/StartServiceTransition.blend`；配置 `Config/transition.json`。通过桥运行 `Scripts/install_transition.py` 完成单资产导入与地图局部替换，记录在 `Receipts/install.json`。

地图 `/Game/GameMaps/L_Dungeon_Randomized` 已保存。未启动 PIE、截图、渲染或游戏测试，效果由用户体验。
