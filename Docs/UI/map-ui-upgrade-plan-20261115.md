# 地图栏审计与升级 · 2026-11-15

> 2026-11-17 归档说明：本记录中的测试/构建日期和结果为历史证据；本次整理未重新运行。地图任务的 Saved 临时目录及截图已移入 `trash/map-system-20261117/` 下的原相对路径，详见 [发布与归档清单](../Publication/MapSystem20261117/README.md)。 标记的最终共享语义与真实 UDP 结果以 [后续共享记录](map-marker-sharing-20261115.md) 为准，覆盖旧版本的“仅个人”说明。


范围为 M 地图、标记编辑与标签、缩放定位、地牢楼层及未知区域反馈。用户明确要求 Product Design 审计并直接优化；保留冷钢主题、真实底图、坐标投影、10 个个人标记、光柱颜色、移动和迷雾归属。

## 当前画面依据

使用独立 `MapUIAudit_20261115131458` 档案，在游戏模式采集，未打开编辑器。图片位于 `Saved/MapUIUpgrade20261115/`。

| 步骤 | 画面 | 观察与处理 |
| --- | --- | --- |
| 1 打开地图 | 01-before-map.png | 真实底图、主题和地标有效；缺少明确的视图状态和可点击缩放入口。 |
| 2 新建标记 | 02-before-editor.png | 表单出现压缩画布，选点发生屏幕位移；名称与颜色没有明确字段标题。改为画布内浮层。 |
| 3 保存标记 | 03-before-saved-marker.png | 标签可编辑，但第一枚标签出现也会改变画布高度；固定标签区高度，补充区域/楼层副标题。 |
| 4 缩放浏览 | 04-before-zoom.png | 白色北向与比例尺在浅色地面上不可辨；补深色衬底。增加倍率、缩放与全图操作。 |
| 5 紧凑窗口编辑 | 05-before-compact-editor.png | 960×720 下表单、标签和帮助堆在底部；改为限宽、限高、可滚动编辑浮层，保留正文档字号。 |
| 6 地牢地图 | 06-before-dungeon.png | 已探索范围外隐藏正常；缺少解释，单层按钮也看起来可切换。增加迷雾提示、明确查看层与所在层，只列已探索楼层。 |
| 7 未探索区域选点 | 07-before-unexplored-feedback.png | 拒绝选点有效，但错误挤进帮助行。反馈移到地图内的独立提示位。 |

## 实施合同

- Slate 实现，仍由 `ColdSteelGameMenuWidget` 管理生命周期；复用 `ColdSteelUIStyle` 的玻璃、边框、按钮、中文字体与数字字体。
- 顶部为标题、浏览/跟随状态、只列已探索层的下拉选择、缩放倍率、全图、定位、关闭。操作按整组重排，正文与短标签横排。
- 中部画布占据剩余空间。标记表单放在同一画布的右下浮层，最大宽度 360px、最大高度服从画布并内部滚动。编辑状态不改变画布大小；选中已有标签才主动定位该点。
- 底部标签区固定占位，空态提供选点引导；标记名和区域/楼层分别单行显示，超长名称省略并提供完整提示。
- 编辑表单明确名称、字数、颜色名称、选中边界与保存/取消动作。未完成编辑时再次选点提示先保存/取消，避免覆盖草稿。
- 地图浏览继续支持 WASD，输入名称期间沿用 UIOnly 与独立移动屏蔽计数；表单按钮可按 Tab 聚焦，Esc 取消并恢复原输入模式。关闭释放原有监听与本次控件。
- 更新沿用地图 Tick、标记版本与既有定时器；标签只在数据变化时重建，不新增全场遍历或同步资源加载。无资产、存档或联机数据结构迁移。
- 范围为 `SColdSteelWorldMap.cpp`、`SColdSteelMapMarkerEditor.h/.cpp` 及本次文档。必要构建为 Editor/Game。视觉复核限本次地图 UI；不将其称为联机或战争迷雾算法回归。

## 地图与 Buff 栏互斥显示（2026-11-15 追加）

- 打开 M 地图时，由控制器立即通知 `StatusEffectsHUDSubsystem` 隐藏左上 Buff 栏并收起悬停提示；M、Esc 和关闭按钮沿用同一关闭入口恢复。
- 仅切换本地显示，不暂停或修改状态效果。关闭地图时重新读取当前效果，已到期效果不恢复，剩余时间取当前值；空效果保持隐藏。
- 子系统保留地图开关状态，Buff HUD 延迟创建时也按该状态显示。沿用既有刷新事件和世界销毁清理，不新增 Tick 或定时器。
- 修改范围为 `FPSGAMEGameMenu.cpp`、`StatusEffectsHUD.h/.cpp`。本次仅制作与必要构建，不进行游戏测试，由用户测试。
- 构建完成：共享工程的 Game 构建 `Saved/Logs/UnknownMagicBowMobileGame20261115.log` 和 Editor 构建 `Saved/Logs/UnknownMagicBowMobileEditor20261115.log` 均为 `Succeeded`，包含本次改动。未启动编辑器或游戏测试。
- 构建期间另将 `UnknownHumanoidAnimInstance.cpp` 中与外层采样函数重名的局部 `Sample` 改为 `ActionSample`，仅消除 C4456 编译错误，计算逻辑不变。

## 任务追踪栏与地图互斥（2026-11-15 追加）

- 沿用地图开关事件，经 `ColdSteelHUDWidget` 通知 `ColdSteelDungeonTracker`：打开时隐藏整个任务追踪控件，M、Esc 和关闭按钮关闭地图时恢复。
- 恢复前读取最新任务快照并重新计算位置；完成、移除和切换阶段采用当前真实状态，空列表保持隐藏。任务推进、存档和联机数据不变。
- 修改范围为 `FPSGAMEGameMenu.cpp`、`ColdSteelHUDWidget.h/.cpp`、`ColdSteelDungeonTracker.h/.cpp`。无新 Tick、定时器或资源。本次仅进行必要构建，不启动游戏测试。
- 本次 Game、Editor 后台构建均为 `Succeeded`，日志为 `Saved/MapTaskVisibility20261115/FPSGAME-build.log` 与 `Saved/MapTaskVisibility20261115/FPSGAMEEditor-build.log`。未启动编辑器或游戏，未进行运行测试，由用户测试。

## 验证边界

基线已采集主神空间和地牢入口层。多层探索、联机同步、光柱远距表现不属于此次视觉采集的通过声明。升级后的构建与画面记录在完成时追加。
