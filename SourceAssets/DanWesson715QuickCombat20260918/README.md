# DW715 快速进战·握把砸击（2026-09-18）

用户 2026-09-18 决定：手枪快速进战的动作改走**作者源路线**（不再用运行时程序化姿态层）。
本目录是这条线的作者源与导入记录，基座是 `DanWesson715PalmClearance20260915` 的可编辑源。

## 文件

- `author_actions.py`：打开掌面避让版可编辑源 → 以 `DW715_idle` 为基准 → 逐帧 120 Hz 烘焙
  `DW715_quickcombat` → 导出 `Animations/A_DW715_quickcombat.fbx` → 存 `DanWesson715_QuickCombat_Editable.blend`。
- `animation.json`：动作表（各段偏移/枪口角/偏航）、接触时间与导出去向。
- `import_assets.py`：以现有骨架 `SK_DW715_Manny_Skeleton` 导入到
  `/Game/Weapons/DanWesson715/QuickCombat20260918/Animations`，压缩设置沿用 `BC_M4Viewmodel`。
- `import.log`：导入记录（`DW715_QUICKCOMBAT_IMPORT_COMPLETE`，读回 `length=0.6000`）。

## 动作（0.60s，接触 0.30s）

| 时间 | 段 | 内容 |
| --- | --- | --- |
| 0.00–0.06 | 起手 | 左手松握离把（手指向静止姿态混合 35%），枪口始抬 24° |
| 0.06–0.18 | 蓄势 | 枪根后上（后 9cm / 上 12cm），枪口上仰 **82°**，右肘外上支撑，躯干偏航 7° |
| 0.18–0.21 | 保持 | 约 3 帧顶点保持 |
| 0.21–0.30 | 下砸 | 枪根前下（前 14cm / 下 9cm），枪口回到 **58°**，右肘前下压，偏航 10° |
| 0.30–0.42 | 跟随 | 惯性带出（前 19cm / 下 13cm），枪口 50° |
| 0.42–0.60 | 回握 | 左手回握（松握权重回 0），整段回待机 |

左手：锚点先随枪 0.06s，之后固定在空间里下垂（左 7cm / 后 8cm / 下 26cm，出镜），
段落结束回握；枪口与左手都按表插值（`smooth/accel/decel`）。

## 作者约定

- **枪的运动写在 `WPN_root` 上，右手由握把关系带动**：`hand_at(p, idle, 'r', G @ RIGHT_GRIP)`，
  与这把枪的换弹 clip 同一约定（换弹也是把持枪运动烘焙到 `WPN_root`）。
- 左手用同一解算器（原骨长、肩带可前送、肘极可偏移）。
- **关键不变量**：`|WPN_root − hand_r| = 0.133 m` 全程恒定（`author_actions.py` 末尾逐帧打印自检），
  即"枪不跟手"这类问题在作者源层面不可能出现。

## 运行时接线

- `FPSGAMECharacter`：`EAKMWeaponState::QuickCombat` + `QuickCombatAnimation`
  （`/Game/Weapons/DanWesson715/QuickCombat20260918/Animations/A_DW715_quickcombat`），
  由 `TriggerPistolQuickCombat()` 播放；单发动作结束走既有 `FinishWeaponAction()`。
- `FPSQuickCombatComponent`：只保留命中射线（起点=握把底）、冷却、修炼与命中镜头冲量。
- 运行时程序化姿态层 `ApplyQuickCombatPose` 已整段删除（含其诊断代码）。

## 未做

未实机测试、渲染或验收，由用户测试。制作脚本里的关键帧读数只用于作者源自检，
不代表视觉/手感合格。
