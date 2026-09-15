# 单手转剑检视：GitHub 资料调查（2026-09-15）

**后续状态：用户否定 V35，2026-09-15 暂停制作。保留本调查及源骨骼研究；结论已整理到 [对应 Skill](../../skills/ue5-fps-arms-animation/references/source-hand-animation-study.md)。归档与运行冻结见 [暂停说明](sword-inspect-paused-20260915.md)。**

本轮按用户要求寻找可直接研究的项目。用户再次否定了当前检视效果，V34 不作为已认可动作。此次没有修改动画、导入游戏资产或运行游戏测试。

后续用户要求继续后，已完成 3 个刀具、8 段动作的骨骼数据转换与重点片段正侧面观察。新结果见 [逐帧研究记录](../../SourceAssets/RuneSword20260913/GitHubMotionStudy20260915/README.md)。下文为最初搜索阶段的记录；“尚未逐帧分析”描述的是当时状态。新的结论仍是可学习协作方法，尚无可直接替换本游戏的同款长剑动作。

## 结论

找到实际包含第一人称刀具模型、五指骨架和检视动作的 GitHub 项目，以及相关 Blender 编辑工具；尚未找到已确认同时满足“长剑、虎口外侧、张掌换握、腕部主导”且可直接用于本游戏的开源动画。

优先继续研究下列 Source 刀具动画。其价值是读取现成的手、指、武器协同关键帧；是否符合本任务的动作必须依据后续实际动作观察判断，不能由 `lookat`、`draw` 名称或骨骼存在推断。当前调查没有完成该项目的逐帧视觉分析。

## 1. 有实际动作资源的项目

[xDShot/csgo_knives_sweps](https://github.com/xDShot/csgo_knives_sweps)

- 仓库树读取版本：`c8535d73d145f895ea6e69d798dd84a9319dd81d`。
- 已读取 Lua 播放逻辑、仓库文件树，以及以下 MDL 文件的骨骼和动作名称字符串。
- `lua/weapons/csgo_baseknife.lua` 的 `Reload()` 通过 `ACT_VM_IDLE_LOWERED` 播放检视；动作时长读取模型 `SequenceDuration()`。Lua 本身没有定义手指或转剑关键帧。
- 模型中存在独立的 `ValveBiped.Bip01_R_Forearm`、`R_Hand` 以及 `R_Finger0…4` 和各指节名称。

| 实际文件 | 字节数 | 读到的相关名称 |
| --- | ---: | --- |
| `models/weapons/v_csgo_bayonet.mdl` | 119416 | `@draw`、`@lookat01`、`lookat01` |
| `models/weapons/v_csgo_falchion.mdl` | 175336 | `@draw`、`@lookat01`、`@lookat02`、`lookat01/02` |
| `models/weapons/horizon/v_csgo_stiletto.mdl` | 151960 | `@draw`、`@lookat01`、`@lookat02`、`lookat01/02` |

这些是编译后的 Source 模型，并非作者的 `.blend`/`.fbx` 制作源文件。本次树中未找到 `.smd`、`.dmx`、`.qc`、`.blend` 或 `.fbx` 文件。后续研究应连同模型依赖读取或转换，不能把 Lua 文件当作动画源。

作者 README 的 License 段明确：只有 Lua 和 tools 代码采用 MIT；模型、声音、纹理属于 Valve 或对应作者，许可未知。因此目前列为学习线索，不列为可直接移植或公开再分发的动画素材。

## 2. 配套编辑工具

- [adenexvfx/io_scene_CSGO](https://github.com/adenexvfx/io_scene_CSGO)：QC/SMD 骨骼修正、帧率读取和 FBX 转换；主分支更新记录包含刀具骨架旋转修正。属于转换工具，不提供目标转剑动作。
- 其 [V-master 分支说明](https://github.com/adenexvfx/io_scene_CSGO/blob/V-master/README.md) 专门描述同时导入手、武器和动画，建立约束后编辑，再导出。可以参考三者对齐方式；尚未在本机安装或确认 Blender 5.1 兼容性。
- [Artfunkel/BlenderSourceTools](https://github.com/Artfunkel/BlenderSourceTools)：Source 模型/动画与 Blender 之间的工具。不能修复原动作本身，也不改变素材授权。
- [Crowbar 项目](https://github.com/ZeqMacaw/Crowbar) / [作者工具主页](https://steamcommunity.com/groups/CrowbarTool)：Source 模型处理工具线索，本轮未安装或执行。

## 3. 已排除的候选

| 来源 | 实际调查所得 | 排除原因 |
| --- | --- | --- |
| [BigAndCrispy/Unity-First-Person-Melee](https://github.com/BigAndCrispy/Unity-First-Person-Melee) | 项目此前采用的 CC0 近战来源，已有 idle、slash、walk | 没有找到所需的转剑检视动作，不能当成新的解决方案 |
| [oyoing5968/blender-battle-animation](https://github.com/oyoing5968/blender-battle-animation) | README 声明 6 秒、24 fps、144 帧的拔刀/横斩/转刀/收刀草稿；对象级动画 | 作者明确说明尚无 Armature 蒙皮骨架和手指动作，许可尚未确定 |
| [Epicguru/Melee-Animation](https://github.com/Epicguru/Melee-Animation) | RimWorld 动画项目 | 不是可研究真实五指和腕部关节的第一人称手模动作 |
| [OpenGameArt：LowPoly Animated Sword](https://opengameart.org/content/lowpoly-animated-sword-w12-animations-blend-rigged) | 实际读取 `Arms.blend` 的 Action 清单及骨架 | 有攻击、格挡、装备、待机、行走、治疗；没有独立命名的检视/转剑 Action，不能据此宣称包含目标动作 |

OpenGameArt 文件为 3674340 字节；Action 清单：`Attack_01…04`、`Block_GetHit`、`Block_Idle`、`Draw_sword`、`Idle`、`Idle_GetHit`、`Skill_Heal`、`Unequip_Sword`、`Unequip_Sword.001`、`Unequip_Sword.002`、`Walking`。两个 Unequip Action 是空范围。仅以禁用自动执行的 Blender 后台读取内容，没有播放、渲染或保存修改。

## 4. GitHub 之外的补充线索

- [Chang Lin Toh：First-person AnimChallenge](https://tohcl.artstation.com/projects/ZGaLrX)：作者描述为 5 秒第一人称动作，结尾有剑花，起止回到侧方待机；目前获得的是作品说明，没有取得编辑源。页面视频嵌入读取失败，未将其视觉质量判定为适合本项目。
- [Darius Gilmere：Sword Flourish](https://dareheis.artstation.com/projects/LRXaQR)：作者说明用 Maya 和 Graph Editor 制作，并给出真人参考视频；展示和编辑源不是一回事。
- [Gamma Studio：First Person Melee Animations](https://www.fab.com/listings/2af6e911-4066-4cbe-91cc-dad8e929f291)：官方列出武器检视动作，但未确认检视是否为本任务需要的张掌外侧转剑，不据此建议购买。

## 下一步制作依据

先从现成动作中实际观察前臂、手掌、五指与武器的配合，再决定选取何种动作作为学习样本。需要确认的是握持点变化、松手/拇指让位/回握的先后，以及手腕附近的衔接。短刀与长剑的柄长、护手和惯性不同，不能只替换武器模型便宣称迁移完成；带环爪刀和蝴蝶刀的机构也不等于虎口夹持长剑。

原有背后拔剑装备动作、格挡、蓄力与 F 键合同保留。本调查不把当前动画的数学指标或无碰撞计数当作用户认可。
