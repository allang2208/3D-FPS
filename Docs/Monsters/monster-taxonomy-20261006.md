# 怪物分类与标签（2026-10-06）

用户指定的管理视图：形态分类 + 标签，供后续制作范围判定。以 `DevelopmentSpawnComponent` 的可刷怪名册为全集。

## 形态标签

- **人形**：标准双足人形骨架角色（僵尸系、巫婆、百目炉渣）。
- **类人形**：人形骨架但有显著非人特征；可与异形双标。
- **异形**：非人形结构（多足、节肢、软体、器官化、兽形四足）。除人形特征成员外，M-数字编号系列默认属异形类。

形态标签决定死亡标准归属：异形适用[连续软体死亡标准](continuous-soft-corpse-standard-20261005.md)，人形／纯类人暂不推广。M-31 按用户指定双标 **类人形＋异形**：分类归异形类管理，死亡入口仍维持人形方式。

## 编号规则（2026-10-16）

M 编号按品阶分段：人形 NPC 统一 **M-01**（同名不同编号的实验体系列，以名字区分）；普通异形 **M-02~09**；精英 **M-10~29**；领主 **M-30~59**；Boss **M-60~89**。号段内按强度递升。对外显示名用新号，内部类名／资产路径保留原号（M07/M08/M09/M10/M14/M25/M27/M66）。

Boss 号段当前留空：根冠、焚骸、合阙按 2026-10-16 用户拍板归入领主（M-34/35/36），领主带经验因此扩到 500–800。

## 数值带（2026-10-16 重排）

同品阶统一数值带，按定位在带内分配（参照：玩家 HP≈100+体×10+等级×10，防御减伤 60/(def+60)）：

| 品阶 | 生命 | 攻击 | 物防 | 魔防 |
|---|---|---|---|---|
| 人形 M-01 | 200–290（基准 250 的 ±20%） | 18–26（基准 22 的 ±20%） | 0 | 0 |
| 普通 | 150–300 | 15–50 | 0–15 | 0–15 |
| 精英 M-10~14 | 1400–2200 | 50–75 | 18–40 | 12–38 |
| 领主 M-30~33 | 2800–3600 | 80–95 | 30–50 | 20–45 |
| 领主 M-34~36（地牢首领） | 4200–6000 | 逐招定义 | 45 | 30–35 |
| Boss M-60~89 | —（预留，暂无在编成员） | — | — | — |

- 人形 M-01 个体差异由 `NurseZombie::BeginPlay` 的 tag 表注入：安保员 +16/+18（290/26）＞搬运工 +12/+14（280/25）＞园艺师（265/24）＞守寝者（255/23）＞技术员（230/21）＞研究员（210/19）＞接待员（200/18）；移速 90–95。
- 精英内按经验强度递升：伏窥者 M-10（1500/55/22-14）＜螳螂 M-11（1400/58/20-12，刺客玻璃）＜百目 M-12（2000/52/40-34，重炉体）＜悬钟 M-13（2000/58/30-38，施法）＜螺柱 M-14（2200/72/38-22，重击）。
- 领主内：涡电匣 M-30（2800/88/30-42，施法者）＜盲祷者 M-31（3000/85/30-28，法战）＜缚群 M-32（3500/90/46-28，巨物）＜沉匣 M-33（3600/92/46-24，顶点）＜根冠 M-34（4200，地牢首领，中茎为弱点）＜焚骸 M-35（6000，焚化区首领）＜合阙 M-36（6000，最终首领）。地牢首领沿用 Boss 体格但品阶为领主，经验 700/750/800。
- 根冠弱点：`Stem_Lower`/`Stem_Upper`/`Crown_Base` 三根连接茎骨为弱点判定骨骼（扇叶为普通组织）。
- BP 覆盖注意：BP 资产层保存的属性覆盖优先于 C++ 默认值（已核实缚群 BP 仅覆盖 WalkSpeed；盲祷者 BP 覆盖 MagicAttack，故其法攻以 BP 值为准、C++ 默认保留 70）。

## 名册

| 怪物 | 类 | 编号 | 形态标签 | 软体死亡 | 音效体系 |
|---|---|---|---|---|---|
| 根冠 | RootCrownRigPreview | M-34 | 异形 | 已接入（独立连续软体） | 三招、受击、落地及死亡音效已接入 |
| 合阙 | HeQueMonster | M-36 | 异形 | — | — |
| 焚骸 | M66IncineratorMonster | M-35 | 异形 | — | 部分：呼吸／炉火体系 |
| 园艺师 | NurseZombie / EcologyGardener | M-01 | 人形 | 否（复用研究员人形死亡） | 共享 HumanoidAudioV1 |
| 安保员 | NurseZombie / FacelessSecurity | M-01 | 人形 | 否 | 共享 HumanoidAudioV1 |
| 接待员 | NurseZombie / FacelessReceptionist | M-01 | 人形 | 否 | 共享 HumanoidAudioV1 |
| 研究员 | NurseZombie / FacelessResearcher | M-01 | 人形 | 否 | 共享 HumanoidAudioV1 |
| 搬运工 | NurseZombie / CargoPorter | M-01 | 人形 | 否 | 共享 HumanoidAudioV1 |
| 技术员 | NurseZombie / CargoTechnician | M-01 | 人形 | 否 | 共享 HumanoidAudioV1 |
| 男性员工 | NurseZombie / LivingStaffMale | M-01 | 人形 | 否 | 共享 HumanoidAudioV1 |
| 女性员工A | NurseZombie / LivingStaffFemaleA | M-01 | 人形 | 否 | 共享 HumanoidAudioV1 |
| 女性员工B | NurseZombie / LivingStaffFemaleB | M-01 | 人形 | 否 | 共享 HumanoidAudioV1 |
| 守寝者 | NightWarden(BP) | M-01 | 人形 | 否 | — |
| 鼓囊 | BellowSacLobber | M-09 | 异形 | 已接入 | **AudioV10/V11** |
| 盲祷者 | BlindSupplicantMonster | M-31 | 类人形＋异形 | 否（人形保留） | 部分：墙拟态身份音 ×1 |
| 伏窥者 | LurkerM08Monster | M-10 | 异形 | 已接入 | **AudioV01**（6 条 + 气炮 V06/V11 沿用） |
| 悬钟 | HangingBellM09 | M-13 | 异形 | 已接入 | **AudioV01**（7 条 + 复用 V07/V08） |
| 沉匣 | M10Mawcrawler | M-33 | 异形 | 已接入 | **AudioV1**（8 条，CC0 源） |
| 螺柱 | SpiralPillarM14 | M-14 | 异形 | 标准原型 V19 | **AudioV01**（9 条） |
| 涡电匣 | VortexCofferM25 | M-30 | 异形 | 已接入 | **AudioV1**（9 条） |
| 缚群 | BoundCongregate | M-32 | 异形 | 已接入 | 部分：旧占位 |
| 螳螂 | MantisM27Monster | M-11 | 异形 | 范围登记、未制作 | **无** |
| 手脑 | HandBrainMonster | — | 异形 | 已接入 | 部分：旧占位 ×3（嚎叫／移动／砸击） |
| 异变巨手 | FleshHandMonster | — | 异形 | 已接入 | 部分：撞击／蓄力／冲撞 ×3 |
| 小皮肤手 | FleshHandMonster(minion) | — | 异形 | 已接入 | 共享巨手音效 |
| 毒蛆 | PoisonMaggotMonster | — | 异形 | 已接入 | 部分：喷吐 ×1 |
| 野狼 | WolfMonster | — | 异形 | 已接入 | **无** |
| 僵尸犬 | ZombieDogMonster | — | 异形 | 已接入 | **无** |
| 感染犬 | InfectedDogMonster | — | 异形 | 已接入 | **无** |
| 胖子僵尸 | FatZombie | — | 人形 | 否 | 共享 HumanoidAudioV1 |
| 突变体-3 | Mutant3 | — | 类人形 | 否 | 共享 HumanoidAudioV1 |
| 护士僵尸 | NurseZombie | — | 人形 | 否 | 共享 HumanoidAudioV1 |
| 毒液僵尸 | SpitterZombie | — | 人形 | 否 | 共享 HumanoidAudioV1 |
| 巫婆 | WitchRebuiltMonster | — | 人形 | 否 | 共享 HumanoidAudioV1 |
| 百目炉渣 | HundredEyedSlagMonster | M-12 | 类人形＋异形 | 否 | — |

## 音效重设计状态

已完成 AudioV1/AudioV01 体系的异形类：M-10、M-13、M-33、M-14、M-30。

**HumanoidAudioV1（2026-10-16）**：`NurseZombie` 基类接入共享人形音效（Idle 循环/Chase/Attack/Hit×2/Death/Step×2，8 条，OpenGameArt CC0 源，槽位挂 `SetState` 状态边沿与速度门控脚步）；护士僵尸、毒液僵尸、胖子僵尸、突变体-3、巫婆及全部 M-01 职员共一套。制作 `Tools/Monsters/author_humanoid_audio_v1.py`，导入 `Tools/Monsters/import_humanoid_audio_v1.py`，资产 `/Game/Monsters/Shared/HumanoidAudioV1/`。守寝者为纯 rig 无玩法类，不在接入范围。

**未完成**的异形类（按缺口排序）：

- M-11 螳螂：零音频，连占位音都没有。
- 野狼／僵尸犬／感染犬：零音频（犬科三员可共用一套制作批次）。
- 毒蛆：仅喷吐一条；无 idle、移动、爆裂死亡音。
- 手脑：3 条旧占位，移动与砸击与现动作集未必对位；沉匣 AudioV1 曾借用其嚎叫源。
- 异变巨手／小皮肤手：3 条旧音，无 idle 与死亡体系。
- M-10 伏窥者：仅气炮武器音；本体 idle、表面爬行、接触异形动作、受击、死亡均无。
- M-31 盲祷者（异形标签侧）：仅墙拟态身份音；施法与受击音在战斗魔法批次内另计。
