# 战锤改造、动作与冲刺联机整理发布

范围为 2026-10-23 符文战锤发布之后，本对话的锤头、符文、两款配重球、通用锤座、空间扰动、镇魂钟动作复用，以及双手锤冲刺位移和第三人称／联机修复。其他会话的在途功能和暂存条目不在本批范围。

## 当前版本与发布边界

- 锤头与图标：RuneAndBellRefinement20261024、HeadRunePBRV3；两个传说锤头继承原装刻纹与法线细节，镇魂钟增加金色电弧。
- 镇魂钟二连：FinalTollDirectReuseV5，完整复用原生 Slash1 右上至左下的发力和 Uppercut 上挑轨道。当前四个第三人称配置叶字段见 [动作清单](body-config-manifest.json)。Kaitlin 已被后续 WeaponContacts20261024 接触修正资产接替，保留其现值；不要重跑旧发布器覆盖这些衍生版本。
- 紫色 ManaOrbPommelV2、蓝色 StarTideCoreV1，以及 OrbEdgeV1 球边缘材质；二者均为符文战锤专属特殊改造。紫色增加 10 秒基础苏醒时间，蓝色苏醒期间每次有效命中增加 0.5 秒，不设总时长上限。
- 破势古印锤座：快速近战命中施加 8 秒破势印与头顶金色古印；保留独立被动属性。叠片缓冲座采用独立属性定位。鸣雷锤座为 StormDriveBuildV1 → StormDriveTrimV2 → StormDriveRuneV3，保留闭合边饰、精修闪电刻纹及与镇魂钟的命中联动。
- 本批 C++ 包含电弧、所有双手锤挥击扰动、前踏／空中惯性及第三人称步态算法，另含用户此前要求排查时制作的显式启用诊断入口。运行配方只更新所属改造、状态和动作键。

可独立拆分的当前源码发布到根目录 Source，作者脚本留在 SourceAssets。共享组件与移动／动画消费者仍混有其他未发布前置，无法独立重放的接线在 [Integration 清单](integration-manifest.json) 记录实际宿主 SHA-256、目标位置和合并说明；`.inc` 是人工合并片段，不可整文件覆盖或直接批量应用。ProductionBluntAuthority.cpp 是完整所属编译单元，但仍依赖同一组件的私有状态与 RPC 前置。

**本批属于源码、配方与接入材料的部分发布，不声明公开仓库干净检出可独立编译。** 完整接入在本机工程，公共重建还需先恢复之前的战锤权威框架、ColdSteelAuthority／技能快照、共享 ProductionToolComponent 及身体动作层，再按清单合并；未把其他会话新增的副手弯刀、逐风等共享改动整文件带入本批。历史发布入口见 [2026-10-23 发布](../RuneboundWarhammer20261023/README.md)。

## 本机资产与恢复顺序

完整模型、FBX、Blend、4K PBR、图标母图、动画供体、密集采样、UE 包及成功构建产物留在本机；商用许可并不等于原资产公开再分发许可。本次没有新增公开二进制，也没有移动任何 Content 包。Content 通过 D 盘工程入口联接到 F:/FPSGAMEData/Content。

1. 恢复已有原装战锤、NormalComboV4/UppercutV1 手臂供体、Jason/Kaitlin 身体供体及标准图标母图。FinalTollDirectReuseV5/inputs.json 记录原始采样入口。
2. 锤头精修仍需 StarOathHammerHeadV1、FinalTollHammerHeadV1/V2 原作者脚本和正式源资产；HeadRunePBRV3 以其真实几何再制作。RuneAndBellRefinement 的安装辅助仍是 OrbEdgeV1 的依赖。
3. 紫蓝球保留各自可编辑 Blend、Export、Textures、程序体积材质；LocalPosition 版本修复了像素阶段使用 PreSkinnedPosition 引起的棋盘格。球体边缘方案在 OrbEdgeV1。
4. 鸣雷 V3 继续依赖 V1/V2 的几何、4K纹理和材质，不把旧目录整体当废案。破势古印的符印、声音与锤座模型由 AncientSealBuildV1 作者源恢复。
5. 按各导入器的明确目的地及现有 UE 批次互斥导入并保存，再合并运行配方。钢锤作者配置只保存本次两个锤座叶字段于 [作者配置片段](steel-author-seat-leaves.json)；不覆盖本机其他条目。仅写导入脚本不算已导入。

作者脚本中的 D:/FPS3D/FPSGAME、UE 安装目录与 Saved/ 日志是本机案例默认值，迁移机器时先修改目的地并准备已许可输入。需要 Shapely 的模型作者脚本使用本机 python_deps；不公开捆绑该第三方安装目录。公开提示词不能替代实际已选图像。

## 退役文件与恢复

[归档清单](archive-manifest.json) 和 [移动回执](archive-receipt.json) 记录全部原路径、trash 目标、大小、SHA-256、原因和保留替代物。1235 个文件，共 4,194,626,740 字节（约 3.91 GiB），已移入本机 `trash/warhammer-refinements-retired-20261025/` 并核对移动前后散列。trash 不推送 Git。

归档包括被 V5 替代的二连重击 V2/V3/V4、被否决的 ManaOrb V1、未采用的棘轮／风枢概念、重复 AuthorHost、完成后的 Before 快照、已有正式 Blend 的 blend1、旧失败日志及 CompileUnits 临时构建单元。当前供体链、最终可编辑源、成功证据与原始许可输入均保留。取回时按清单恢复到临时位置做三方合并，不用旧完整配置或暂存裁剪文件覆盖活动工程。

## 既有证据与本轮操作

[证据摘要](validation-summary.json) 仅归纳此前用户要求排查／修复时的本机结果：Editor 和 Game 完整构建成功；隔离权威 28 项通过；真实本机 UDP 在 80 ms 延迟、2% 丢包下前移 100 cm、扣费一次，最终位置误差 0.029 cm；Jason/Kaitlin 原生动画图各 4 组采样。详细范围见 [当时报告](../../../SourceAssets/WarhammerSprintLunge20261025/CompletionReview/review.md)。

权威夹具直接调用处理器，不是 UDP。UDP 仅固定平地的一客一监听主机并关闭身体渲染；未覆盖真实敌人完整实战、第三观察者、重连与全部坡面。骨骼采样采用重建轨迹和离线蒙皮，不是最终武器、服装和地面 IK 的实机画面。本轮只做归档与 Git 发布检查，未重新构建、启动 UE、运行游戏或验收；最终观感和操作手感由用户确认。

复用经验同步到个人技能与仓库 skills：武器材质／改造、成熟动作复用／步态、攻击身份与 CMC 同步三个部分。
