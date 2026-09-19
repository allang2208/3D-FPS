# M4 快速近战：参考重建 I（2026-09-19）

> 整理状态（2026-09-19）：本目录保留参考／作者依赖，不是当前运行母版。最终 M4 为 N；QBZ191 为 O；收势使用统一 runtime recover。完整入口见 [发布与恢复](../../Docs/Weapons/quick-melee-publication-20260919.md)。


状态：六套可编辑源、FBX 和 UE 动画已制作、导入保存，C++ 已接入，Game / Editor 正式构建完成（`build-game.log`、`build-editor.log`）。**本轮未运行游戏、渲染或测试，等待用户试用；不是已接受基线。**

## 参考与重建依据

- 用户原参考：[BV13K421e7Rw](https://www.bilibili.com/video/BV13K421e7Rw/)，1:05–1:07 的 AK47 枪托近战。
- 本机原片：`D:/FPS3D/test/uzi_ref/uzi_ref.mp4`，1280×720、30 fps。
- 本次取第二次完整挥击，66.266667–67.166667 s，0.9 s。`Reference/` 留有原生帧和提亮读谱图，不入公开仓库。
- 实际逐帧观察：枪托从画面右侧进入上半部，再向中部偏左送出；接触姿态的枪口仍朝左下。出手很快，随后有短暂受力停留，再往右收回低持。
- 原 H 版把枪口从左甩到右，与这段参考不一致。本轮按枪托位置和枪口朝向重建整枪姿态，不继续套 H 的大幅回旋参数。

`reference_motion.json` 保存参考时间、手动标注的枪托屏幕位置及三维重建参数。视频只有一个视角；深度、遮挡中的姿态和 M4 与 AK47 的形体适配属于人工重建。屏幕标注和离线相机只用于制作，不能代替 UE 实机观感，也不代表像素级或骨骼级 100% 复刻。

## 时序

| 阶段 | 动作时间 | 原片时间 | 制作意图 |
| --- | --- | --- | --- |
| 离开待机 | 0.0333 s | 66.3000 s | 枪身迅速横入前景 |
| 枪托进入右上 | 0.1000 s | 66.3667 s | 准备横向送出 |
| 接触姿态 | 0.1667 s | 66.4333 s | 枪托到中部，枪口朝左下 |
| 跟随与受力停留 | 0.2667–0.5000 s | 66.5333–66.7667 s | 小幅连续漂移，保留原片节奏 |
| 收枪 | 0.5333–0.8667 s | 66.8000–67.1333 s | 回右侧，再回原待机 |
| 结束 | 0.9000 s | 67.1667 s | 接回原待机姿态 |

接触时刻是按视频中的视觉接触姿态选择，原片未提供真实游戏命中事件数据。

## 手臂与握点

- 沿用已存在的 Base、Drum、Angled、Vertical、Canted、Prism 待机源。
- 所有 `WPN_` 骨骼、手掌和手指随同一个武器变换运动；保留各配置的握点关系。
- 肩肘用双骨求解补齐；上臂、前臂及其辅助扭转骨使用完整骨段变换。首尾平滑回到原待机肩部。
- 六套动作均烘焙 120 Hz、109 个采样姿态，FBX 不做简化。没有另加运行时武器根旋转来叠加动作。

## 文件与再制作

1. Blender 执行 `read_authoring_input.py`：读取原待机骨架和枪托几何，生成 `authoring_input.json`。
2. CPython（NumPy / SciPy）执行 `fit_reference_motion.py`：由 `reference_motion.json` 生成 `motion_frames.json`。
3. Blender 后台执行 `author_replica.py`：制作六套骨骼动作。
4. UE 编辑器 Python 执行 `import_replica.py`：沿用 M4 骨架及 `BC_M4Viewmodel`，导入、保存六个动画资产。

可编辑源：`<Profile>/M4_QuickCombat_<Profile>_Editable.blend`。

引擎导出：`<Profile>/Animations/A_M4_QuickCombat_<Profile>.fbx`。

UE 路径：`/Game/Weapons/M4QuickMeleeReplica20260919/<Profile>/A_M4_QuickCombat_<Profile>`。

`authoring.json` 是制作回执，`import.json` 是导入保存回执，均不代表运行或视觉验收。参考视频、帧图和生成的二进制仅保存在本机。

## 运行时接入

M4 使用独立资源与 0.1667 s 接触时钟；其它步枪保留原资源和时钟。伤害、距离、冷却、修炼和击退合同沿用现有快速进战技能。

M4 命中探针从枪身前段移到枪托末端，跟随当前动画的 `WPN_Root`。作者坐标点为 `(0,+0.235,+0.025)` m，导入后的 UE 骨空间为 `(0,-23.5,+2.5)` cm；采用无缩放方向变换，避免把导入骨骼缩放重复应用到厘米值。

旧 H 作者源及 `/Game/Weapons/M4StockMelee20260918` 资产仍在原处，本轮未覆盖。
