# M1911 / Dan Wesson 715 双持

当前握姿迭代为 [NaturalAimV3：自然握姿与准星汇聚](pistol-dual-natural-aim-20260915.md)，取代 ReferencePoseV2 的固定 18° 内转；奔跑动作当前使用 [SprintSmoothV5：流畅度修订](pistol-dual-sprint-smoothness-20260915.md)，保留 [SprintReferenceV4](pistol-dual-sprint-reference-20260915.md) 的抬枪与跑停方向。预览角色初始化修复见 [崩溃修复记录](pistol-dual-wield-preview-crash-20260915.md)。以下保留各阶段的制作记录。

实现于 UE 宿主 `D:/FPS3D/FPSGAME`。用户选择：鼠标左右键分别开火，双持取消 ADS。开发、动画导出、导入和必要构建完成后交由用户测试；本任务不运行 PIE、游戏测试、截图或验收渲染。

## 使用

在同组主手／副手装备两把手枪：主手 1 配副手 1，或主手 2 配副手 2。支持两把 M1911、两把 715，以及两种枪混搭。

- 左键：右手主枪；右键：左手副枪。每次按下各发一枪，两键可同时按下。
- R：两侧分别为未满枪补弹。一侧换弹时，另一侧仍可开火。
- 双持没有 ADS；卸下副手或换成其他主武器后恢复原单持流程。
- 各枪保留自己的弹匣／弹巢、枪匠配件、伤害、射速、强化与附魔。备弹来自背包，同口径共享弹药池，异口径分别消耗。无限备弹沿用当前场景开发选项。
- HUD 主手为原大号弹量，副手另列名称、口径、弹量和备弹；两侧换弹／空仓颜色独立。

## 参考与制作

参考 [用户指定视频 BV1PExtzNEBS](https://www.bilibili.com/video/BV1PExtzNEBS/)：7–10 秒的握姿和射击，9–12、35–37 秒的双枪换弹，12–14、31–34 秒的奔跑。开头的检视花式动作没有当作换弹使用。视频仅用作动作分析，未将视频、音频或其中游戏资产导入 Content。

持枪分列画面下方，奔跑左右错相摆臂；开枪各自抬腕后坐、套筒／击锤运动、枪口火光、烟雾和枪声。换弹采用抬枪退匣／退壳、压低到腰部装填、回正的顺序，装填阶段采用画外动作。715 长逐发换弹的抬枪时刻由最后一发接触时刻决定；快速装弹器保留原先清空弹巢再装填的规则。

源资产复用当前获准使用的 M1911、715 与 Manny 手臂。每侧导出对应的真实左右臂网格，枪体保持原有几何方向，不做负缩放。手指握姿、全上臂／前臂／扭转骨及腕部一同制作。缺少多视角的部分属于三维重建，不是视频动画数据的精确提取。

## 接入

`UPistolDualWieldComponent` 管理两份装备实例、半自动触发边沿、独立后坐／换弹时钟和动画。左手沿用现有施法手臂求解，施法时隐藏副枪及附件，主枪继续可用。左右附件各自绑定该枪机械骨骼；消音器出口、激光和手电使用各自枪体的接口。

装填在实际弹匣就位／逐发入膛时，通过现有存档事务扣除备弹并写入对应实例。弹道在发射时记录该枪附魔和技能效果，不读取之后换上的主枪。已有存档里手枪的旧 `isTwoHanded` 值由装备规则兼容，物品实例和占格不变。

主要文件：

- `Source/FPSGAME/Weapons/PistolDualWieldComponent.{h,cpp}`、`PistolDualWieldCombat.cpp`
- `Source/FPSGAME/UI/ColdSteelDualPistolRuntime.cpp`、`ColdSteelAmmoReadout.cpp`
- `SourceAssets/PistolDualWield20260914/author_dual.py`、`import_dual.py`
- 可编辑源：`SourceAssets/PistolDualWield20260914/{M1911,DW715}/{r,l}/*_Dual_Editable.blend`
- 引擎资产：`Content/Weapons/PistolDualWield20260914/{M1911,DW715}/{r,l}`

`import.json` 记录完整导入，`reload-import.json` 记录 715 装填收尾更新。导入器对纯动画 FBX 提示绑定姿势回退；本任务没有通过运行或渲染认定视觉结果，握持接触、摆幅与实际手感留给用户测试。

## 本次交付记录

- 完整源资产导出及首次导入完成；715 更新导入记录已写入 `reload-import.json`。更新命令行进程因 HTTP 插件占用本机 8000 端口返回 1；日志错误为 `HttpListener unable to bind to 127.0.0.1:8000`，动画导入与保存步骤已执行。
- 编辑器关闭后，普通 `FPSGAMEEditor Win64 Development` 最终构建完成，日志为 `SourceAssets/PistolDualWield20260914/build-final.log`。
- 未运行测试、PIE 或视觉验收。需重新打开工程使用更新后的 DLL 和动作资产。

## 2026-09-15 参考握姿修订（ReferencePoseV2）

用户反馈整体方向正确，但手臂位置与方向不自然。本次按同一参考视频中下方两侧露出手、腕和短前臂的构图调整，保留原有 Manny 手臂、手套、两种枪械网格与机械动作。

- 独立设置左右肩位及肘部弯曲方向，替换沿用单持姿态的肘部方向。肩位展开到各自一侧，肘部朝外下方；上臂、前臂保持原长，前臂扭转骨分摊握腕转动。
- 握位横向由每侧 16 cm 调至 18.5 cm，高度由相机下方 20 cm 调至 19.2 cm。枪和握持手整体内转 18°、轻倾 3°，保持手指与枪柄的相对接触。
- 奔跑左右相差半周期，加入前后与上下交替，肩、肘带有较小的跟随摆动；不再让左右手同时按二倍频上下跳动。
- 射击时肘肩吸收一部分后坐；换弹与装备时肩肘跟随下沉。M1911 普通／空仓、715 逐发／装弹器等所有动作回到新的共同握姿，机械轨道和装填时间沿用原动作。

制作参数为 `SourceAssets/PistolDualWield20260914/ReferencePoseV2/pose_profile.json`；可编辑 Blend 和动画 FBX 位于同目录下的 `{M1911,DW715}/{r,l}`。`author_dual.py` 当前生成此版本，UE 用 `import_dual.py -DualPoseUpdate` 导入到原武器目录下的 `ReferencePoseV2/Animations`，运行组件读取这一动作目录；已接入的骨骼网格与材质继续复用。

本次只完成制作、导入与必要构建，不启动游戏、PIE、测试或验收渲染。最终画面与手感由用户测试；参数是依据单视角参考制作的三维姿态，不是从原视频提取的骨骼动画。

本版制作结果：

- M1911、715 两侧动作及可编辑源导出完成；UE 动画导入进程返回 0，记录在 `ReferencePoseV2/import.json` 与 `import-ue.log`。
- `FPSGAMEEditor Win64 Development` 最终构建成功，记录在 `ReferencePoseV2/build.log`。为解除编译阻塞，将 `WolfMonster.cpp` 中 `TSubclassOf` 的三元表达式改为显式 `.Get()`，`TObjectPtr` 数组循环改为引用写法。
- 用户保存并关闭的编辑器留下了已退出但仍映射 DLL 的进程。旧 DLL 保留在 `Saved/BuildEditor/DualPoseV2-20260915-001720/UnrealEditor-FPSGAME.dll`，新 DLL 已按正式模块名构建到 `Binaries/Win64`。构建使用与项目脚本相同的普通 Build.bat 参数，并通过进程的 `HasExited` 状态排除已退出的残留记录。
- 未运行测试或视觉验收，重新打开工程后由用户测试。
