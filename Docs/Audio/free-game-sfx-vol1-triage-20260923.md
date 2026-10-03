# Free Game Sound Effects Starter Pack – 65 Free Sounds 分诊表（2026-09-23）

Fab 条目：<https://www.fab.com/listings/c00b1073-0f0b-42be-a049-fc4c22d0243f>
本地库缓存：`D:/FPS3D/VaultCache/FabLibrary/Free_Game_Sound_Effects_Starter_Pack_-_65_Free_Sounds-c00b1073`

## 落盘状态（本文写成时）

- 缓存目录内**只有 31 KB 的 `unreal-engine/manifest`，没有 `data\`**；对照组：其余 15 个库条目均有 `data\`。
- 工程内**不存在** `Content/FreeGameSoundsVol1/`；`Death_Rattle`、`Gore_Bone`、`Orc_War`、`Wolf_01`、`Rain_Steady`、`Spell_Fireball` 等独特名全盘无命中。
- manifest 内 `.wav` 计数为 **0**：包体是 `65 SoundWave + 65 SoundCue = 130 uasset`，**不含源音频文件**。
- 结论：该包**尚未下载/导入到 FPSGAME**。下表由 manifest 解析的文件名 + 现有源码接点推得，**未试听任何一条**；电平、时长、采样率、是否可循环均需导入后实测。

## 导入前先确认的两件事

1. **引擎版本**：manifest 记录构建 `5.9.0-58096714+++UE5+Dev-Marketplace-Windows`；工程 `EngineAssociation: 5.8`（`E:/Program Files (x86)/UE_5.8`）。已成功导入的 Vefects 包为 `5.8.0-49790047`。**5.9 存盘的 uasset 在 5.8 通常加载失败**，Fab 插件里必须选 5.8 兼容构建；没有则先处理引擎版本，不要硬导。
2. **不要用包内 SoundCue**：`*_Cue` 是 legacy SoundCue（5.8 已废弃，编辑器侧基本不可编辑）。取 `SoundWave`，变体靠代码已有的 `Pitch/VolumeMultiplier` 或自建 MetaSound/容器。

## 目标接点（现有代码，硬编码路径）

| 系统 | 位置 | 现状 |
|---|---|---|
| 脚步 bank | `Source/FPSGAME/Movement/FPSFootstepAudioComponent.cpp:30-39` | 从 `/Game/Audio/FreeFootsteps/S_%s` 载入；**Grass、Dirt 各只有 `S_mud02` 一个采样** |
| 火球 | `Source/FPSGAME/Skills/FPSFireballComponent.cpp:30` | `ImpactSoundAsset` 单条 `S_FireballImpactLayered`（`TSoftObjectPtr`，非数组） |
| 冰锥 | `Source/FPSGAME/Skills/FPSIceSpikeComponent.cpp:31`、`FPSIceSpikeVolley` | 单条 `S_IceImpact` |
| 冷钢挥剑/命中 | `Source/FPSGAME/Weapons/RuneSwordComponent.cpp:140,144`；`Skills/FPSQuickCombatComponent.cpp:74,76` | 轻/重/过顶共用一条 swing；`HitSound`/`BlockSound`/`ParrySound` 槽位存在 |
| 确认命中 | `Source/FPSGAME/FPSGAMECharacter.cpp:274`；`Weapons/FPSImpactFXSubsystem.cpp:63` | `S_Player_MonsterHit`、`S_GunHit`、`S_MeleeHit_Quick` |
| 怪物发声 | `Source/FPSGAME/Monsters/HandBrainMonster.h:32-34,82`；`Monsters/PoisonMaggotMonster.h:33` | `SlamSound`/`HowlSound`/`MoveSound`/`Voice`/`SpitSound` 槽位，多为空 |
| 天气 | `Source/FPSGAME/FPSWeatherManager.h:122-131`；`.cpp:133-136,190` | 雨 `/Game/Weather/Audio/S_Rain_*`；雷 `/Game/Thunder_Sounds/CUE/%s`；**无 wind 通道** |
| UI | `Source/FPSGAME/UI/M4GunsmithWidget.cpp:22` | 全项目 UI 仅一条 `S_Gunsmith_Confirm` |
| 泉水 | `Source/FPSGAME/Building/ColdSteelFountain.h:75,90-91` | `SplashCues` + `WaterLoop` 数组待填 |

## 65 条清单与判定

A = 高价值，直接替换/补空位；B = 可选，需新槽位或与现有资产重复；C = 不建议使用。

| # | 包内路径（`SFX/` 下，同名 `SoundWave` + `_Cue`） | 判定 | 接点 / 理由 |
|---|---|---|---|
| 1 | `Spell_Fireball/Spell_Fireball_01` | A | 火球 impact 变体 1（`FPSFireballComponent.cpp:30`） |
| 2 | `Spell_Fireball/Spell_Fireball_02` | A | 变体 2 |
| 3 | `Spell_Fireball/Spell_Fireball_03` | A | 变体 3；三条一起用需把 `ImpactSoundAsset` 改成数组 |
| 4 | `Spell_Ice_Spear/Spell_Ice_Spear_01` | A | 冰锥 impact 变体（`FPSIceSpikeComponent.cpp:31`） |
| 5 | `Spell_Ice_Spear/Spell_Ice_Spear_02` | A | 齐射时降重复 |
| 6 | `Sword_Swing_Fast_Light/Sword_Swing_Fast_Light_01` | A | 快速轻击挥剑层 |
| 7 | `Sword_Swing_Medium/Sword_Swing_Medium_01` | A | 中击挥剑层 |
| 8 | `Sword_Swing_Heavy/Sword_Swing_Heavy_01` | A | 重击挥剑层 |
| 9 | `Sword_Swing_Overhead/Sword_Swing_Overhead_01` | A | 过顶挥剑层；四方向分层是当前近战最缺 |
| 10 | `Gore_Bone_Crack/Gore_Bone_Crack_01` | A | 命中肉体/骨裂层 → `ConfirmedMonsterHitSound`、`RuneSwordComponent::HitSound` |
| 11 | `Footsteps_Dry_Leaves/Footsteps_Dry_Leaves_01` | A | 补 Grass/Dirt bank 单采样问题（现与 `S_leaves01/02` 合并成 5 采样） |
| 12 | `Footsteps_Dry_Leaves/Footsteps_Dry_Leaves_02` | A | 同上 |
| 13 | `Footsteps_Dry_Leaves/Footsteps_Dry_Leaves_03` | A | 同上 |
| 14 | `UI_Click/UI_Click_01` | A | 通用按钮音 |
| 15 | `UI_Interface_Click/UI_Interface_Click_01` | A | 面板/页签切换，与 14 分层级 |
| 16 | `UI_Confirm/UI_Confirm_01` | A | 可对照或替换 `S_Gunsmith_Confirm` |
| 17 | `UI_Access_Denied/UI_Access_Denied_01` | A | 负重不足/材料不足/不可放置等拒绝反馈 |
| 18 | `UI_Achievement/UI_Achievement_01` | A | 技能解锁、任务完成 |
| 19 | `UI_Craft_Complete_Success/UI_Craft_Complete_Success_01` | A | 锻造/制作成功 |
| 20 | `UI_Slot_Insert_Click/UI_Slot_Insert_Click_01` | A | 库存放入插槽 |
| 21 | `Death_Rattle/Death_Rattle_01` | A | 怪物死亡喘息 |
| 22 | `Voice_Idle_Groan_Low/Voice_Idle_Groan_Low_01` | A | 怪物待机低吟（`HandBrainMonster::Voice`） |
| 23 | `Voice_Idle_Groan_Medium/Voice_Idle_Groan_Medium_01` | A | 中音域，三条可做音高池 |
| 24 | `Voice_Idle_Groan_High/Voice_Idle_Groan_High_01` | A | 高音域 |
| 25 | `Attack_Bite/Attack_Bite_01` | A | 僵尸/变异体扑咬攻击音 |
| 26 | `Rain_Steady/Rain_Steady_01` | A | 远景雨 bed（`RainSound`/`HeavyRainSound` 候选，需实测可否循环） |
| 27 | `Storm_Approaching_Thunder/Storm_Approaching_Thunder_01` | A | 补 `ThunderSounds` 池 |
| 28 | `UI_Hologram_Open/UI_Hologram_Open_01` | B | 全息/魔法面板开启；科幻音色需试听判断 |
| 29 | `Wind_Howling_Storm/Wind_Howling_Storm_01` | B | `FPSWeatherManager` 无 wind 通道，要加 `UAudioComponent` 槽位 |
| 30 | `Tool_Axe_Chop_Tree/Tool_Axe_Chop_Tree_01` | B | 与 `EasyBuildingSystem/Audio/Sounds/Interactions/Chopping/SFX_Tree_Chop_001-004` 重复 |
| 31 | `Pickaxe_Strike_Rock/Pickaxe_Strike_Rock_01` | B | 与 `SFX_Pickaxe_Tool_001-004` 重复；可作石面差异层 |
| 32 | `Pickaxe_Strike_Hard_Stone/Pickaxe_Strike_Hard_Stone_01` | B | 矿点硬度分级候选 |
| 33 | `Pickaxe_Strike_Metal_Vein/Pickaxe_Strike_Metal_Vein_01` | B | 金属矿脉专用，现有资产缺这型 |
| 34 | `Gather_Strip_Bark/Gather_Strip_Bark_01` | B | 采集树皮，资源节点反馈 |
| 35 | `Tool_Cut_Jungle_Vine/Tool_Cut_Jungle_Vine_01` | B | 割藤蔓/植被交互 |
| 36 | `Armor_Plate_Movement/Armor_Plate_Movement_01` | B | 装备/受击金属层叠用；亦可用于重甲敌人 |
| 37 | `Splash_Person_Diving_In/Splash_Person_Diving_In_01` | B | 大落水冲击（当前只有踩水小音） |
| 38 | `Splash_Cannonball_Jump/Splash_Cannonball_Jump_01` | B | 同上，力度不同 |
| 39 | `Splash_Seawater_Splash/Splash_Seawater_Splash_01` | B | 水体交互泛用 |
| 40 | `Park_Fountain_Plaza/Park_Fountain_Plaza_01` | B | `ColdSteelFountain::WaterLoop` 候选（实景录音，与幻想风需核对） |
| 41 | `Forge_Hammer_On_Anvil_Light/Forge_Hammer_On_Anvil_Light_01` | B | 锻造台三段力度 1（现有 UI 无音） |
| 42 | `Forge_Hammer_On_Anvil_Medium/Forge_Hammer_On_Anvil_Medium_01` | B | 同上 |
| 43 | `Forge_Hammer_On_Anvil_Heavy/Forge_Hammer_On_Anvil_Heavy_01` | B | 同上 |
| 44 | `Wolf/Wolf_01` | B | 村庄/野外氛围；当前无狼类敌人 |
| 45 | `Wolf/Wolf_02` | B | 同上 |
| 46 | `Wolf/Wolf_03` | B | 同上 |
| 47 | `Goblin_Attack_Grunt/Goblin_Attack_Grunt_01` | B | 工程无哥布林系；仅在人形敌人复用 |
| 48 | `Goblin_Death_Gurgle/Goblin_Death_Gurgle_01` | B | 同上 |
| 49 | `Goblin_Idle_Chatter/Goblin_Idle_Chatter_01` | B | 同上 |
| 50 | `Orc_Attack_Grunt/Orc_Attack_Grunt_01` | B | 同上 |
| 51 | `Orc_War_Cry/Orc_War_Cry_01` | B | 同上（群体冲锋喊话可用性强于单体） |
| 52 | `Interior_Cafe/Interior_Cafe_01` | C | 现代咖啡馆环境，与冷钢/末世调性冲突 |
| 53 | `Street_Suburban_At_Night/Street_Suburban_At_Night_01` | C | 现代市郊夜景，不可用 |
| 54 | `Weapon_Blaster_Pistol_Fire/Weapon_Blaster_Pistol_Fire_01` | C | 科幻激光；枪械走 AKM/M4/SVD 真枪音 |
| 55 | `Weapon_Blaster_Pistol_Fire/Weapon_Blaster_Pistol_Fire_02` | C | 同上 |
| 56 | `Weapon_Blaster_Pistol_Fire/Weapon_Blaster_Pistol_Fire_03` | C | 同上 |
| 57 | `Knife_Chef_Knife_Chopping/Knife_Chef_Knife_Chopping_01` | C | 厨房切菜，无对应玩法 |
| 58 | `Knife_Cleaver_Chopping/Knife_Cleaver_Chopping_01` | C | 同上 |
| 59 | `Knife_Rapid_Dicing/Knife_Rapid_Dicing_01` | C | 同上 |
| 60 | `Sizzle_Bacon_Frying/Sizzle_Bacon_Frying_01` | C | 煎肉；除非做烹饪小游戏 |
| 61 | `Sizzle_Steak_Hit_Pan/Sizzle_Steak_Hit_Pan_01` | C | 同上 |
| 62 | `Bubble_Single_Pop/Bubble_Single_Pop_01` | C | 用途不明 |
| 63 | `Creature_Dolphin_Whistle/Creature_Dolphin_Whistle_01` | C | 海豚，场景无海洋生态 |
| 64 | `Horse_Hoofbeats/Horse_Hoofbeats_01` | C | 当前无马匹/NPC 骑兵 |

> 第 65 条：`Bow_Draw_Full_Tension/Bow_Draw_Full_Tension_01` → **B**，工程当前无弓，若做弓系武器直接可用。
> 计数：**A 27 条 / B 25 条 / C 13 条**（合计 65）。

## 导入后的落地清单（未执行）

1. 落盘到 `/Game/FreeGameSoundsVol1/SFX/<Category>/`，与工程约定 `/Game/Audio/<主题><日期>/S_*` 不一致 → 决定是原地引用，还是整理成 `Content/Audio/FreeGameSFX20260923/`。整理会改变硬编码路径，需同步改表。
2. 包内只有 uasset，**无源 wav**；若要进 MetaSound 或做变体容器，需在编辑器里对 SoundWave 执行 Export 取回 wav。
3. 需要的小改造：`FPSFireballComponent::ImpactSoundAsset` 单条 → 数组；挥剑按攻击类型选 swing；`FPSFootstepAudioComponent.cpp:35-36` Grass/Dirt 追加 leaves 采样；UI 侧新增点击/拒绝/成功/插槽四条统一入口。
4. 130 个二进制 uasset 进 `Content/`，按 `AGENTS.md` 与 `Docs/AssetSetup.md`「未审核再分发许可的原始资源不公开提交」先定提交边界。
5. 本表按文件名与代码接点推得，**未试听、未测电平/时长/循环点**；A 级判定不等于听感合格。
