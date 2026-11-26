---
name: ue5-cpp-gameplay
description: UE5.6-UE5.8 gameplay C++ implementation for Actors, Components, DataAssets, and gameplay logic. Use when requests ask to write .h/.cpp pairs, expose UPROPERTY/UFUNCTION to Blueprint, use GameplayTags, or build reusable component-based systems.
---

# UE C++ 玩法开发

**第一条（FPSGAME）　文件位置与引用路径。** 以含 `FPSGAME.uproject` 的当前工程根为准，先读 `Docs/Production/README.md` 和 `WORKFLOW.md` 第 4.1 节。先确定制作源、正式资产和输出目录，再创建或引入文件。工程 Content 资产用 `/Game/...` 包名引用，制作脚本从工程根或已配置的制作源根解析相对路径。交付时在同一功能条目登记实际位置、引用及备份状态。

遵守用户全局规则：后台开发与必要构建，不主动测试或跨对话协调。涉及资产、反射布局或编辑器占用时读取[执行规则](../ue5-auto-assistant/references/editor-open-development.md)。 原因：后台制作与必要构建已能完成任务，运行检查和跨对话沟通需要当前明确要求。

- 沿现有 Actor、Component、Subsystem 和存档边界实现；只修改必要的头文件和源文件，不为小改动强制创建成对新文件或设计表。 原因：现有宿主已定义生命周期和保存职责，小改动不需要另建抽象或额外文件结构。
- 生命周期、委托解绑和对象持有关系须与现有宿主一致；复制仅在功能涉及多人时接入，并保持服务端权威。 原因：对象持有、委托和复制属于宿主生命周期，另建一套会产生悬挂引用或错误权威。
- 反射布局变化要让依赖模块完成必要重编译；追加成员不能代替重编译。不因历史案例默认 Clean 或删除缓存。 原因：保存资产与依赖模块使用同一类型布局，追加成员不能让旧二进制自动兼容。
- Unity 名称冲突、UHT、物理 setter、5.8 API 差异或旧对象布局问题：按需读[引擎问题记录](references/engine-pitfalls.md)，不预先套用全部修复。 原因：历史条目只是故障线索，按真实报错读取可避免预先修改无关实现。
- 本次必要构建报错应处理；未运行游戏或测试时如实交付。 原因：源码需要生成对应产物才能交付构建状态，构建不能替代没有执行的运行测试。

## FPSGAME 按领域读取

新增 Tick、定时器、属性查询或加载路径时，读取 [性能开发约束](../ue5-performance-packaging/references/fpsgame-performance-development.md) 的高频路径部分。复用有界只读数据缓存，保留完整失效语义，避免同步加载与同一调用链重复计算；最终战斗状态仍实时参与原公式。
For FPSGAME active/passive skills, magic, progression and cast-hand arbitration, start with [skill and magic workflow](../ue5-skill-magic-workflow/SKILL.md).
For FPSGAME weapon work, start with [UE5 weapon workflow](../ue5-weapon-workflow/SKILL.md); arms/reload/MAT use [arms animation](../ue5-fps-arms-animation/SKILL.md).
For Godot first-person weapon ports, read [migration contracts and validation](references/godot-weapon-migration.md) before translating camera transforms, animation timing, recoil, or action audio.
FPSGAME traversal geometry, camera handoff and surface IK: [traversal contact](../ue5-fps-arms-animation/references/traversal-contact.md).
FPSGAME directional dodge, Shift tap/hold and invulnerability: [player dodge](references/player-dodge.md).
FPSGAME first/third person animation, world equipment and outfits: [player world body](references/player-world-body.md).
[饥饿、水分与 SAN](references/survival-state-and-attribute-penalties.md)：组件真源、分段消耗、组合属性倍率、归零边界通知与存档保持。

- F6 面板固定动作观察镜头：[固定第三人称观察](references/fixed-third-person-observation.md)。

- 已支付工件、评分品质与联机结算：[工件品质契约](references/paid-workpiece-quality.md)。

- FPSGAME 联机归属、事务中断与重连／重生／换图：[生命周期与覆盖记录](references/multiplayer-lifecycle-and-coverage.md)。

- [升级奖励与公开镜像](references/profile-progress-publication.md)：2026-10-18 本轮实现经验与恢复边界，按问题读取；不授权自动测试。
- 原生身体/性别变体、MetaHuman 头发装配、换装与家具相机：[身体变体工作流](references/native-body-variants.md)。

- 人物冷加载缺头、整人隐藏及衣物晚到：读取 [首次外观就绪](references/initial-appearance-readiness.md)。

- 消耗品的双手互斥、左键取消、普通面板与工作台待机见[交互动作占用](references/consumable-action-ownership.md)。

骑乘视点与交谈注视参见[骑乘视点与交谈注视](references/mounted-view-and-resident-gaze.md)。
