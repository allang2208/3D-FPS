# 地图个人标记 · 2026-11-14

> 2026-11-17 归档说明：本记录中的测试/构建日期和结果为历史证据；本次整理未重新运行。地图任务的 Saved 临时目录及截图已移入 `trash/map-system-20261117/` 下的原相对路径，详见 [发布与归档清单](../Publication/MapSystem20261117/README.md)。 标记的最终共享语义与真实 UDP 结果以 [后续共享记录](map-marker-sharing-20261115.md) 为准，覆盖旧版本的“仅个人”说明。


按用户要求直接实施。地图、顶部方位条和世界光柱读取同一份本地玩家会话数据，最多共存 10 个标记。

- M 地图单击地面新增，单击已有图标或底部标签编辑；拖动仍为平移，滚轮缩放，右键也可选点。新建后输入名称、选择颜色，再保存；空名称采用“标记”。
- 名称最多 32 个 UTF-16 字符，单行。八色为金、蓝、绿、红、紫、青、橙、白。选色只作用于导航身份，玻璃底、普通文字、按钮继续使用 ColdSteelUI 共用主题。
- 底部标签横向滚动，长名称省略，悬停显示完整名称、区域与楼层。编辑区整组控件换行，不拆分按钮文字。容量提示常驻，达到上限时可继续编辑、删除已有标记。
- 编辑时使用 UIOnly 输入并单独持有移动屏蔽计数；Enter 保存、Esc 取消。M、Delete 进入文字编辑器，避免输入时误关闭地图或删除标记。结束编辑释放本次计数，恢复地图原有 GameAndUI 输入，角色可继续移动。
- 地牢选点必须命中本层已探索补丁中的实际地面。补丁保存探索时的地面高度，射线只覆盖该高度附近，并核对模块及楼层。丘陵使用实际地形高度，普通场景使用地表射线。
- 光柱从选点向上延伸 2 km，复用 M_LootBeam 和引擎 Plane，异步加载。每个有效标记一个无碰撞、无阴影、无复制的本地 Actor，仅所属玩家可见；地牢光柱只显示当前楼层。
- 方位条按世界 +X 北、+Y 东计算方向，处理 0/360 度接缝。视野外标记在两端给出转向指示；名称、距离、地牢楼层最多三排，重叠名称省略。战斗目标卡显示期间保留指示图标，名称让出其位置。
- 标记归属本地 PlayerController 会话，不与队友共享，也不新增存档字段。同一地牢实例返回主神空间后保留，重新进入恢复；新实例/布局退役清除旧地牢标记。离开区域隐藏光柱，删除/会话结束销毁光柱；世界原点变更同步平移标记。
- 更新复用菜单 0.1 秒定时器，最多处理 10 项；地形 Actor 仅在区域切换时查找，文字和标签列表按版本变化重建。HUD 不遍历场景，也不触发加载。

实施文件：ColdSteelMapMarkers、SColdSteelMapMarkerEditor、SColdSteelWorldMap、ColdSteelWorldMapData、ColdSteelDungeonMap、ColdSteelGameMenuWidget、ColdSteelHUDNavigation 及玩家控制器的只读入口。

交付边界：源码与必要后台构建；按用户规则不启动编辑器、游戏或测试。实际视觉、输入与联机效果由用户测试。

构建记录：2026-11-14，FPSGAMEEditor Win64 Development 成功，DLL 已链接落盘；FPSGAME Win64 Development 成功，目标已是最新。日志为 `Saved/Logs/MapMarkersEditorBuildFinal.log` 与 `Saved/Logs/MapMarkersGameBuildFinal.log`。未运行游戏或测试。

## 2026-11-15 光柱不可见修复

用户反馈保存标记后看不到光柱。原实现同时使用 `Spawn.Owner=PlayerController` 与 `OnlyOwnerSee`；UE 的 `LocalPlayer` 将 `GetViewTarget()` 作为 `ViewActor`，`PrimitiveSceneProxy` 仅在该视角 Actor 位于光柱拥有者链时显示光柱。正常视角为 Pawn，旧链只有光柱 Actor 和 PlayerController，因此被隐藏。

光柱现以当前 `GetViewTarget()` 为拥有者，并在原有 0.1 秒更新中只在目标变化时重新绑定，覆盖重生、占有角色变化与相机目标切换。无有效视角时隐藏光柱。标记数据仍属于原本地 PlayerController 会话，颜色、数量、楼层和探索限制保持原合同。

本次依据当前源码与引擎渲染路径定位；未启动游戏进行视觉测试。

构建记录：2026-11-15，`FPSGAME Win64 Development` 与 `FPSGAMEEditor Win64 Development` 均成功，游戏 EXE 与 `UnrealEditor-FPSGAME.dll` 已链接落盘。日志位于 `Saved/Build/MapMarkerBeamVisibility20261115/game.log`、`editor.log` 和 `editor-ubt.log`。构建期间另修正 `TemperateVegetationLiveTrace.cpp` 的首个 include 顺序，以满足 UBT 的对应头文件优先要求。用户保存并关闭 UE 后完成 Editor 构建；未重新打开编辑器，未运行游戏或测试。
