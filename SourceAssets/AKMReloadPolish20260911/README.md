# AKM 换弹细节修正 — 2026-09-11

握把换弹末段后续改为直接回握，最新专用握把换弹引用与验证见 [AKM Grip Return](../AKMGripReturn20260911/README.md)。本记录的食指、弹鼓脱手及预览显示修正继续保留。

## 后续：原厂弹匣在作者预览中重叠

用户反馈后发现，Blend 作者预览把原厂弹匣保留在枪身网格中，又显示了独立弹鼓；UE 使用的材质分区隐藏并不会自动作用于 Blender。已将作者预览的原厂弹匣独立为 `AKM_FactoryMagazine_Preview`，保留原权重和骨骼，弹鼓分支同时关闭渲染与视口显示。标准弹匣分支仍正常显示。

`preview_visibility.py` 统一此规则，接入安装、握把动作、换弹精修三套生成脚本；`fix_preview_visibility.py` 修复了 31 个现有作者文件，验证总面数未变化，结果见 `preview_visibility_validation.json`。游戏动作 FBX 与已导入动画不需要重烘焙，本次没有更改姿态或换弹时序。

实机此前侧面回放未复现原厂弹匣叠加；新增运行检查现在会在弹鼓普通/空仓换弹的每个采样点验证全部 LOD 的原厂弹匣分区保持隐藏。复核日志 `runtime-akm-mag-visibility-v1.log`；对比图 `Delivery/magazine-visibility-fixed.jpg`。

修复用户指出的右手食指前伸，以及弹鼓尚未拔出就飞离枪身的问题。保留已接受的模型、配件安装、手模、总换弹时长和装弹结果。

## 原因与调整

原 AKM 弹鼓飞出事件在 60 Hz 事件时钟的第 25/26 帧触发，相当于 120 Hz 源动画第 50/52 帧。实测弹匣骨骼在第 60 帧前仍与枪体固定，所以事件先于拔出动作。原弹鼓动作直接复用标准弹匣动作，未独立匹配脱手时间。

- 全部 12 条换弹变体（原握姿、棱镜握把、斜握把，各含普通/空仓及弹鼓普通/空仓）将 `index_01_r` 至 `index_03_r` 保持为已接受 AKM 待机的自然弯曲。骨长、权重、手指平移和缩放保持原值。
- 弹鼓前段采用单调三次时间映射：新源帧 `[0,44,56,86,106,120]` 对应原源帧 `[0,44,60,72,100,120]`。完整动作一起重定时，保留左手和弹鼓的同步抓握，延长可见拔出过程。
- 新源帧 78–90 渐渐松指，98–112 回到原取弹姿态；脱手事件改为源帧 86（60 Hz 事件帧 43）。UE 压缩读回显示：帧 64 已拔离约 6.9 cm，帧 76 约 16.3 cm，帧 86 约 24.9 cm。
- 弹鼓脱手后的侧向速度由 180 降至 85 cm/s，向下初速度由 110 调为 140 cm/s，以自然下落为主。M4 的事件和抛掷速度保持原值。
- 拔匣音效改至源时间 0.5 秒，经现有 `ReloadRuntimeTime` 映射到运行时。插入、压实和拉栓的接触及声音时点保持原样。
- 源帧 120 之后，除右手食指外完全恢复原动作。基础时长仍为 3.333333 / 4.291667 秒，弹鼓继续使用既有倍率。

## 资产与重建

新候选及当前实际加载路径：`/Game/Weapons/AKMIntegration/SovietFab/ReloadPolish/{base,prism,angled}`。原接入资产留存，便于对照。

`build.py` 从已接受源文件重建 12 条独立 Blend/FBX；`import.py` 导入，`verify_ue.py` 在独立 UE 进程读取压缩动作。运行引用位于 `FPSGAMECharacter.cpp`、`M4HandstopVisual.cpp`、`M4AngledForegrip.cpp`；脱手事件位于 `M4DrumVisual.cpp`。

## 验收

- `build-preview.log`：原生模块编译成功。
- `ue_validation.json`：12 条压缩资产通过。食指相对待机最大角差约 0.029°；弹鼓回到原时间轴后的关键骨骼位置差低于 0.02 cm 阈值。
- `runtime-akm-polish-prism-v1.log`、`runtime-akm-polish-angled-v1.log`：普通、空仓、弹鼓普通、弹鼓空仓及回握/装备，0 失败。新增断言验证“可见拔出 → 脱手”，并检查完成装弹及原弹匣隐藏。
- `runtime-akm-polish-side-v2.log`：侧面实机复核与实际混音录制。
- `Delivery/first_person_drum_normal.mp4`、`first_person_drum_empty.mp4`、`side_drum_normal.mp4`、`side_drum_empty.mp4`：实际运行截图按游戏时间配合同次 UE 混音，不是配音。采集为变帧率，缺少采样的时间段沿用前图，间隔记录在 `capture-report.json`；源和压缩姿态另以 120 Hz 检查。

测试均使用独立审计存档，没有改写玩家背包。旧编辑器进程须重启才会加载新原生模块；已验证的是新启动的测试进程。
