# SVD / PKM 快速近战调整（2026-09-24）

**当前修订：** 用户认可本版枪体动作后反馈腕臂扭曲与 SVD 右手脱离后握把。后续修复已在 [ArmRepairV2/README.md](ArmRepairV2/README.md) 记录，十条修正动画已保存至相同运行路径。本文件以下保留首次轨迹调整的历史记录；当前腕臂作者源和导入回执以 `ArmRepairV2` 为准，先前源约束测量不构成蒙皮或游戏视觉通过的结论。

用户指定：SVD 手、手臂穿模，动作需要微调；PKM 几乎看不到枪托攻击。按手臂 SKILL 的固定本枪握点、整臂支撑、收势交接方法制作，范围仅为两枪原厂与 vertical / canted / prism / angled 的十条 `quick_melee`。

交付状态：十条动画已由后台 commandlet 导入并保存到下述原运行路径，全部长度约 0.9 s；完整保存回执见 `import_receipt.json`。原包已逐项备份，十套 Blend / FBX 已落盘。没有启动交互编辑器或游戏，没有修改 C++。

## 当前检查依据

- `runtime_before.json` 从已有 UE 编辑器读取当前实际动画资产及导入源，包含对应 idle 和压缩姿态。读取时没有 PIE、目标动画没有未保存改动。
- SVD 使用 `SVDHandRepair20260923` 的当前近战与五类 idle；PKM 使用 `PKMLowpoly20260922/Melee24`。早期退役的 Meshy PKM 不在本次范围。
- `inspection_before.json` 是当前作者源测量，`Review/before_*` 是源模型检查图，不是游戏截图。SVD 右肘在击打段抬到枪体／瞄具附近；PKM 枪托位于源坐标 y≈0.067 m、z≈-0.060 m，动作被压在第一人称画面下方。

## 制作

- SVD 调整整枪中段倾斜和位置，右肩／肘向外支撑，前臂避开机匣、瞄具和枪托区域。保留本枪与本握把的掌心矩阵、整组指骨局部姿态。
- PKM 重写收枪、翻转、枪托前送、缓冲与回收位置；击打段枪托前移、抬高，并保持枪托后端领先。左右肩分别提供外侧与后侧支撑，避免左肘过度折叠。
- 整枪、机械件、双手共同移动，完整大小臂和 twist 骨另行解算。先拟合腕部／可达性／粗略枪体避让，再进行刚性可达范围投影，禁止拉长手臂追握点。
- 240 Hz 烘焙；首末帧回到各自当前 idle。0.9 s 时长、1/6 s 命中、伤害、声音、冷却、已有视模收势交接均保持原合同。
- 回收时先同步衰减整枪拟合修正和肩臂支撑，末段接回本枪 idle；限制回收期机匣向镜头上浮，避免为了迁就仍未退回的肩位把枪拉到近裁剪面。
- 没有修改骨架参考姿态、蒙皮、枪械网格、材质、换弹、冲刺或 C++。

## 文件与运行路径

1. `prepare.py`：读取当前作者源的骨架、握点及旧近战轨迹。
2. `fit_motion.py`：两枪独立轨迹与腕肘拟合，输出 `motion.json` / `design.json`。可追加 `SVD/base` 等键只处理指定分支。
3. `author.py`：输出十个可编辑 `*_QuickMelee.blend` 和 `Animations/{SVD,PKM}/*.fbx`。
4. `run_import.ps1` / `import_animations.py`：同一批次互斥下，有编辑器时使用现有 MCP 桥，无编辑器时使用后台 commandlet。保留目标动画的骨架、压缩与 root-motion 设置，备份原包，仅导入并保存十条近战。

运行路径保持不变：

- SVD 原厂：`/Game/Weapons/SVDDragunov20260922/Complete20260923/Animations/A_SVD_quick_melee`。
- SVD 握把：`/Game/Weapons/SVDDragunov20260922/Accessories20260923/Animations/A_SVD_<family>_quick_melee`。
- PKM 原厂：`/Game/Weapons/PKMLowpoly20260922/Animations/A_PKM_quick_melee`。
- PKM 握把：`/Game/Weapons/PKMLowpoly20260922/Accessories14/Animations/<family>/A_PKM_<family>_quick_melee`。

`authoring.json` 记录实际导出；`import_receipt.json` 只记录成功导入且保存的资产。导入前原包在 `Before/Weapons/`，不覆盖已有恢复备份。导入成功不等于视觉或游戏手感验收。

## 检查与边界

本次检查是用户明确要求的局部动作检查：源模型画面、握点、手指局部姿态、骨段长度及起止归位。`review_source.py` 和 `inspect_baked.py` 为这次检查保留，后续不默认运行。源预览使用代码中的腰射／动作锚点近似构图，不包括 UE 的第一人称渲染、镜头冲击、实时混合和改造枪托。

最终十条烘焙源的逐帧测量记录在 `baked_source_inspection.json`：枪根相对掌心最大位置差约 0.0027 mm、指骨局部位置差小于 0.0004 mm、大小臂骨长差小于 0.001 mm、首末帧与各自 idle 最大位置差小于 0.001 mm。上述浮点量级结果仅证明源骨架约束，不能作为 UE 压缩、表面无穿模或游戏验收的结论。

未启动交互编辑器、PIE 或游戏，未做运行时回归。开始时用已有编辑器读取当前引用；保存阶段编辑器已关闭，最终通过无界面 commandlet 完成导入保存并正常退出，无需 C++ 编译。最终游戏视觉和手感由用户测试。Blend / FBX / 测量数据与第三方模型依赖留本机，沿用原资产许可，不作公开再分发声明。
