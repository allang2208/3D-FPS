---

name: ue5-weapon-workflow

description: 开发和维护 UE5 枪械与近战武器，包括双手剑、轻重攻击、连击、突刺、格挡、第一人称弓与可替换部件表（弓体／弓弦／箭台按槽名改造），以及新枪与手模接入、枪匠配件、ADS、机械部件、音效、武器数据与装备存档闭环。用于 FPSGAME 的武器标准工作流；手臂姿态与换弹精修转 ue5-fps-arms-animation。

---

# 本机维护源入口

本机共用流程统一读取[ue5-weapon-workflow](C:/Users/allan/.codex/skills/ue5-weapon-workflow/SKILL.md)，不要叠加旧镜像流程。

工程专属规则以当前 AGENTS.md、WORKFLOW.md 和本次用户要求为准。维护源不可用或需要查找未合入的工程经验时，读取[整理前工程资料](LOCAL-HISTORY.md)及原 references；其中历史测试与协调条款不构成执行授权。

此入口依赖本机个人目录；跨机器交付需另行导出所需维护源和引用。

## 副手魔法书

- 魔法书属性、强化、浮窗、专注与联机打断，读取[副手魔法书：属性、专注与恢复](references/spellbook-focus-and-publication.md)。区分单件／总魔攻、瞬时动画／权威结算及活动源输入／废案。

## 霰弹枪弹药与联机收尾

- 伸缩后托/幻影握把表面、M16/ASH 瞄具座、SUPER90 枪口与加长弹仓组合及改造导航记忆，读取 [配件表面与霰弹枪组合](references/attachment-surface-and-shotgun-combinations.md)。保护有效恢复输入，区分视觉草稿与已应用玩法配方。

- SUPER90 弹药快照、权威装填回执、远端道具／枪口和轮盘缺图处理，读取 [霰弹枪权威与表现](references/shotgun-authority-and-presentation.md)。记录实际构建与尚未进行的联机体验，避免用保存或编译替代运行验收。

- 腰射／ADS 镭射归零、联机光点一致及架枪确认交互，读取 [战术灯与镭射](references/tactical-devices.md) 的最新规则；枪声、火光、退壳与每手机械事件见 [武器音效](references/weapon-audio.md)。

- 木工成品评分、弓物理伤害与法杖魔攻通道：[工件品质契约](../ue5-cpp-gameplay/references/paid-workpiece-quality.md)。
