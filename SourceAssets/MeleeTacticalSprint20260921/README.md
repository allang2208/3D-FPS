# 近战战术冲刺：右上持剑 V1

2026-09-21 整理：已替代的动画输出及临时源码／编译快照按清单移到 `trash/melee-sprint-retired-20260921/SourceAssets/` 对应路径。当前为 V4 六条移动片段 + V5 两条0.25秒前摇攻击片段；下文旧输出位置与瞬发说明保留为历史。V4作者与导入入口已限定移动片段。详见 `Docs/Weapons/melee-publication-20260921.md`。

后续用户反馈已形成 V2：最新制作源和安装记录见 `../MeleeTacticalSprintRearCarry20260921/README.md`。本目录保留 V1 作者文件；运行中的同名8条动画已更新为 V2。

按2026-09-21用户确认的设计制作。概念与参考见 `Docs/Weapons/melee-tactical-sprint-design-20260921.md`；本目录保留制作源，不覆盖原待机、走动和下劈动画。

## 动画

普通柄与长柄各有四条120Hz动画：

| 片段 | 长度 | 用途 |
| --- | --- | --- |
| SprintEnter | 0.20秒 | 从原握姿抬至右上方，剑身转为水平向前 |
| SprintLoop | 76/120秒 | 两步一轮的轻微起伏，保持双手固定握柄 |
| SprintExit | 0.20秒 | 回落至原待机握姿 |
| SprintOverhead | 源长2.60秒，运行从1.22秒开始 | 高位持剑直接下劈，于源时间1.31秒接回当前V5落点和收势 |

高位握持目标中心在视模右侧23.5cm、前方31.5cm、眼线上方7.5cm，整体持握根据左右臂展共同回投，不拉长手臂。保留原手型和武器相对双掌的矩阵；肩肘分别求解，前臂旋转沿既有蒙皮辅助骨分布。两种握柄分别读取当前已安装姿态，保留实际握距。

可调项见 `motion.json`。普通柄和长柄各自的 `Sword_TacticalSprint_Editable.blend` 内包含四个动作；`*_keys.json` 为完整可编辑骨轨道。导入时另导出每条动作的FBX。

## 制作与接入

1. `capture_inputs.py` 通过项目桥读取当前两种握柄的Idle和Overhead源轨道，供实际制作使用，没有执行游戏测试。
2. `author_sprint.py` 在Blender生成两套候选。它复用现有UE/Blender骨坐标标定和现有蒙皮分布，不执行旧作者脚本的制作入口。
3. `import_sprint.py` 经 `Tools/AssetPipeline/mcp_call_codex.ps1` 的批次互斥创建新资产、写入轨道、保存并导出FBX；记录于 `import_receipt.json`。
4. 新资产分别位于两套原动画目录下的 `TacticalSprint20260921`。源码 `RuneSwordSprint.cpp` 负责进入、循环和退出；握柄适配仍由现有装备动画目录选择。

冲刺姿态不占用攻击输入，也不改速度、体力或技能准备时长。停止冲刺从当前可见姿态过渡；攻击可以直接打断。现有100ms持握约束入场混合用于不同步相／动作的交接，不为伤害时钟增加等待。大旋风仍使用自己的原入场时钟。

冲刺攻击仍使用1.22–1.40秒源时间接触窗、前方60°扇区、一次命中去重与原收势。来自高位持剑时选择新SprintOverhead视觉片段，运行从1.22秒直接开始，首次攻击Tick即可判定；其他来源继续使用原Overhead。新动画可用时不再叠加旧奔跑视模的下移和22°滚转。

## 交付边界

本轮不主动启动PIE、运行测试、截图或验收渲染。概念图不代表实际游戏表现。骨架制作、UE保存与原生构建结果分别记录；实际握姿、视野遮挡与手感由用户测试。

### 制作与编译记录

- 两套Blend、完整骨轨道及8条UE动画/FBX已完成。桥回执 `import-sprint-01.txt` 与 `import_receipt.json` 记录8条新动画均已保存，原有动作资产未覆盖。
- 运行逻辑已接入 `RuneSwordSprint.cpp`，并修改 `RuneSwordComponent.cpp/.h`、`RuneSwordDashAttack.cpp`、`RuneSwordMeshComponent.cpp/.h`。没有新增对象字段或反射属性；冲刺过渡复用既有持握约束混合。
- 当前编辑器原先未启用Live Coding；通过引擎自带 `LiveCoding` 控制台命令只在当前会话启用，没有修改持久偏好设置。随后构建被 `LiveCodingLimitError` 拦截：128个动作超过100项上限。回执 `compile-live-02.txt`。没有强制结束当前编辑器或修改全局构建上限。
- 使用UBT实际响应文件和MSVC工具链，在本目录独立输出4个对象文件：`RuneSwordComponent.cpp`、`RuneSwordDashAttack.cpp`、`RuneSwordMeshComponent.cpp`、`RuneSwordSprint.cpp`，结果成功，见 `compile-only.log`。这不等于已链接或加载新的游戏模块。
- 用户关闭编辑器并要求继续后，已完成常规构建与 `UnrealEditor-FPSGAME.dll` 链接，结果 `Succeeded`，日志 `Saved/BuildEditor/build-20260921-125243.log`。重新打开编辑器即可加载新模块；未启动编辑器或运行游戏测试。
- 首次常规构建被弹药图标的返回类型错误阻塞：`MakeShared` 生成的 `TSharedRef<FSlateBrush>::Get()` 返回引用，而函数需要指针。仅将 `ColdSteelAmmoPresentation.cpp` 对应返回改为 `&Brush.Get()` 后完成构建，未改变图标行为。
