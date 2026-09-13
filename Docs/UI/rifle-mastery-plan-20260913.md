# 技能栏与步枪精通接入规划

2026-09-13。阶段：按用户要求直接制作并接入 UE，必要构建后由用户测试，不启动游戏或生成验收图。规范为 `UI-WORKFLOW.md` 与冷钢 UI 2.3。

## 原项目与迁移范围

来源为 `E:/无尽轮回/长期备份/2026-7-13-1/game-dev`：`data/skills.json`、`src/ui/skill-manager.js`、`src/combat/skill-level-system.js`、`src/config/attack-formula.js`、`src/effects/level-up-queue.js`、`src/ui/top-notification-queue.js`、`ui/panel-theme-backpack.css`。

仅接入首个被动技能 `rifleMastery`，不创建尚无玩法的主动技能或快捷栏绑定。原技能初始 1 级、上限 20 级；升级需求为当前等级×100；击杀 +10、暴击 +5，可叠加，普通命中不给修炼值。步枪武器贡献为 `round(武器伤害×(1+等级×0.01)+等级)`，角色攻击另加。精神加成为等级，作为派生值计入一次，不把原脚本的升级写基础属性和公式额外相加路径重复移植。

原版概率暴击与当前 UE 的要害判定冲突，已向用户提出选择；暂按推荐的要害伤害每级 +1% 迁移，保留要害判定。命中语境取发射时快照，飞行中换枪不会改变加成或修炼归属；仅有效怪物的直接步枪命中／击杀参与修炼，环境、无效命中、尸体不计。

## 面板与栏目

| 区域 | 内容 | 布局与状态 |
| --- | --- | --- |
| 现有右抽屉 | 启用“技能”页签，状态／装备／技能同级 | 复用玻璃、尺寸和开合；标题／返回／页签固定 |
| 分类栏 | 全部／被动／主动／魔法 | 4 个等宽按钮，36px 高、4px 间隔；无技能分类显示明确空状态 |
| 技能卡 | 原图标、名称、被动标签、等级、修炼条 | 点击或键盘确认进入详情；被动不拖入快捷栏 |
| 技能详情 | 描述、当前等级／下一等级效果、修炼来源、当前装备生效状态 | 固定返回列表，主体滚动；窄窗自然换行，名称与数值分列 |
| 升级提示 | 图标、技能／角色升级、等级和收益摘要 | 顶部居中单一 FIFO，约2.8秒，淡入／停留／淡出、银白扫光与0.5秒低强度亮光；不截获输入 |

普通 UI 为 Noto Sans SC，数字为 JetBrains Mono；字号使用20／16／14／12，图标48px。颜色和按钮从公共主题取得，卡片共享抽屉模糊。新增快捷键 `P` 直达技能，原 Tab／Caps／Esc 关闭和焦点合同保留，Esc 在技能详情先返回列表。

## 数据、保存与通知

- 配置放 `Content/ColdSteelData/skills.json`，稳定键为 `rifleMastery`。保存结构增加独立技能布局版本与技能进度映射，旧存档补入1级0经验，不改基础属性、不移除物品。
- 模型统一提供技能等级、修炼值、当前／下一等级效果、实际步枪伤害与精神派生值。展示不自行计算另一套成长。
- 玩家击杀经验与同一击的技能奖励共用现有保存事务；升级成功后才发布 UI 变化和通知。非致命要害命中也通过保存事务增加修炼。
- 提示队列只承载视觉和声音，关闭提示、排队或暂停不延迟／取消已经提交的属性。人物升级与技能升级进入同一槽，按触发顺序展示。
- 原音效由 `data/audio-config.json` 的 `uiCues.playerUpgrade` 定位到 `assets/sounds/ui/player_upgrade.mp3`；原始来源保留，转换为 UE 可播 PCM WAV。图标使用 `assets/skills/步枪精通.png`，保留原图身份。
- 技能页通过 Slate 绑定读取同一模型，数值改变不重建按钮；仅分类／详情切换和 DPI 改变重排。保留分类、详情与滚动，返回恢复卡片焦点；无数据／满级／未装备步枪均给出明确文字。通知组件只轮询待展示队列并推进视觉时钟，暂停冻结显示和音频，Destruct 停止音频并释放 Slate 引用。

## 修改范围

新增技能规则、技能面板和公共升级提示组件；局部接线 `ColdSteelStatusModel`、Profile 保存结构与加载、HUD 页签、角色伤害聚合及发射／弹道命中。资源来源和制作脚本保存在 `SourceAssets/Skills20260913` 与 `Tools/UI`。本轮无需要废弃的旧正式面板文件；不移走并行工作。

只完成必要原生构建，不运行技能、战斗、存档或 UI 测试，不把源码接入描述为运行验证通过。

## 已接入的实现

- `Source/FPSGAME/Skills/ColdSteelSkillTypes.h`：保存进度、效果、发射快照、提示数据。
- `ColdSteelSkillRules.h/.cpp`：读取配置、旧存档补齐、成长与伤害规则、命中路由。
- `ColdSteelSkillModel.cpp`：派生收益、怪物有效命中、击杀事务上下文与升级队列。
- `UI/ColdSteelSkillPage.h/.cpp`：分类、可点击技能卡、滚动详情、当前／下一级收益、装备状态；不提供被动拖放。
- `UI/ColdSteelProgressNotification.h/.cpp`：顶部玻璃提示、低强度银白亮光、细进度扫线、原版音效。单次事务跨多级时合并显示起止等级，避免数十条旧等级提示占用队列。
- `ColdSteelProfileRuntime`、`ColdSteelStatusModel`、`ColdSteelInventoryTypes/Rules`：沿用 A/B 保存事务；基础精神不写入技能增量。角色属性表展示基础＋被动总值并说明来源。
- `FPSGAMECharacterProfile`：加工后的步枪贡献应用精通，角色基础攻击保持另加。角色即发命中和 `FPSBallisticsComponent` 飞行弹丸都使用发射时快照；穿透链不因首个目标触发升级而临时改变同一发伤害。
- `ColdSteelHUDWidget`：启用技能页签、P 快捷键，保留 Tab／Caps／Esc 的输入模式与抽屉开合。Esc 在详情页先返回列表，再收起面板。

资源脚本 `Tools/UI/prepare_skill_assets.py` 已生成 `Content/ColdSteelData/Skills`。音效为 44.1kHz、双声道、16-bit PCM，约1.128秒，音量0.6；在提示真正开始展示时播放。源图和 MP3 及散列留在 `SourceAssets/Skills20260913`，资源经已有 ColdSteelData UFS 配置随项目部署。

本轮未运行游戏、技能、存档或 UI 测试；不创建验收报告。实际表现与交互由用户测试。

构建交付：Win64 Development 的 Editor 与 Game 目标已生成。Editor 使用独立模块编号 `913131`，避免覆盖仍被占用的原生模块；重新打开编辑器加载。构建日志为 `Saved/RifleMastery-editor-build-20260913.log` 和 `Saved/RifleMastery-game-build-20260913.log`。
