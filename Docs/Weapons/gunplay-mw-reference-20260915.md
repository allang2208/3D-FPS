# COD 风格 gunplay 参考与首轮移动表现优化

日期：2026-09-15。当前宿主：`D:/FPS3D/FPSGAME`，UE 5.8.2。

本轮读取 `ue5-weapon-workflow`、`ue5-fps-arms-animation`、Gunplay 与 M4 基线引用、`ue5-cpp-gameplay`，并搜索 GitHub、阅读下面列出的项目源码及作者说明。最贴近需求的具体实现集中在 MW2019 与 MWII（2022）社区模组；这不是 COD16 到 COD22 每代的官方源码研究，也不能用模组参数代表原作内部实现。

## 有价值的项目

| 项目 | 实际内容与值得参考的部分 | 在本工程的使用方式 |
| --- | --- | --- |
| [ARC9-COD2019](https://github.com/Seulyy/ARC9-COD2019) | Garry's Mod 的 MW2019 武器包。M4 分别定义腰射/ADS 视觉后坐力、连射修饰、冲刺姿态、中间点与冲刺动画。 | 参考动作分层与状态关系，不导入其 COD 模型、动画、声音。 |
| [ARC9-MW22](https://github.com/Seulyy/ARC9-MW22) | MWII（2022）武器包，README 标记 WIP，依赖 ARC9 与 MW2019 包。M4 明确有 `sprint_in`、`sprint`、`sprint_out` 和 `SprintMidPoint`。 | 参考进入/循环/退出的分工；本轮只修改已有 UE 持枪姿态的程序过渡。 |
| [ARC-9](https://github.com/necoarctic/ARC-9) | 上述模组的 Lua 基础框架。镜头、视模位置、惯性、真实后坐力与视觉后坐力各有独立入口；支持围绕锚点的惯性旋转。 | 优先学习层与层之间的权重、坐标空间和状态职责，不复制整个框架。 |
| [UE5-CrystalRecoil](https://github.com/CrystalVapor/UE5-CrystalRecoil) | UE 原生后坐力曲线编辑器、抬升/回正、玩家压枪补偿与扩散组件。项目标明 MIT。 | 后续需要可编辑弹道曲线时可评估；本轮没有安装插件或替换现有枪匠后坐力公式。 |
| [ProceduralFPSAnimationsPlugin](https://github.com/gerlogu/ProceduralFPSAnimationsPlugin) | UE4/5 的曲线与数据驱动持枪摆动，项目 LICENSE 为 MIT；README 的更新说明为 2022-09-10。 | 适合参考曲线作者流程；尚未做 UE 5.8 兼容性测试。 |
| [KINEMATION 示例工程](https://github.com/kinemation/scriptable-animation-system) | Unity 的 FPS Animation Framework 示例；README 要求另行导入框架包。[镜头抖动说明](https://kinemation.gitbook.io/scriptable-animation-system/recoil-system/camera-shake)可用于理解视觉层。 | 它是示例工程，不能据此宣称完整商业框架已开源。 |

### 已读具体源码

- [MW2019 M4](https://github.com/Seulyy/ARC9-COD2019/blob/main/lua/weapons/arc9_cod2019_ar_m4.lua)：`VisualRecoil*`、`VisualRecoilDoingFunc`、`SprintMidPoint`、`SprintPos/Ang`、冲刺动画映射。
- [MW22 M4](https://github.com/Seulyy/ARC9-MW22/blob/main/lua/weapons/arc9_mw22_ar_m4.lua)：不同的视觉后冲参数与冲刺进/出动画；素材署名列出 Infinity Ward/Sledgehammer Games/Activision。
- [ARC9 镜头](https://github.com/necoarctic/ARC-9/blob/main/lua/weapons/arc9_base/cl_camera.lua)：速度、开镜权重控制 bob；相机附件动画与程序反馈分开处理。
- [ARC9 视模](https://github.com/necoarctic/ARC-9/blob/main/lua/weapons/arc9_base/cl_vmposition.lua)：移动姿态、开镜、惯性锚点与冲刺中间点。
- [ARC9 参数入口](https://github.com/necoarctic/ARC-9/blob/main/lua/weapons/arc9_base/shared.lua)、[后坐力实现](https://github.com/necoarctic/ARC-9/blob/main/lua/weapons/arc9_base/sh_recoil.lua)：实际后坐力与视觉后坐力的职责、条件修饰和曲线。

这些文件通过公开网页/raw 源码阅读；未执行第三方代码、未下载 COD 二进制素材。ARC9 和 COD 武器包未在本轮确认可用于独立商业游戏的完整许可。新 C++ 使用本项目已有弹簧与脚步接口独立实现；上述项目仅作机制参考。

## 当前代码依据

修改前，角色镜头用独立的 8/12 rad/s 时钟，M4 冲刺用独立的 1.65 Hz 速度时钟，普通步枪 bob 又使用另一时钟。手枪已由 `UFPSFootstepAudioComponent::GetStridePhaseRadians()` 驱动。镜头幅度随 `bIsSprinting` 直接切换，步枪没有起步/急停的速度滞后层。

当前开火表现已具有枪型参数、首发/连射脉冲、分段回稳与高倍镜收敛。本轮保留这些近期实现，先补移动表现。

## 本轮接入

实现：`Source/FPSGAME/Weapons/FPSGAMECharacterLocomotion.cpp`；角色声明和调用在 `FPSGAMECharacter.h/.cpp`。

1. **共用脚步节奏**：镜头、步枪行走与 M4 冲刺读取已有脚步距离相位，左右接触对应同一个周期；停止、腾空、滑铲、闪避、翻越时淡出移动摆动。
2. **镜头步态**：脚落地时轻微下沉，侧向幅度收小；补低幅俯仰和横移侧倾。步行/冲刺幅度用连续权重过渡，仍由 `CameraMotionScale` 控制，ADS 减弱。
3. **步枪惯性**：世界空间速度与滞后速度的差驱动枪体的轴向/横向位移及轻微转动。起步略滞后，急停后回稳；静止转头不会凭空产生平移惯性。使用工程已有解析阻尼弹簧。
4. **M4 冲刺过渡**：保留当前 35° 抬枪端点及手臂与枪体的完整装配，给过渡增加小幅中间位移与平滑权重，行进弧线与脚步对齐。
5. **动作占用**：换弹、装备、检视、施法、翻越、闪避时衰减新增步枪惯性；射击时降低其权重，完全 ADS 时归零。切枪重置新增惯性缓存。手枪的现有烘焙冲刺资产与双持逻辑沿用。

只增加本地角色表现状态，没有新增 UObject、RPC、存档字段、逐帧射线或资源导入。伤害、射速、弹药、散布、控制器后坐力公式、冲刺转开火时长与换弹接触时间沿用。

### 调整入口

- `RifleLocomotionScale`：新增步枪行走摆动、呼吸和移动惯性幅度，默认 1。
- `M4SprintMidpointOffset`：冲刺过渡中点的附加相机空间位移，默认 `(-1.5, -0.5, -1.0)` cm；首尾归零。
- `M4SprintOffset`、`M4SprintRotation`、`M4SprintSwayCM`：原有抬枪端点和冲刺侧摆。
- `CameraMotionScale`：已有镜头移动表现幅度。

## 后续值得制作的动作

真正的单手竖枪战术冲刺需要单独制作手臂、放开左手、循环与重新回握，不能只旋转现有双手持枪网格便称为完成。适合在当前双手冲刺基础上另做动作候选。开火镜头可进一步研究短促旋转脉冲、玩家压枪后的回正边界，但应与当前弹道/枪匠公式分开设计。

## 交付状态

本轮为程序表现实现及源码研究，没有制作或替换新的骨骼动作。未启动游戏、预览、截图、运行回归或进行视觉验收；手感与画面由用户测试。

通过 `Tools/Build/Build-Editor.ps1` 完成必要原生构建，`FPSGAMEEditor Win64 Development` 返回 `Result: Succeeded`。日志：`Saved/BuildEditor/build-20260915-123219.log`。构建包含新增移动表现源文件及角色调用；这不代表视觉或手感验收通过。

## 12:39 启动崩溃的后续诊断

用户报告 `InitializeFoldingSights()` 第 36 行访问违规。已读取现有日志和构建记录，没有启动游戏复现。

- 崩溃发生于 `BeginPlay -> InitializeWeaponVisuals -> InitializeFoldingSights`，尚未执行 Tick 中新增的移动表现函数。第 36 行包含组件设置、瞄具组件数组 Add 和安装变换数组 Add，不能只凭源码行号认定具体哪一个操作失败。
- 本轮给 `AFPSGAMECharacter` 增加成员，改变了后续成员的原生内存偏移。
- `Saved/Logs/WeaponDamage20260915Build.log` 的另一次构建与这些编辑交叉进行：编译角色时已经读到新调用，却报告找不到 `UpdateLocomotionPresentation`、`GroundLocomotionWeight` 等新增声明；同轮编译了 `M4FoldingSights.cpp`。该构建失败。
- 本任务随后进行增量构建并返回成功，但没有重新编译所有使用角色头文件的翻译单元。
- `Saved/Logs/WeaponDamage20260915BuildRetry.log` 随后只执行三个链接/元数据动作，生成 `UnrealEditor-FPSGAME-9150901.dll`，并更新模块清单。
- 用户编辑器是 12:38 新启动的进程，日志确认从启动时就加载 `9150901` 模块。因此不能简单归咎于用户没有重启编辑器，也不能仅凭模块后缀断言发生了进程内热重载。

综合判断：**高度怀疑编辑与构建交叉后，新旧角色布局的目标文件混合链接，导致初始化访问错误成员地址**。这是本轮角色结构修改触发的构建一致性问题；尚未通过 minidump 逐指令分析或运行复现最终确认，不能把构建成功写成崩溃已消失。

保留原模块、PDB、模块清单和交叉构建日志于 `Saved/CrashModuleEvidence/gunplay-20260915-123920/`；原崩溃目录 `Saved/Crashes/UECC-Windows-F704229842D2A9BF1A949895D6837D22_0000/` 保留。修复处理使用引擎 `-Rebuild -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles` 完整重建 Editor 目标，重新生成全部目标文件及普通模块。没有给瞄具函数添加掩盖错误内存布局的空指针跳过逻辑。

完整重建执行 155 个动作并返回 `Result: Succeeded`，其中角色、新增移动表现、瞄具源文件均重新编译。完整控制台记录：`Saved/BuildEditor/gunplay-crash-rebuild-20260915.console.log`。未运行游戏，崩溃是否消失由用户重新打开工程测试。
