# 其他步枪应用 M4 N 版自然腕臂近战

> 收尾（2026-09-19）：用户在后续 recover 修正后确认成功结束。以下为制作时记录；最新版本、有效依赖与归档位置见 [发布与恢复](../../Docs/Weapons/quick-melee-publication-20260919.md)。


**后续修正：QBZ191 的五条运行动画已由 [O 版后握把接触修复](../QBZ191QuickMeleeGrip20260919O/README.md) 接管。下文及本目录的 QBZ191 作者文件是 N 版历史输入；重新发布 QBZ191 应使用 O 版导出/导入入口，不能直接重导入本目录的旧 FBX。AKM、ASH-12 不受影响。**

用户要求将 M4 N 版扩展到其他枪械。本轮按其他步枪范围制作 AKM、QBZ191、ASH-12；关于两把手枪的范围问题尚未收到答复，不改动已接入的 M1911 / DW715 握把砸击动作。

## 覆盖

| 枪型 | 独立作者动画 | 运行配置 |
| --- | --- | --- |
| AKM | Base、Angled、Vertical、Canted、Prism | 弹鼓共用 Base，与现有待机及冲刺一致 |
| QBZ191 | Base、Angled、Vertical、Canted、Prism | 弹鼓共用 Base，与现有待机及冲刺一致 |
| ASH-12 | Base | 当前枪匠只提供瞄具、弹匣、枪口，沿用基础抓握 |

共 11 条独立动画。现有 M4 的六条 N 版动作不重写。

## 作者输入与适配

- 运动来源：`../M4QuickMeleeRefine20260919N/Base/M4_QuickCombat_Base_Editable.blend`，109 个 120 Hz 采样，0.9 s，接触 0.1667 s。
- AKM/QBZ 的当前抓握源沿用 `../RifleTacticalSprint20260915/source-poses.json` 中逐枪逐握把的已接入待机；ASH-12 使用 `../ASH1220260917/ASH12_Editable.blend` 的 `ASH12_idle`。
- 每把枪从自己的待机姿态开始和结束，保留原手指形状、枪械机械骨关系及网格。M4 的绝对掌位和枪根坐标不直接写到其它枪上。
- 枪托参考轨迹按各枪自身后端表面点调整，再由双臂可达范围限制整体运动；ASH-12 无托布局的后端距枪根明显不同，因此单纯复用右手位移不足以保持同样的打击位置。
- 握把转轴先表示到 M4 原抓握手掌空间，再通过各枪自己的右手待机抓握映射回枪根空间；以此执行 N 的整手换向和右肘/前臂求解。
- 手掌换向后整组右手手指同步变换，保持各指相对手掌的抓握；辅助骨随完整骨段分配扭转。双臂肩部支撑和可达限制复用 K 方法。
- 起势、收势沿用 0.10 s 淡入、0.72–0.8667 s 淡出，结束恢复各自待机。

这些是制作方法和参数说明，不是新枪的效果验收结论。按本轮默认工作规则，没有渲染、运行游戏或追加测试。

## 运行接入

- 资产：`/Game/Weapons/RifleQuickMelee20260919/<Weapon>/<Profile>/A_<Weapon>_QuickCombat_<Profile>`，骨架取每把枪当前实际使用的网格，AKM 使用原精度压缩设置，其余使用 M4 视模压缩设置。
- `FPSGAMECharacter.cpp` 按 AKM/M4/QBZ191/ASH12 分别选择动作，避免共享标志 `bUsingM4Infima` 将 QBZ/ASH 当成 M4。弹鼓和 ASH 配置按上表映射。
- 四把步枪共用参考动作时钟：0.9 s 总长、1/6 s 接触。技能冷却、伤害、击退、眩晕、音效和输入门槛不在本轮修改范围。
- `QuickCombatRifleMotion.h` / `FPSCastingMeshComponent.cpp` 的命中探针使用各枪枪托表面点，跟随当前 `WPN_root`。单位为不再应用骨缩放的 UE 厘米：AKM `(0.107212,-28.872550,1.638935)`，QBZ191 `(0.072809,-20.850360,5.925570)`，ASH12 `(0.343015,-45.591554,-4.261902)`。M4 沿用原点位。

## 文件与恢复

- `author_rifles.py`：读取上述源动作并制作 11 条动画；依赖保留的 K `arm_support.py` 与 N `natural_wrist.py`。
- `<Weapon>/<Profile>/*_Editable.blend`、`Animations/*.fbx`：可编辑源与动画导出。
- `authoring.json`：每条动作的来源、路径、握把轴和各枪枪托点。
- `import_rifles.py`、`import.json`：导入脚本与保存回执。
- 修改前的三个 C++ 快照已归档到项目 `trash/quick-melee-retired-20260919/SourceAssets/RifleQuickMelee20260919/Before/`，仅作定点恢复参考；共享文件不得整份覆盖回退。旧 QBZ191 Blend 仍为 O 的作者输入，保留在本目录。

11 条作者源和 FBX 已制作，11 条 UE 动画已导入保存。主项目导入启动遇到 AutoFootstep 类重复注册，改用 `ImportHost/RifleMeleeImport.uproject` 的 Python/EditorScripting 最小宿主完成；其 Content 目录连接到实际项目 Content，仅写入本轮独立动画目录。

本任务的完整构建请求曾被 `Tools/Build/Build-Editor.ps1` 的占用保护拦住；随后确认项目中的并行完整构建已产生 19:34:59 的正式 `UnrealEditor-FPSGAME.dll`，晚于本次三个源码文件的 19:33:24 修改时间，当前编辑器进程 92280 已加载该正常文件名 DLL。追加 Live Coding 编译于 19:38:49 成功返回“no code changes detected”，UBT 结果 Succeeded。记录见 `integration.json` 与 `live-coding-ubt.log`。

11 条动画已保存，运行代码已进入正式 DLL，当前编辑器的资产注册表也已同步新增目录。未测试，由用户实机试用。
