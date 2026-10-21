---
name: ue5-fps-arms-animation
description: 制作、迁移和修正 UE5 第一人称手臂动画及手部装备外观（皮肤、衣袖、手套材质与袖口），包括自然手指抓握、双手近战挥砍/重击/突刺/格挡、单手工具挥击、甩弹匣、取弹插入、普通与空仓换弹、拉栓、装备、检视、换握和奔跑；用 MAT、Control Rig、Blender 及实际音画检查修复扭曲、穿模、抖动与接触不同步。
---

# 本机维护源入口

本机共用流程统一读取[ue5-fps-arms-animation](C:/Users/allan/.codex/skills/ue5-fps-arms-animation/SKILL.md)，不要叠加旧镜像流程。

工程专属规则以当前 AGENTS.md、WORKFLOW.md 和本次用户要求为准。维护源不可用或需要查找未合入的工程经验时，读取[整理前工程资料](LOCAL-HISTORY.md)及原 references；其中历史测试与协调条款不构成执行授权。

此入口依赖本机个人目录；跨机器交付需另行导出所需维护源和引用。

枪械换弹屏幕反馈的当前实现和逐枪覆盖见[换弹镜头标准 RC1](../../Docs/Weapons/reload-camera-standard-20261013.md)。

双持甩弹匣／开弹巢的运行时分段节奏、音效提前量和独立弹壳交接见[双持换弹发力节奏 R1](../../Docs/Weapons/dual-reload-power-tempo-20261013.md)。

## 魔法书衔接

- 魔法书侧握到悬浮阅读、开合或落掌回握，及重复翻转/腕臂扭曲：[魔法书开合衔接](references/spellbook-transitions.md)。区分握持、掌向与阅读终点；当前 V30 保留已合格的主体动作与 1.12 秒时长，细调手指错峰、肩肘弧线和回握接触，效果待用户体验。

## Super90 分段节奏与腕臂续修

- 用户认可动作而只要求慢对准／快推进，或修腕臂、拉栓穿模时，读取 [Super90 共用源时钟与局部修订](references/super90-shared-clock.md)。保留有效作者输入，区分历史废案、已保存资产和待用户体验的最新节奏。

- 第三人称持剑握柄接触、旋风方向和版本恢复：[持剑接触与方向](references/third-person-sword-contact.md)。

- 冲刺屏幕幅度、全枪换弹镜头标准及双持甩匣／开巢节奏：[镜头反馈与双持发力](references/reload-camera-and-dual-tempo.md)。

- M870 的 AKM 整手复用、UC 装备／装填继承与快速近战右肘修订：[M870 动作与抓握](references/m870-source-motion-and-grip.md)。保留本枪接触、真实蒙皮铰链及仍有效的旧版工具依赖。

- [第三人称双手锤左手施法](references/third-person-casting-arm.md)：2026-10-18 本轮实现经验与恢复边界，按问题读取；不授权自动测试。

- 持弓左手施法、进食与回握，以及双手食物的取消恢复：[弓动作交接](references/bow-hand-string-contact.md#第三人称-sparrow-与左手动作交接2026-10-18)；拇指与最终蒙皮问题：[进食抓握](references/food-and-drink-grasp.md)。

- S12K 检视避让、空仓拇指回握与共振握把整臂跟随：[S12K 检视避让、空仓拇指回握与共振握把整臂跟随](references/saiga12k-grip-and-return.md)。按问题读取；历史检查不授权自动重测。

## 固定工位视角手臂 IK

- 工作视角里手看不见、同时有一条贯穿屏幕的 1px 细线，或要改 `AAlchemyWorldView`／`AForgeInteraction` 这类把相机与手臂一起搬进工位的视角：[工位视角手臂 IK 锚点](references/workbench-view-arm-anchor.md)。核心是"够手距离必须落在臂展内"，按该页的量取顺序先算距离再查渲染；`ArmBones` 含 clavicle 全部子骨，折叠非手臂骨救不了肩部拉伸。

- 衣袖与长袍漏空、原生绑定、下摆连续覆盖和布料同帧时序：[衣袖与长袍漏空、原生绑定、下摆连续覆盖和布料同帧时序](references/garment-continuity-and-cloth-timing.md)。按问题读取，历史证据不授权自动重测。

- SVCH 快速近战整手错位、腕肘扭曲、压缩帧间甩臂与动作时钟：读取 [SVCH 握点与帧间修订](references/svch-grip-subframes.md)。保留 V9、实际握点和仍有效的旧版恢复输入。

本轮导出的 [手枪与副手书](references/pistol-book-ads-and-reload.md) 记录原待机/V5 ADS、直接回握、双持消耗品及联机身份边界；共享维护仍以个人目录为准。

第三人称动作恢复、共用身体配置修改及动画发布，另读 [共享配置写入与发布](../../Docs/Workflow/player-body-config-publication.md)，保留其他动作入口并区分本地接入、Git 推送与用户认可。
