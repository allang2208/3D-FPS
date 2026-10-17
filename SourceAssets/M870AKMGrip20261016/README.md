# M870 复用 AKM 左手握姿

后续入口：`../M870AKMArmSupport20261016/`。本目录是其整手冻结输入；肩肘支撑已经由后续版本接替。不要单独重导本目录的旧肩肘动画覆盖后续版本。

2026-10-16，按用户指定改为复用现有认可的 AKM 抓握，停止 M870 单独的拇指拟合和虎口曲面试作。

**当前状态：13 条 M870 动画已通过后台 commandlet 导入并保存。** `install_receipt.json` 记录 `completed=true` 和 13 个已保存资产，执行日志为 `install_resume.log` / `install_animations.log`。此前编辑器 PIE 导致的拦截属于历史记录，本次已完成保存。没有启动游戏或追加运行时测试，视觉效果仍由用户复测。

## 来源与适配

- 当前 AKM 原厂握姿：`/Game/Weapons/AKMIntegration/SourceMatched/A_AKM_idle`，由 `FPSGAMECharacter.cpp::LoadAKMAnimation` 的 SovietFab 分支加载。
- 对应作者源：`SourceAssets/AKMSoviet20260911/AKM_Soviet_Editable.blend` 中 `AKM_Native_idle`。
- 将左掌、四根掌骨和五指作为完整握姿迁移，以解剖掌面和原生绑定轴消除两种骨架的轴定义差异。保留 M870 原生骨长及局部骨位移，不对某一根手指重新优化。
- 对齐 AKM 护木与 M870 护木的下支撑面、握持纵向位置和指根行。之后整只手向左 10 mm、下移 3 mm 做接触微调；手指之间的旋转关系不变。
- 沿用 M870 已有泵动、装填侧转、机械轨迹、右手动作与事件时钟；肩肘按新整手握点重新接续。
- 没有应用 `M870ThumbRootSwing20261016` 中的任何表面、法线或绑定试作，也没有改 M870/Super90 的网格、权重、UV、材质或共用裸臂。

## 文件

- `read_akm.py` / `akm_grip.json`：既有 AKM 手型与枪体参考。
- `transfer_grip.py` / `transferred_grip.json`：完整握姿转移及整手接触变换。
- `author_akm.py` / `M870_AKMGrip_Editable.blend`：13 条 M870 动画及可编辑源。
- `Exports/Animations`：本轮 13 条 FBX；`authoring.json` 记录源与时长。
- `install.ps1`：现有桥批次或后台 commandlet 保存；`install_receipt.json` 为实际保存凭据，`Before/Animations` 保存替换前包。

本轮制作预览位于 `Review/`，采用简化材质，不是游戏截图。没有启动游戏或 PIE；最终游戏中的接触与观感由用户复测。
