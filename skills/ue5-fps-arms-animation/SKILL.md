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
