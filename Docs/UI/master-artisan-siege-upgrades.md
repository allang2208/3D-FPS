# 工匠大师 · 守备设施升级

研究「守备机械」后，在东门马厩对面的机械工坊瞄准工匠大师按 E。选择「升级守备机械」进入工坊页面。「闲聊」使用村民对话的逐字显示、数字选项和返回机制。

## 卡片与交互

升级页从屏幕右侧滑入，在常用桌面尺寸占宽约 39%。顶部固定独立浅底标题带（`守备设施升级 · 全村共享 · 即时生效`）、金色灵魂胶囊余额与 `收起 Esc` 按钮。设施选择区采用水平可扩展列表，已完整接入「配重投石机」「固定式弩炮」「城防热油锅」「符文引雷塔」四项设施（选中超出视口卡槽时自动 `ScrollDescendantIntoView` 滚动对焦）。设施卡复用东门马市 R46 同源图牌 `SHorseMarketPlate`（可按设施配置 `PortraitFocus`，选中态呈现四角金色 L 框与底线，未选卡暗角压底常显名称，悬停微放大提亮）。

桌面尺寸卡片下方附带当前设施 4 项生效指标的总览条；强化项目沿用**强化栏分段式进度条**并保留亮金色配色：已达成段为暖亮金（满级转为浅金），下一级高亮半透金描边提示，未解锁段为暗槽；15 级与 3 级属性分别渲染 15 格与 3 格等宽分段。满级项切换暖金高亮卡与「✓ 已满级」金徽章，余额不足按珊瑚红标出缺额，结算期间锁定操作并在底部提示条高亮反馈。面板高度低于 620 布局单位时自动切换 50px 矩形缩略页签（`投石机 / 弩炮 / 热油锅 / 引雷塔`）并收起总览条。

## 2026-11-27 符文引雷塔接入（待备份 · 未跑实机 PIE/多人验证）

- 数值与工坊卡片：`VillageSiegeUpgrades.h` 启用全部 `uint64` 位宽（`16×4 = 64 位`，`FacilityCount = 4`、`Count = 16`，零存档迁移）新增 `EFacility::LightningSpire = 3`（48 阶：雷击伤害 15 / 聚能冷却 15 / 感电层数 3 / 引雷射程 15）；`SSiegeWorkshopMarket.cpp` 新增第 4 张设施卡（[LightningSpire.jpg](../../Content/ColdSteelUI/SiegeWorkshop/LightningSpire.jpg)）与页签切卡自动滚动对焦。
- 运行时玩法与屋顶建造：`AVillageLightningSpire`（[VillageLightningSpire.cpp](../../Source/FPSGAME/WorldGeneration/VillageLightningSpire.cpp)）限定仅可安放于高塔/石城门屋顶，采用 `52–75.4 m` 水平 2D 射程与越墙高弧斜劈（兼顾塔脚贴墙单位），支持按 `E` 接管手动瞄准（磁吸辅助、`320 cm` 落地震荡涌流、`+20%` 手瞄伤害、`10%` 冷却缩减），发射加粗 `AFPSLightningArc`（自动 `2.40×`、手瞄 `2.85×`）并连锁 3 目标、施加麻痹打断（`0.65 s / 0.35 s`）与 `AddElectrified` 感电及 5 层过载爆炸；建筑放置（按 `B`）同步显示低饱和升级联动范围圈（`M_SiegeRangeIndicator`）。
- 离线验证记录：[编辑器编译日志](F:/FPSGAMEData/ArtReviews/HighVillageDefense/LightningSpirePhase2-20261127/EditorBuild.log)（`Succeeded`）· [自动化测试日志](F:/FPSGAMEData/ArtReviews/HighVillageDefense/LightningSpirePhase2-20261127/SiegeTests.log)（`TESTS_EXIT=0`，`FPSGAME.Village.Siege.LightningSpire` 与 `PreviewAndReload` 全过）· [工坊 UI D3D12 审查日志](F:/FPSGAMEData/ArtReviews/HighVillageDefense/LightningSpirePhase2-20261127/WorkshopUIReview.log)（`UI_EXIT=0`，`WORKSHOP_DRAWER passed`）· [UI 审查截图目录](F:/FPSGAMEData/ArtReviews/HighVillageDefense/LightningSpirePhase2-20261127/UI)（`03d-spire.png` 等）。

## 2026-11-26 分段进度条、15 级数值调整、热油锅接入与字号字重统一（待备份）

- 排版与字重校准：[SSiegeWorkshopMarket.cpp](../../Source/FPSGAME/UI/SSiegeWorkshopMarket.cpp) 统一通过 `TextFont(Px * 0.75f, Weight)` 按冷钢规范对齐 `NotoSansSC` 字重（仅顶栏主标题 `守备设施升级` 使用 `Bold 700`，卡名/分区标题/项目名/目标新值与满级徽章用 `SemiBold 600`，正文/当前值/按钮/魂价与提示均用 `Regular 400`），并为顶部与分区标题补充金色竖线、总览条竖分隔及分区横细线。
- 数值与存档：`VillageSiegeUpgrades.h` 由 `uint16`（8×2 位）扩展为 `uint64`（12×4 位 = 48 位，每项支持 0–15 级）；`UVillageDefenseSave`（`Version=2`）将旧版 v1 `uint16 SiegeRanks` 自动无损迁移至 `SiegeRanksV2` 并保留损伤档案；`ATemperateHillsWorld::SiegeRanks`、`UChapelDialogueComponent::WorkshopRanks()` 与 `AVillageSiegeMissile` 同步升级至 `uint64`。
- 热油卡图与玩法联动：基于 `SM_OilHearth.meshzip` 在 Blender 5.1 同棚拍机位与布光下渲染 [HotOil.jpg](../../Content/ColdSteelUI/SiegeWorkshop/HotOil.jpg)，并完成 `AVillageOilField` / `FVillageOilSpread` / `VillageOilFireFront` / `UCombatStatusFormula::AddOilBurn` 与 `FlowR2/M_OilFilm`（CPD 1 动态时长渐隐）全链路接入。
- 验证输出：[编辑器编译日志](F:/FPSGAMEData/ArtReviews/HighVillageDefense/WorkshopOilUpgrades-20261126/EditorBuild-Typography.log)（`BuildExit=0`）· [材质发布回执](F:/FPSGAMEData/ArtProduction/HighVillageDefense/WorkshopOilUpgrades-20261126/Surfaces/published.json) · [UE 无头 Slate 审查日志](F:/FPSGAMEData/ArtReviews/HighVillageDefense/WorkshopOilUpgrades-20261126/review-v2.log)（`ReviewExit=0`，0 错误）· [实机截图目录](F:/FPSGAMEData/ArtReviews/HighVillageDefense/WorkshopOilUpgrades-20261126/LiveUE_V2)（`02-trebuchet.png` / `03-ballista.png` / `03c-hotoil.png` / `04-compact.png` / `04b-short.png`；实机 PIE/多人联机实战暂未运行验证）。

## 数值与灵魂定价

付款玩家承担费用，同一村庄中所有玩家、已有与新建守备设施共用等级。

- **3 级上限项目**（投石机爆炸半径、弩炮护甲穿透、热油持续时间、热油灼烧层数）：逐级消耗 **200 / 400 / 800** 灵魂（单项目满级累计 **1,400** 灵魂）。
- **15 级上限项目**（伤害、装填冷却、射程、热油蔓延范围）：逐级消耗 **100 / 140 / 180 / 230 / 290 / 360 / 440 / 530 / 640 / 760 / 900 / 1,060 / 1,240 / 1,440 / 1,680** 灵魂（单项目满级累计 **9,950** 灵魂）。

| 设施 | 属性 | 上限 | 初始 (Lv0) | 每级增量 | 满级 |
| --- | --- | ---: | ---: | ---: | ---: |
| 投石机 (`48 阶`) | 中心伤害 | 15 级 | 300 | +10% (+30) | 750 (+150%) |
| 投石机 | 装填冷却 | 15 级 | 10.00 秒 | -3% (-0.30 秒) | 5.50 秒 (-45%) |
| 投石机 | 爆炸半径 | 3 级 | 5 米 | +0.75 米 (+15%) | 7.25 米 (+45%) |
| 投石机 | 射程 | 15 级 | 81 米 | +3% (+2.43 米) | 117.45 米 (+45%) |
| 弩炮 (`48 阶`) | 伤害 | 15 级 | 180 | +10% (+18) | 450 (+150%) |
| 弩炮 | 装填冷却 | 15 级 | 3.27 秒 | -3% (-0.098 秒) | 1.80 秒 (-45%) |
| 弩炮 | 护甲穿透 | 3 级 | 0% | +10% | 30% |
| 弩炮 | 射程 | 15 级 | 56 米 | +3% (+1.68 米) | 81.2 米 (+45%) |
| 热油锅 (`36 阶`) | 热油伤害 | 15 级 | 10 / 0.25s | +10% (+1) | 25 / 0.25s (+150%) |
| 热油锅 | 蔓延范围 | 15 级 | 2.75 米（基础削弱） | +0.15 米 | 5 米 (+2.25 米) |
| 热油锅 | 持续时间 | 3 级 | 10 秒 | +2 秒 | 16 秒 (+6 秒) |
| 热油锅 | 灼烧层数 | 3 级 | 1 层 / 次 | +1 层 / 次 | 4 层 / 次 (+3 层) |
| 引雷塔 (`48 阶`) | 雷击伤害 | 15 级 | 115（手瞄 +20%） | +10% (+11.5) | 287.5 (+150%) |
| 引雷塔 | 聚能冷却 | 15 级 | 4.50 秒（手瞄 -10%） | -3% (-0.135 秒) | 2.48 秒 (-45%) |
| 引雷塔 | 感电层数 | 3 级 | 1 层 / 次 | +1 层 / 次 | 4 层 / 次 (+3 层) |
| 引雷塔 | 引雷射程 | 15 级 | 52 米（水平 2D / 0 盲区） | +3% (+1.56 米) | 75.4 米 (+45%) |

投石机/弩炮/引雷塔自动索敌与手动瞄准读取同一射程，开火时锁定本发伤害、装填/充能冷却及穿透/半径/感电参数，装填动作、声音与进度条按同一时长同步。热油锅在泼出油区生成（`BeginPlay`）时锁定当前村庄升级等级并通过 `COND_InitialOnly` 同步至客户端，分别控制 0.25s 脉冲伤害、蔓延半径、火海寿命（含 `M_OilFilm` CPD 1 淡出时长与点光衰减半径）以及每次接触触发 `AddOilBurn` 施加的灼烧层数。引雷塔每次击发额外召唤加粗 `AFPSLightningArc` 并最多连锁 3 名视野内敌对目标，按跳次衰减 15%、施加麻痹打断并叠加 `AddElectrified`（满 5 层触发 1.2s 过载眩晕与 `225 cm` 范围雷暴）。

[数值来源](../../Source/FPSGAME/WorldGeneration/VillageSiegeUpgrades.h) · [存档与迁移](../../Source/FPSGAME/WorldGeneration/VillageDefenseState.cpp) · [升级页面](../../Source/FPSGAME/UI/SSiegeWorkshopMarket.cpp) · [棚拍脚本](../../Tools/WorldGeneration/MasterArtisan/workshop_plates.py) · [机械卡图](../../Content/ColdSteelUI/SiegeWorkshop) · [旧版备份](Y:/备份/FPS3D/HighVillageDefense/MasterArtisan-SiegeUpgrades-20261124/SiegeUpgrades.zip)
