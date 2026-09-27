# 猎手长弓：整理、发布与恢复

2026-09-27，按用户要求整理本对话的弓开发、沉淀技能并向
`https://github.com/allang2208/3D-FPS.git` 的 `main` 普通推送。
工作目录为 `D:/FPS3D/FPSGAME`。本轮不重新制作资产、不构建、不启动 UE 或游戏。

## 发布范围

- 猎手长弓命名、五槽改造目录、弓体形变、腰射/ADS 对位与扩散、搭箭衔接、连续射击与持弓移动接线。
- 50% 拉距发射门槛、50% 至 150% 蓄力伤害、弓伤害参数整体 1.5 倍及独立存档迁移。
- 暴击伤害 +50%、无枪声警报、立即击杀不传播群体受击警报；受击存活时保留既有报警。
- 穿甲/淬毒/锯齿三类箭，R 轮盘、弹药袋、按箭种替换模型、命中状态快照、实弹自动与手动回收。
- 独立弓改造预览、装备图标接线、21 张改造图标的灰阶制作配方，以及统一武器浮窗词汇和弓/枪械摘要。
- 作者/导入脚本、配置、设计与制作记录、归档清单和技能参考；不提交模型、媒体或引擎缓存。

## 当前本机资源

| 用途 | 保留的作者入口 | 已接入资产族 |
|---|---|---|
| 11 骨弓臂、四款弓体外表面修复 | `SourceAssets/BowSurfaceRepair20260927`，上游 `BowFlex20260927` / `BowBodyVariants20260926` | `DarkBow20260925/ElasticV15` |
| 五槽拆分、两款箭台 | `SourceAssets/BowModular20260926` | `ModularV13` |
| 木质圆环与竖针瞄具、自然连接座 | `SourceAssets/BowWoodBracket20260927` | `WoodBracketV19` |
| 握把三款及原装绑绳贴合 | `BowGripSeries20260927` / `BowGripContact20260927` | `GripSeriesV20` / `GripContactV22` |
| 搭箭连续动作与走跑动作 | `BowNockContinuity20260927` / `BowLocomotion20260927` | `NockContinuityV21` / `LocomotionV23` |
| 三款箭头、原箭杆/尾羽 | `SourceAssets/BowArrowVariants20260927` | `ArrowVariants20260927` |
| 统一灰阶改造图标 | `SourceAssets/BowIconAudit20260927` | `ColdSteelData/AttachmentIcons20260913/bow_dark_*` |
| 拉弓/放箭原速视频摘录 | `SourceAssets/BowVideoAudioDirect20260926` | `AudioVideoDirect20260926` |

上述弓资产族均位于 `/Game/Weapons/DarkBow20260925/` 下，图标例外。
保留 ContactV9/V7 手模、原生骨架、ArmsV2 木箭、木材/皮肤表面以及各作者脚本读取的
Blend、密集姿态 JSON、接触拟合数据。旧作者目录仍可能是新版本的输入，不能按日期清空。
特别是 `BowSightContact20260926/generated_actions.py` 与
`Bow_SupportClearanceV11.blend` 仍被快速近战制作链读取。

三款箭的 3 个静态网格、6 份新材质已导入保存；PNG 也已接入。
淬毒箭当前只有凹槽涂层和绑线为绿色，现有箭矢图标过曝，绿涂层识别偏弱；
这是待改进项，未将唯一当前输出当废案丢弃。
细节见 [箭矢制作记录](bow-arrow-variants-20260927.md)。

## 废案归档

本轮将两个已完成用途的一次性脚本移至 `trash/bow-publication-20260927/`：
V22 握把停止游玩脚本、因 PIE 拒绝保存而临时使用的补保存脚本。
正常重导入口 `BowGripContact20260927/import_assets.py` 保留。
源/目标路径、大小、移动前后 SHA-256 和替代入口见
[本轮清单](bow-retired-20260927.json)。

此前已经退役的 21 个长弓导入试件仍在 `trash/wood-longbow-probes-20260926/`，
本轮补发布 [原归档清单](wood-longbow-probes-retired-20260926.json)，不重复搬移。
V9 以前的归档以及其他任务的近战/快速近战归档保持原样。
当前模型源、历史接触求解输入、首次安装回执、关键失败对照、导入记录及当前唯一图标均保留。

## 精确暂存与未发布依赖

整理时共享 checkout 为 `cursor/highland-blade-seat`，基线与 `origin/main` 相同。
在现有 checkout 精确构造索引候选，普通推送 `HEAD:main`；不切换共享分支、不清理其他工作。
共享 C++ 文件按弓相关段落拆分；索引候选不写回工作文件。

- 另一任务的弓快速近战运行接线仍留本机；它依赖尚未发布的技能动作占用接口与整体近战调整。该任务作者配方已由此前提交公开，本轮不代为发布它。
- 生产工具/长杖评估及工具强化、树木生命值、锻造的未发布分支不纳入本轮。落在这些新函数中的公共浮窗词汇修改保留本机；公共词汇头、格式规则和可独立的弓/枪械/近战显示修改已发布。
- 弹药袋另一个任务的视图缓存重构不纳入本轮；位于该新函数内部的箭种说明仍留本机，已有结构上的弓脚注、R 轮盘和实际弹药处理已拆出。
- 枪械弹种扩展、换弹阶段、其他武器瞄具/动作、HUD 和地下城生成改动均未夹带。弹药目录只替换四个箭条目；群体警报只接入弓静默命中延迟判断，保留远端原邻接房遍历逻辑。

因此，公开源码与完整本机开发状态仍有明确差别。不能用本次提交覆盖脏工作区，
也不能宣称其他任务的交叉功能已全部发布。

## 许可、技能与交付状态

原木弓/扫描表面/原生手模和动作有各自来源，商用许可不等于公开再分发许可。
用户视频音效是原混音摘录，没有独立资产再分发许可，不能继承更早音效库的 CC0 标记。
Blend、FBX、UE 包、密集 JSON、贴图、音视频与回执由 `.gitignore` 留在本机；
Git 克隆不是完整可运行资产备份。恢复按上表和 [AssetSetup](../AssetSetup.md) 补齐合法本机资源。

个人与项目的武器技能补充 [箭种与回收合同](../../skills/ue5-weapon-workflow/references/bow-arrow-ammunition.md)，
更新 ContactV9 历史说明；改造图标标准和
[浮窗固定格式](../../skills/ue5-ui-umg-slate/references/weapon-tooltip-schema.md) 一并入库。

本轮只做用户授权的仓库/推送检查：暂存差异、文件边界、敏感信息、许可、脚本语法、
引用依赖、归档散列与远端提交读回。未运行游戏测试、渲染或验收。
最新箭种与浮窗原生代码仍按用户“稍后构建”的安排暂缓编译；历史构建成功不代表这一版 DLL 已更新。

发布前依赖阅读另外发现远端基线 `ColdSteelSkillTypes.h` 已引用尚未入库的 `Combat/MonsterToughnessTypes.h`。该怪物韧性文件属于其他未发布工作，本轮不代为提交；这也是不能宣称公开快照可独立完整构建的原因之一。
