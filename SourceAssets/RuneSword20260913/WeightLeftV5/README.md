# 双手符文剑 WeightLeftV5

本轮要求：增加挥砍镜头反馈，参考 GitHub 第一人称近战方案，挥砍双臂适当前伸，延长蓄力并增加停顿，待机展示剑身左侧。

## 动作与外观

- 沿用 V4 缩小后的剑体，保持相对 V3 的 0.8 倍大小、五路贴图及正式手臂材质。待机剑长轴角从 65° 翻到 115°，以 90° 刃线方向为界展示另一侧剑面。
- 剑体全部姿态增加 50° 长轴旋转，同时左右抓握局部矩阵反向补偿 50°，保持手掌和手指的既有朝向。继续使用 Manny 原骨架、网格、权重及 V4 连续肩肘解算。
- 基础攻速下起势 0–0.30 s，固定蓄力姿态 0.30–0.38 s，快速横扫 0.38–0.495 s，收势至约 0.983333 s。快速段仍为 0.115 s，保留相对 V2 的 2× 播放速度。
- 蓄力末端减速至停止。停顿段固定剑柄、双手及肩肘支撑，避免剑停住而手臂继续换握。快速段前 35 ms 平滑前送，双手最大额外前伸 6 cm，横扫后用 0.20 s 平滑撤去前送。
- 两条攻击继续使用左右不同的 160° 横扫轨迹。剑气两张弧面网格按更新后的剑刃轨迹重做，运行接触窗、音效、剑气启动时间和物品攻速描述同步。
- 六条动作以 240 Hz 烘焙；可编辑源为 `AzureRunesword_Manny_Editable.blend`，导出在 `Export/`。停顿由作者动作实现，未使用全局时间缩放。

## 镜头

`URuneSwordComponent::GetCameraMotion` 根据同一攻击时间给出局部位置和角度，角色 `UpdateCamera` 与现有镜头反馈组合，受现有 `CameraMotionScale` 控制。

- 起势向后 1.4 cm，向起势侧 0.9 cm，轻微抬头和侧倾；停顿期保持该目标。
- 快速挥砍向前、向挥砍方向位移，同时转向并侧倾。方向角约 1.45°、侧倾约 1.3°，快速段另有被包络限制的轻微振动。
- 收势用指数衰减和余弦回弹返回中立；镜头位置沿用角色已有平滑。
- 实际造成伤害时，每斩首次命中触发一个 0.20 s 内衰减的额外冲击。扫中多个目标仍按原方式结算，镜头冲击不逐目标叠加。取消攻击、卸装、禁用操作和结束时移除反馈。
- 镜头旋转合成到显示朝向，玩家控制旋转不被累积改写。武器仍随现有相机挂接关系运动。

## GitHub 参考

2026-09-13 阅读项目文档及以下实现；本轮只借鉴实现思路，UE 代码和双手骨骼动作在本工程制作，没有引入这些项目的源码、手臂或动画文件。

- [COBRA-FPS-Feelkit / melee_weapon.gd](https://github.com/WynnSystems907/COBRA-FPS-Feelkit/blob/main/scripts/weapons/melee_weapon.gd)：分开攻击与恢复时间、恢复期输入缓存、区别挥空和命中音画反馈。其剑挥舞是程序化模型变换，并非可直接使用的双手骨骼动画。本项目保持原有两斩缓存与剑刃扫掠，在新时间窗上增加命中镜头反馈。
- [unity-procedural-motion / ProWeaponAnimator.cs](https://github.com/berkehansari/unity-procedural-motion/blob/main/Runtime/ProWeaponAnimator.cs)：将目标位移、旋转、冲击和回弹组合成第一人称外观反馈。该库主要是武器惯性参考；本轮用解析衰减曲线实现受攻击阶段控制的镜头回弹，没有移植其 Unity 控制器。
- 原动作相位来源继续为 [BigAndCrispy/Unity-First-Person-Melee](https://github.com/BigAndCrispy/Unity-First-Person-Melee)，固定版本和 CC0 许可见父目录 `Reference/`。Meshy、Manny 与本地剑气材质的来源许可不变。

## 接入

- `build_sword.py` / `arm_solver.py`：当前制作入口。
- `import_revision.py`：更新原 UE 资源路径，并在 `Before/` 保留导入前资源；不改装备或存档身份。
- `ImportHost/RuneSwordImport.uproject` 是无游戏模块的导入宿主，`Content` 目录联接到主工程 Content。仅用于 NullRHI 资产导入，避免共享 DLL 并行重建影响导入，不作为游戏启动入口。
- 原生代码使用工程标准 Editor 构建安装，交付模块随当前整个工程源码生成，保留并行开发。`NativeBuildSnapshot/` 保存本轮最终构建输出副本供恢复来源追踪，不自动回写正在被其他构建更新的模块。
- `author.log`、`build.log`、`build_install.log`、`import.log` 记录制作、必要构建与导入；`import_receipt.json` 由成功保存的导入脚本生成。

按用户全局规则，本轮不运行检查、测试、PIE、渲染或验收。现有 V4 图片仅作为制作参考；本轮最终外观、镜头幅度及攻击手感交由用户自行测试。

## 交付记录

六条动作、静态剑、完整双手视模和两张剑气弧面已制作并导出，Blender 制作进程返回 0。

首个必要构建生成后缀 49135 并成功结束，但随后其他并行构建重新生成了共享模块；后缀安装未完成，未将旧模块清单强行写回。后续标准 Editor 构建成功，输出 FPSGAME、AutoFootstep、AutoFootstepEditor 正常模块，并保留本轮输出副本。日志见 `build_install.log`，进程返回 0。构建时保留所有并行源码修改。

独立导入宿主通过 Content 目录联接更新主工程原资源路径，十项资源保存回执见 `import_receipt.json`；最终导入进程于 2026-09-13 23:47:15 结束，返回 0，日志为 `import_host.log`。导入前的原 uasset 保留在 `Before/`。早先主工程导入进程在 Python 脚本执行前因共享构建期间启动停滞被停止，其 `import.log` 不代表最终导入结果。

以上是制作、构建和导入结果，不是游戏内测试。重新打开工程后由用户测试最终剑面、手臂和攻击镜头手感。
