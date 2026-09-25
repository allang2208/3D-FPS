# 采集工具强化系统设计（2026-09-25）

> 本次只交付**设计**：不改代码、不动资产、不设消耗、不设强化后数值。数值与消耗等待用户另行授权。
> 用户已确定的五项决策（2026-09-25）：① 出厂即 1 级石头外观，现有青铜降为 2 级；② 独立字段 `tool_enhance_level` ＋ 改造工作台新增「强化」栏；③ 金属／木质分离走 **Blender 重导出拆材质槽**；④ 覆盖第一人称视模与背包／图鉴图标等级角标，**不含铁铲**、不含 5 级发光特效；⑤ 等级规则**逐级 +1、不可降级、不可跳级**。
> 相关口径：[采集工具改造系统](tool-modification-20260924.md)、[采集工具战斗接入](../../skills/ue5-weapon-workflow/references/harvesting-tools.md)、[采集工具发布与恢复](production-tools-publication-20260920.md)、[面板／栏目工作流](../../UI-WORKFLOW.md)。UI 栏目细化见 [强化栏规划](../UI/tool-enhancement-column-plan-20260925.md)。

## 1. 与武器强化的区别

现有武器／防具强化（`UColdSteelEnhancementSystem`）是**数值加工**：`enhanceLevel` 直接进 `ProcessedDamage` 的 `L` 项、有金币＋强化石报价、上限 15／10 级、外观只有图标右上角光晕。工具强化是**外观档位**：

| | 武器强化（现状） | 工具强化（本设计） |
| --- | --- | --- |
| 字段 | `enhanceLevel`（0…15） | `tool_enhance_level`（1…5，缺省 1） |
| 语义 | 数值加工等级 | 金属部位材质档位 |
| 外观 | 不换模型材质，只有图标角光晕 | 换金属材质槽的材质实例 |
| 消耗 | 金币 ×1.5^L ＋ 强化石 | **本次不设**（目录预留字段，留空） |
| 数值 | `Increase=0.05`／级，进伤害公式 | **本次不设**（目录预留字段，留空；`ColdSteelTool::Evaluate` 不读等级） |
| 入口 | 强化台 `EnhancementPanel` | 改造工作台第五栏「强化」 |
| 上限来源 | `enhancement.json` | `tool-enhance.json` 的等级条目数 |

**为什么不复用 `enhanceLevel`**：该字段一旦非零就立刻进 `ProcessedDamage` 的强化项与浮窗「已强化 +N」，等于在"先不设置强化后数值"的前提下偷偷加数值；而且它的上限、报价、附魔卷轴都绑定武器口径。独立字段可以让本次交付严格是"外观 + 存档 + UI"，数值后续单独授权。

## 2. 等级阶梯与外观定义

出厂即 1 级；强化只改**金属部位**（斧＝斧刃前段＋斧背＋固定箍；镐＝镐尖＋镐身金属套），木柄、绑带、皮革保持原装。

| 等级 | 材质代号 | 中文名 | 外观意图 | PBR 目标（母材质参数） |
| --- | --- | --- | --- | --- |
| 1 | `stone` | 石头刃（出厂） | 打磨石块绑在木柄上，粗粝、无金属感、边缘有崩口 | Metallic 0；Roughness 0.85；BaseColor 灰褐；法线大颗粒 |
| 2 | `bronze` | 青铜（＝现有外观） | 现在这套已认可的青铜／风化金属，作为 2 级基线**原样保留** | 沿用现有 `T_*_BaseColor/Metallic/Roughness/Normal` |
| 3 | `steel` | 钢铁 | 冷灰锻钢，比青铜更亮更硬，磨痕方向沿刃口 | Metallic 1；Roughness 0.35；Tint 冷灰 |
| 4 | `stainless` | 不锈钢强化反射 | 镜面级反射、刃口高光锐利，明确"强化反射"观感 | Metallic 1；Roughness 0.12～0.18；Clear Coat 0.6～0.8（或 Specular 抬升）；Tint 冷白 |
| 5 | `purple_stone` | 紫色强化石 | 紫色矿石质感，非金属但有内透光感，最高档辨识度 | Metallic 0；Roughness 0.45；BaseColor 深紫＋晶粒；Emissive 极弱紫（≤0.15，不做 bloom 特效） |

约定：
- 2 级必须与**当前已认可外观逐像素等价**（同一套贴图、同一 UV），这是"重导出不改变现有观感"的验收基线。
- 4 级的"强化反射"用 Clear Coat（或抬 Specular）实现，不加屏幕空间特效、不加光源。
- 5 级只做材质，**不做**发光粒子／光柱（用户本次未选）。若后续要加，走 `ue5-fluid-vfx-workflow` 的有界池口径，另开授权。

## 3. 数据模型

### 3.1 物品实例字段

写在物品 Data JSON（与 `gunsmith_parts` 同级，**不放进 `gunsmith_parts`**）：

```json
{ "tool_enhance_level": 3 }
```

- 缺省：字段不存在＝1 级。旧存档不需要迁移。
- `NormalizeProductionState` 的定义刷新字段列表**不加**这个键（与 `gunsmith_parts` 同理），否则玩家进度会被出厂定义覆盖。
- 与改造互不干扰：`Installed()`／`Normalize()`／`Calculate()` 都不读它。
- 只有 `tool_axe`、`tool_pickaxe` 认这个字段（`ColdSteelInventory::IsEquippedProductionTool` 口径）；铁铲写了也无效。

### 3.2 目录文件 `Content/ColdSteelData/tool-enhance.json`（新）

```json
{
  "version": 1,
  "metal_slot": "Metal",
  "wood_slot": "Wood",
  "levels": [
    {
      "level": 1,
      "id": "stone",
      "name": "石头刃",
      "description": "打磨石块捆扎成的刃部，粗粝但够用。",
      "materials": { "tool_axe": "/Game/Items/ProductionTools/Enhance20260925/MI_ToolHead_Stone.MI_ToolHead_Stone",
                     "tool_pickaxe": "/Game/Items/ProductionTools/Enhance20260925/MI_ToolHead_Stone.MI_ToolHead_Stone" },
      "cost": {},
      "stats": {}
    }
  ],
  "weapons": [
    { "id": "tool_axe", "traits": [ { "icon": "mechanic", "text": "……" } ] }
  ]
}
```

- `cost` 与 `stats` 本次**恒为空对象**，加载器解析但不使用；后续接入消耗／数值时只改目录与对应系统，不改存档结构。
- `materials` 按工具分开写：斧与镐的金属区面积、磨损方向不同，允许各自指向不同 MI（本次可共用同一批）。
- 目录**不含颜色字段**：角标色统一走现有 `ColdSteelUI::Enhanced`，理由见第 6 节。
- `weapons[].traits` 给浮窗「特殊性质」段，说明强化只改外观、不影响采集与自卫数值（**在数值接入前必须如实这么写**）。

### 3.3 C++ 侧（设计，不在本次实现）

```cpp
// Production/ProductionToolEnhance.h（新）
struct FToolEnhanceLevel { int32 Level=1; FString Id,Name,Description; TMap<FString,FString> Materials; };
namespace ColdSteelToolEnhance
{
    int32 MaxLevel();
    int32 Level(const FColdSteelItem& Item);                 // 缺省 1，夹在 [1, MaxLevel]
    const FToolEnhanceLevel* Find(int32 Level);
    FString MetalMaterialPath(const FColdSteelItem& Item);   // 找不到返回空 → 保持现状
}
// Production/ProductionToolAppearance.h（新）：唯一的外观落地点
namespace ProductionToolAppearance
{
    void ApplyLevel(UStaticMeshComponent* Mesh, const FColdSteelItem& Item);    // 世界／掉落／工作台预览
    void ApplyLevel(USkeletalMeshComponent* Mesh, const FColdSteelItem& Item);  // 第一人称视模
}
```

**按槽名找材质索引，不按固定索引**（`GetMaterialIndex("Metal")`／`Mesh->GetMaterialSlotName(i)`），LOD 与槽序变化都不会错位。找不到 `Metal` 槽时**静默保持现状**并只 log 一次——这样代码可以先于资产落地，重导出未完成时游戏不报错、不换错材质。

## 4. 资产方案：Blender 重导出拆材质槽

### 4.1 现状（已核对 uasset）

| 呈现 | 资产 | 材质槽 |
| --- | --- | --- |
| 世界／掉落／背包图标 | `SM_BattleAxe` | **1 个**：`Material_001` → `M_BattleAxe` |
| 世界／掉落／背包图标 | `SM_RusticPickaxe` | **1 个**：→ `M_RusticPickaxe` |
| 第一人称视模 | `SK_Harvest_Axe` | 3 个工具槽：`M_Harvest_Axe`、`M_Harvest_Axe_001`、`M_BattleAxe`（＋Manny 手臂 `MI_Manny_01/02`） |
| 第一人称视模 | `SK_RusticPickaxe` | 1 个工具槽：`M_RusticPickaxe`（＋Manny 手臂） |

两件工具都来自用户提供的 Meshy AI 单体网格（斧 `Meshy_AI_Weathered_Battle_Axe_0918025738_texture.fbx`、镐 `Meshy_AI_Rustic_Mountaineering_0919083808_texture.glb`），金属与木柄**画在同一套贴图里**，没有分区蒙版、没有多材质槽。所以"只换金属部分"必须先拆槽。

> 上表材质槽来自离线读取 uasset 名称表（`SM_BattleAxe` 明确是单槽 `Material_001`；`SK_Harvest_Axe` 名称表出现 3 个工具材质引用）。视模的**实际槽数与槽序**在动资产前需在编辑器里核对一次，名称表不等于槽列表。

### 4.2 拆槽流程（每件工具同一套）

1. 打开作者源：斧 `SourceAssets/BattleAxeReplace20260919/`（`Original/Meshy_..._texture.fbx` ＋ `Fitted/BattleAxe_{8000,16000,32000,LOD1,LOD2}.fbx`）；镐 `SourceAssets/RusticPickaxe20260919/`（`RusticPickaxe_TwoHand_Editable.blend` ＋ `Export/RusticPickaxe_{World,LOD1,LOD2,Viewmodel}.fbx`）。
2. 新建本轮作者目录 `SourceAssets/ToolEnhance20260925/`，脚本化选面（沿用 `RusticPickaxe20260919/author_two_hand.py`、`BattleAxeReplace20260919/fit_battle_axe.py` 的做法）：
   - 对每个面取 UV 中心，采样现有 **Metallic 贴图**（斧 `T_BattleAxe_Metallic`、镐 `T_RusticPickaxe_MetallicRoughness` 的 R 通道），阈值 ≥0.5 归入金属区；
   - 金属区面片赋新材质槽 `Metal`，其余赋 `Wood`；
   - 输出选面统计与包围盒到 `material-regions.json`（与 `SourceAssets/ProductionToolMaterials20260913/material-regions.json` 同格式，便于复核与回溯）。
3. **人工复核边界**：固定箍、铆钉、绑带、刃口高光属于哪一区必须逐个确认；阈值选面在 AI 网格上会有锯齿状边界，需要按法线／连通域平滑（`select linked` ＋ 手动补删），并把最终面数与归属写进 `authoring.json`。
4. 重新导出（保持现有三角面档位与 LOD 不变，只多一个材质槽）：
   - 斧：`BattleAxe_16000`（世界）、`LOD1`、`LOD2`、视模网格；
   - 镐：`World`(32k)、`LOD1`(8k)、`LOD2`(2k)、`Viewmodel`(96k)；
   - UV、顶点色、骨架绑定、挂载角度（`mount_pitch/yaw/roll`）、`tool_scale` **一律不动**；重导出后必须核对 `source_dimensions.json` 的尺寸与挂载点未漂移。
5. 材质资产（新目录 `Content/Items/ProductionTools/Enhance20260925/`）：
   - `M_ToolHead_Master`：母材质，参数 `BaseColor/Normal/Roughness/Metallic` 贴图 ＋ `Tint`(Vector) ＋ `RoughnessScale` ＋ `ClearCoat` ＋ `Emissive`；
   - `MI_ToolHead_Stone / _Bronze / _Steel / _Stainless / _PurpleStone`：5 个实例，`_Bronze` 直接指向现有贴图，保证 2 级＝现状；
   - `M_ToolWood_*`：木柄槽材质。优先**直接沿用现有 `M_BattleAxe`／`M_RusticPickaxe` 作为 Wood 槽材质**（它们本来就是整套外观），只有当木柄需要与金属区解耦时才新建；
   - 贴图来源优先级：工程内已有 PBR（`Items/ProductionTools/Materials/T_Production_MetalColor|MetalNormal|WoodColor|WoodNormal`、`SourceAssets/ProductionToolMaterials20260913/T_MetalRust_00A_BaseColor.png`、`T_WoodSurface_00A_BaseColor.png`）→ 不足时按 [asset-model-workflow](../../skills/asset-model-workflow/SKILL.md) 生成（石头、紫石这类不规则粗糙主体优先 5080 路线；不锈钢／钢铁可用程序化磨痕）。新增贴图的来源与许可记进 `AssetSetup.md` 与本轮 `README.md`。
6. 备份与恢复纪律：改动前把被替换的 `SM_BattleAxe`／`SM_RusticPickaxe`／`SK_*`／`M_*` 现状写入 `before-backup.json`（`BattleAxeReplace20260919` 已有同款先例）；确认退役的旧资产按 `trash/<topic>-YYYYMMDD/` 归档并记散列，不按年龄批量清理。用户 Meshy 源与派生 uasset **不公开提交**（`AssetSetup.md`「双手伐木斧与矿镐」条目已确立该边界）。

### 4.3 重导出后必须逐项核对

- 世界网格、LOD1／LOD2、视模四者的 `Metal`／`Wood` 槽名一致（运行时按名字找）；
- 2 级（青铜）外观与重导出前逐像素等价——这是唯一能证明"拆槽没改变现有观感"的检查；
- 动作不受影响：视模重导出必须保留 `SK_Harvest_Axe_Skeleton`／`SK_RusticPickaxe_Skeleton` 的骨骼与既有 6 段动作（Idle/Equip/Swing/HitRecover/Walk/Run）绑定，不新建骨架；
- 图标：`ue_icon` 是烘焙 PNG（`ProductionTools/axe.png`、`pickaxe_upright.png`），拆槽后**必须用 `BattleAxeReplace20260919/render_icon.py` 同款流程按 2 级材质重烘一次**，否则图标与模型不一致；
- 掉落物／地面摆放复用同一 `SM_*`，自动跟随；
- 尺寸与占格不变（斧 1×3、镐 2×3），不触发 `ApplyOrientation` 迁移。

## 5. 运行时接入点（设计）

外观落地点必须**只有一处**（`ProductionToolAppearance::ApplyLevel`），调用方：

| 呈现 | 调用点 | 备注 |
| --- | --- | --- |
| 手上／地面世界网格 | `UProductionToolComponent::ApplyToolStats` 内对 `ToolMesh` 调用 | 换实例与同实例改数据两条路径共用，见下方要点 |
| 第一人称视模 | 同一处对 `Viewmodel`（骨骼网格）调用 | 视模在换实例路径重建、在改数据路径保留；`ApplyLevel` 幂等，重复设置同一 MI 无额外开销 |
| 采集提示与挥砍 | 不需要 | 外观与时钟解耦，`RateScale` 不受等级影响 |
| 工作台预览 | `UM4GunsmithWidget::SetStandaloneToolItem` | 草稿等级即时预览；取消／关闭恢复 |
| 掉落物 | 与 `SM_*` 同源，自动 | 无需额外代码 |
| 背包／仓库卡片 | `ColdSteelInventoryPresentation` | 角标见第 6 节 |
| 图鉴 | `ColdSteelCodexPage` | 展示**阶梯表**，不展示某个实例的等级 |

**关键实现要点（容易漏，已核对现有源码）**：`UProductionToolComponent::RefreshHeldTool` 有三条路径——① `Id` 与 `DataHash` 都没变直接 return；② 同实例只改数据 → `EquippedDataHash=DataHash; ApplyToolStats(Item,Profile); return;`（改造应用走这条，保留已加载资源不闪帧）；③ 换实例 → 清空并重新请求资源。强化等级写在物品 Data 里，因此改等级必然改变 `DataHash` 并落到路径 ②。**所以 `ApplyLevel` 必须放进 `ApplyToolStats`（路径 ②③ 都会调用），不能只挂在路径 ③ 的资源加载完成回调之后**，否则"应用强化"后手上工具不换材质。

**不得用换网格的方式做强化**：`tool_mesh` 在 `NormalizeProductionState` 的定义刷新白名单里（与 `tool_scale`、`mount_*`、`ue_icon` 等同列），任何按等级改写的 `tool_mesh` 都会在下次读档时被出厂定义覆盖。本设计只换材质槽的材质实例，不碰网格、不碰挂载角度、不碰占格。同理，`tool_enhance_level` **不进**该白名单（与 `gunsmith_parts` 一样属于玩家进度）。

刷新时机：`ApplyColdSteelProfile` → `RefreshHeldTool`（每次 profile 发布），与改造应用共用同一条链，因此"应用"后立刻生效，不需要额外事件。

性能：材质实例是**共享资产**（5 个 MI 常驻），`ApplyLevel` 只做 `SetMaterial(SlotIndex, MI)`，不新建动态材质实例、不加载贴图；等级读取是物品 Data 的一次 JSON 解析，已由 `RefreshHeldTool` 的 Id＋DataHash 缓存挡住重复调用，符合 [性能开发约束](../../skills/ue5-performance-packaging/references/fpsgame-performance-development.md)。**不得**为每件工具建 `UMaterialInstanceDynamic`（会造成每实例材质与着色器变体膨胀）。

## 6. 图标等级角标

物品卡四角占用已核对 `ColdSteelInventoryPresentation.cpp`：

| 位置 | 现有占用 | 工具卡实际情况 |
| --- | --- | --- |
| 左上 | 物品名芯片（`Name` 为真时） | 占用，不动 |
| 右上 | 强化光晕 `DrawProcessingCorner`，色 `ColdSteelUI::Enhanced` | **复用**：`tool_enhance_level>=2` 时点亮 |
| 右下 | 加工光晕 `Crafted` ＋ 堆叠数量（`Count>1`） | 空闲（工具不产生 `_craftData`，且不可堆叠） |
| 左下 | 附魔光晕 `Enchanted` | 空闲（`CanEnchant` 只接受 firearm／weapon，工具永远不附魔） |

- **等级数字**：程序化文本芯片画在**左下角**，文案 `Lv.N`，字体走 `GunsmithUI::NumberFont`（JetBrains Mono，与堆叠数量同字号档 12），底色沿用数量芯片的 `Gray(10,220)` 圆角盒；不烘焙进 PNG（UI-WORKFLOW §6：图标图内不烘焙文字）。
- **出厂即 1 级也显示 `Lv.1`**：石头与青铜外观差别大，玩家需要能在背包里分辨；右上光晕则只在 ≥2 级点亮，保持"加工过"的语义与武器一致。
- **不按档位分色**：光晕统一用现有 `ColdSteelUI::Enhanced`。稀有度色是 6 档语义色（common 银灰／uncommon 绿／rare 蓝／epic 紫／mythic 金／legendary 粉红），只有 epic 紫与 5 级紫石巧合，mythic 金与 4 级不锈钢并不相符；挪用会让稀有度与强化两套语义混淆。若确实要按档位分色，属于正式设计规则变更，需在 [冷钢 UI 正式规则](../UI/ui-cold-steel-design-system.md) 新增"工具强化档位色"条款并由用户授权，本次不做。
- 浮窗与图鉴：浮窗标题元信息追加「强化 Lv.N · 材质名」（与武器「已强化 +N」同一位置口径，`ColdSteelItemTooltipLayout.cpp` 的 Meta 串）；图鉴「采集工具数值」段附一张 1～5 级材质阶梯表（图鉴读出厂 Probe，没有实例等级，不显示某个实例的档位）。

## 7. 阶段划分

| 阶段 | 内容 | 交付判定 |
| --- | --- | --- |
| 0（本次） | 设计文档 ＋ UI 栏目规划 | 用户确认阶梯、字段、拆槽路线 |
| 1 数据与代码骨架 | `tool-enhance.json`、`ProductionToolEnhance`／`ProductionToolAppearance`、`tool_enhance_level` 读写、工作台第五栏、图标角标、浮窗／图鉴文案 | 原生构建通过；**资产未到位时按"找不到 Metal 槽→保持现状"降级，不报错** |
| 2 资产拆槽与材质 | Blender 选面拆槽、重导出世界／LOD／视模、5 个 MI、2 级等价核对、图标重烘 | 2 级与现状等价；1／3／4／5 级在设计稿范围内 |
| 3 数值与消耗（**需另行授权**） | `cost`／`stats` 落地，接入 `ColdSteelTool::Evaluate` 与报价 UI | 另开设计，本次不预设任何数值 |

阶段 1 与 2 可并行：代码有降级路径，资产晚到不阻塞。

## 8. 风险与未决

1. **AI 网格选面边界**：Meshy 单体网格的金属／木柄交界处没有硬边，阈值选面会锯齿；需要人工复核与连通域平滑，可能要多轮。若最终边界不可接受，回退方案是"蒙版母材质"（用 Metallic 阈值在着色器里混材质，不动网格）——本轮不采用，但保留为退路。
2. **视模槽位**：`SK_Harvest_Axe` 现在有 3 个工具材质槽，重导出后需要明确哪个槽是金属、哪些合并为 Wood，否则第一人称与第三人称档位不一致。
3. **2 级等价性**：拆槽会改变材质边界处的采样（原本一张贴图跨金属／木柄连续），可能出现接缝。设计上要求 2 级沿用原贴图与原 UV，接缝只可能出现在槽边界，需要一次并排比对。
4. **图标重烘**：`ue_icon` 是 PNG，拆槽后若不重烘，背包里 2 级工具与模型不一致；重烘需要编辑器/离线渲染批次（走 `Tools/AssetPipeline/mcp_call_codex.ps1` 的批次互斥）。
5. **等级规则（用户 2026-09-25 确认，不再待决）**：逐级 +1、不可降级、不可跳级。本次无消耗，因此「应用」只在草稿＝当前等级+1 时可用；比当前高的第 2 档及以上在 UI 上禁用并给「需先强化到 Lv.N」，当前档标「已装备」且不可再选。后续接入消耗只增加报价与扣除，不改这条交互规则。核对 3／4／5 级材质时改用调试入口（离线自检或临时命令）而不是放开选择规则。
6. **未纳入**：铁铲、5 级发光特效、强化数值、强化消耗、强化的音效／命中反馈差异。铁铲除用户本次未选之外还有客观障碍：它的网格是第三方包资产（`/Game/MilitaryTrench/Assets/3D/Ind_Mine_Tool_Shovel_Old_01`），`SourceAssets` 里没有作者源，拆材质槽等于改动无源第三方资产，许可与可恢复性都不如斧镐；若后续要纳入，应先确认许可或改走蒙版母材质路线。

## 9. 本次交付状态

只产出设计文档（本文件与 UI 栏目规划）。未修改源码、未改动资产、未运行构建、未启动编辑器或游戏，未测试。

---

> 以下第 10 节为**实施记录**，在设计确认之后追加。第 1～9 节的设计条款未被改写；实施中与设计有出入的地方在第 10 节显式标注。

## 10. 阶段 1 实施记录（2026-09-25）

阶段 1（数据与代码骨架）已分 1-A／1-B／1-C／1-D 四次落地。本节如实记录实际落地的内容，**不声称任何实机测试或验收**——编辑器未启动、PIE 未运行、无截图。

### 10.1 已落地的文件与功能

**新增**

| 文件 | 内容 |
| --- | --- |
| `Content/ColdSteelData/tool-enhance.json` | 等级阶梯目录：`version=1`、`metal_slot="Metal"`、`wood_slot="Wood"`、5 级（stone／bronze／steel／stainless／purple_stone）、`weapons` 两条 traits。每级 `cost`／`stats` 恒为 `{}`。 |
| `Source/FPSGAME/Production/ProductionToolEnhance.{h,cpp}` | 目录加载器：`Levels()`／`MaxLevel()`／`MetalSlotName()`／`Find()`／`Level()`／`CanEnhance()`／`MetalMaterialPath()`／`LevelName()`。静态惰性加载一次，失败保持空目录并只 log 一次。`cost`／`stats` 刻意不解析也不暴露。 |
| `Source/FPSGAME/Production/ProductionToolAppearance.{h,cpp}` | **唯一外观落地点**：`ApplyLevel(UStaticMeshComponent*)`／`ApplyLevel(USkeletalMeshComponent*)`。按槽名找材质索引，只 `SetMaterial`，不建 MID。 |
| `Source/FPSGAME/UI/M4GunsmithEnhance.cpp` | 工作台第五栏全部 UI 逻辑（档位卡、草稿、应用、预览同步、详情行）。 |
| `Tools/Production/check_tool_enhancement_consistency.py` | 强化目录离线自检（见 10.4）。 |

**修改**

| 文件 | 内容 |
| --- | --- |
| `Production/ProductionToolComponent.cpp` | `ApplyToolStats` 内对 `ToolMesh` 与 `Viewmodel` 各调用一次 `ApplyLevel`（覆盖 `RefreshHeldTool` 路径 ②③）；异步资源到位回调内 `SetMesh` 之后补一次。 |
| `Weapons/GunsmithSystem.{h,cpp}` | 草稿等级 `DraftEnhanceLevelValue`、`SetDraftEnhanceLevel`（只接受当前 +1）、`Pending` 计入草稿、`Apply` 在同一次 `CommitState` 事务里写 `tool_enhance_level`、`Undo`／`Close`／`Begin` 清零。 |
| `UI/M4GunsmithWidget.h`、`M4GunsmithLayout.cpp`、`M4GunsmithOverview.cpp`、`M4GunsmithSelectedDetails.cpp`、`M4ToolGunsmith.cpp`、`M4MeleePreview.cpp`、`SMeleePartIcon.h` | 左 Rail 追加「强化」项、选项区显式标题、右侧总览段与详情行、预览随草稿换材质、栏目矢量图标 `enhance` 分支。 |
| `UI/ColdSteelInventoryWidget.h`、`ColdSteelInventoryPresentation.cpp` | 展示结构体新增 `ToolEnhanceLevel`；右上光晕在 ≥2 级点亮；左下 `Lv.N` 芯片。 |
| `UI/ColdSteelItemTooltipData.cpp` | 工具分支 Meta 追加「强化 Lv.N · 材质名」。 |
| `UI/ColdSteelCodexPage.cpp` | 「采集工具数值」段后追加「工具强化材质阶梯」卡（1～5 级材质名 ＋ 外观说明）。 |

### 10.2 与设计条款的差异（需知悉）

1. **总览数值行**：本文件第 5／6 节与 UI 栏目规划对右侧总览的采集／自卫数值行措辞不同（规划写「全部显示 —」，本文件要求「既有行保持不变」）。实施采取后者：保留既有改造数值行原样，另加「强化不影响数值」一行。理由是把既有改造件收益改成「—」会让玩家看不到改造本身的效果。若要改为前者，需明确授权。
2. **键集合自检口径**：加载器**不读取** `cost`／`stats`（设计上就是「解析但不使用」的降级写法——本次连解析都不做）。因此离线自检对这两个键单独走「必须为空对象」的断言，其余键才与加载器读取键逐字比对。
3. **`Lv.N` 芯片位置**：落在左下角、`Gray(10,220)` 圆角盒、字号档 12，与数量芯片同款；工具不可堆叠（Count 恒 1），不会重叠。出厂 1 级也显示 `Lv.1`，光晕则只在 ≥2 级点亮。
4. **额外改动**：`ColdSteelInventoryWidget.h` 追加了 `friend class UColdSteelInventoryVisualAudit;`——既有审计文件是从 `UColdSteelHUDWidget`（已是 friend）访问 `Presentation` 的，为让审计也能读新字段而补齐；不改变任何既有可见性。

### 10.3 构建结果

| 阶段 | 命令目标 | 日志 | 结果 |
| --- | --- | --- | --- |
| 1-A | `FPSGAME Win64 Development` | `Saved/BuildEditor/build-enhance-A.log` | 本任务文件编译通过（零诊断）；整体 Failed，原因当时是并行会话既有错误，非本任务文件 |
| 1-B | 同上 | `Saved/BuildEditor/build-enhance-B.log` | Succeeded，已到 Link |
| 1-C | 同上 | `Saved/BuildEditor/build-enhance-C.log` | Succeeded，已到 Link |
| 1-D | 同上 | `Saved/BuildEditor/build-enhance-D.log` | 见 `Saved/Production/tool-enhance-phase1-report.md` 阶段 1-D 段 |

构建统一用 Game 目标（`Build.bat FPSGAME Win64 Development`），**未使用** `Tools/Build/Build-Editor.ps1`（编辑器进程占用时会抛错）。

### 10.4 离线自检

`Tools/Production/check_tool_enhancement_consistency.py`（新，与已通过的 `check_tool_modification_consistency.py` 并列，未改动后者）。报告写 `Saved/Production/tool-enhance-report.txt`。断言范围：目录结构／版本、等级阶梯恰 5 档且 id 固定、材质路径形式、`cost`／`stats` 必须为空、traits 必须如实写「不影响数值」、**目录键集合与 C++ 加载器读取键逐字对齐**、`CanEnhance` 仍是逐级 +1（防后续被改成跳级）。

### 10.5 材质资产未制作导致的降级行为

`Content/Items/ProductionTools/Enhance20260925/` 目前**不存在**，目录里的材质路径指向尚未制作的资产。阶段 1 的降级链（三层，各有独立 `static` 守卫，只 log 一次、不刷屏、不弹窗）：

1. 路径为空串（未登记工具，如铁铲）→ 直接返回，保持现有材质；
2. `LoadObject` 返回 null（资产未制作）→ 保持现有材质并 log 一次；
3. 网格上找不到 `Metal` 槽（`SM_BattleAxe`／`SM_RusticPickaxe` 当前是单槽，尚未拆槽）→ 保持现有材质并 log 一次。

因此**阶段 1 的视觉效果是"代码已接、视觉未变"**：工作台预览与手上工具的换材质在当前资产状态下不会产生可见变化，这是设计内的降级，不是缺陷。拆槽与 5 个 MI 属阶段 2。

### 10.6 未实现项

- **阶段 2 全部内容**：Blender 选面拆槽、世界／LOD／视模重导出、`M_ToolHead_Master` ＋ 5 个 MI、2 级等价性核对、`ue_icon` 重烘。
- **阶段 3（需另行授权）**：`cost`／`stats` 落地、接 `ColdSteelTool::Evaluate` 与报价 UI。当前 `cost`／`stats` 恒空、UI 显示「待定」／「—」，**无任何假数字**。
- **明确未纳入**：铁铲、5 级发光特效、强化音效／命中反馈差异。
- `Lv.N` 未进浮窗图标角标以外的位置；`check_tool_modification_consistency.py` 未扩展（另建了新脚本）。

### 10.7 未做实机测试

**本阶段未启动 UE 编辑器、未跑 PIE、未截图、未做任何实机验证或验收。** 上文所有行为陈述（角标绘制、浮窗文案、降级链、换材质时机）均为**代码层面结论**，由 Game 目标构建的编译／链接结果与离线自检脚本支撑，不代表运行时观感。视觉与交互验收由用户自行进行。

## 11. 阶段 2 实施记录（2026-09-25）

执行方式：编辑器当时已关闭，全部 UE 侧操作走 **headless commandlet**（`UnrealEditor-Cmd -run=pythonscript -unattended -NullRHI`），Blender 侧走 `--background` 独立进程；未启动 GUI 编辑器、未跑 PIE。回执：`SourceAssets/ToolEnhance20260925/ue-install-receipt.json`、`ue-viewmodel-receipt.json`、`ue-icon-receipt.json`；日志在 `Saved/Production/tool-enhance-*.log`。

### 11.1 拆槽与选面规则（沿用阶段 2 前置分析）

纯 Z 切：面心 `z >= z_cut`（斧 0.195、镐 0.315，拟合网格局部坐标）。最终占比：斧 4111/16000、641/2500、130/600；镐 7599/32000、2057/8000、527/2000；导出后包围盒漂移 0.000000。已知取舍：斧柄顶端少量面落入金属槽（读作金属端帽），不做形态学清理（清理会误删镐头细岛）。脚本 `split_tool_material_slots.py`，区域记录 `material-regions.json`，评审渲染 `Saved/Production/tool-enhance-split-*.png`。

### 11.2 阶段 A：母材质与实例

`M_ToolHead_Master_{Axe,Pick}` ＋ 8 个 `MI_ToolHead_{Axe,Pick}_{Stone,Steel,Stainless,PurpleStone}` 落在 `Content/Items/ProductionTools/Enhance20260925/`。UE 5.8 的实例参数设置挂在 `MaterialEditingLibrary.set_material_instance_*_parameter_value`（对象方法已移除，探针 `ue_probe_mi_api.py` 确认）；母材质与实例均 `used_with_skeletal_mesh=True`（实例继承父材质使用标志）。

### 11.3 阶段 B：世界网格

两个静态网格**删除后全新导入**（重导入会保留旧槽：镐曾出现 `[M_RusticPickaxe, Metal, Wood]` 三槽，旧槽索引与面索引对应关系不可靠），与 `install_battle_axe.py` 原流程一致；`AssetImportTask.save` 必须为 True（commandlet 退出丢弃未保存包，首跑因此整次丢失）。导入后槽名恰为 `[Metal, Wood]`，`import_lod` 补 LOD1/2，屏幕尺寸 `[1.0, 0.35, 0.1]`，nanite 关，`Metal`←1 级石制 MI、`Wood`←原木材质；回执 before/after 包围盒逐位一致、LOD 3 级。

### 11.4 阶段 C：视模

在可编辑 blend 上解析复现世界网格的 Z 切：放置变换为 `v = R @ (fitted − origin)`，故 `(R⁻¹·v).z >= z_cut − grip_z` 即金属面（`R`＝WPN_root rest 矩阵，`grip_z=−0.26`）。占比斧 8088/32000（25.27%）、镐 22784/95999（23.73%，视模网格密度高于世界网格），与世界网格占比吻合。拆槽 blend 与 SK FBX 写到 `SourceAssets/ToolEnhance20260925/Viewmodel/`，**不改动已认可的作者源 blend**。UE 侧同样全新导入：槽 `[Wood, Metal, MI_Manny_01, MI_Manny_02]`，手臂材质从旧 SK 按名继承，`Metal`←石制 MI、`Wood`←原木材质，骨架资产原路径保存，±80 包围盒扩展保留。阶段 1 的 C++ 按目录 `metal_slot` 名找槽，视模无需改代码即接通。

**保存事故与修复（同日）**：首跑阶段 C 后用户实机发现视模金属槽是 WorldGridMaterial（镐头在白色测试场里读作"消失"、轴身无贴图观感）。根因：`AssetImportTask.save=True` 先把**导入态**落盘，随后的槽绑定用 `EAL.save_asset()` 保存但**未检查返回值**——该 API（及 `save_loaded_asset`）在 PIE 期间静默返回 false，绑定从未落盘。修复：在运行中的编辑器里重绑两个 SK 的 Metal/Wood 槽，改走 `EditorLoadingAndSavingUtils.save_packages([pkg], False)`（返回 true、uasset mtime 更新），并用独立 commandlet 回读盘上槽材质确认四个资产（2 SK＋2 SM）全部正确。`ue_install_viewmodel.py` 已加固为 save_packages＋回读校验，不回读一致即 raise。教训：**任何 UE 保存调用必须检查返回值或以 mtime/回读为准**，PIE 期间尤其。

**手模系统按索引隐藏槽（同日第二事故）**：材质落盘后用户仍报"斧刃、镐头缺失"。真凶是 `Content/ColdSteelData/modular_outfits.json` 里两个工具视模档的 `hide_source_materials: [1,2]`——`FPSModularOutfitComponent` 按**索引**对源视模逐 LOD `Section(Source,M,L,false)` 隐藏手臂槽（旧布局 `[tool, Manny01, Manny02]` 里手臂＝1,2）。拆槽后布局变 `[Wood, Metal, Manny01, Manny02]`，[1,2] 就把 **Metal** 和一只手臂槽隐藏了。修复为 `[2,3]`（工作副本已含该改动，本文核对过语义：`Tools/ModularOutfit/export_bare_family_sources.py` 也用同一数组从源网格抽手臂面，新布局下 2,3 同样正确；派生手臂网格 `SK_*_BareArmsV7` 不受影响）。`shirt_covers`/`glove_covers` 索引指向派生 base 网格自身槽，未动。教训：**拆槽会平移下游所有按索引引用槽的数据**（手模隐藏、覆写表），拆槽交付前必须全局搜索引引用；该 json 为运行时读取，改后需重启 PIE/游戏生效。

**v2 语义重拆（同日第三轮，取代上文 v1 占比数字）**：用户反馈 v1 纯 Z 切把镐前端绳缠与木棍也划进 Metal。数据分析（`SourceAssets/ToolEnhance20260925/resplit-analysis.json`）：绳缠/木棍连通域 metallic≈0.001、金属头是独立连通域（metallic_mean 0.19–0.78）、穿出头顶的木帽 chroma 0.18–0.30；斧为焊接单连通域但 chroma 可分（柄 0.27–0.30、头 ≤0.15）。v2 规则：镐＝连通域规则（metallic_mean≥0.15 且 chroma_mean≤0.16 且 z_min≥0.33）；斧＝逐面（z≥0.195 且 chroma<0.20 或 metallic>0.2），见 `split_tool_material_slots_v2.py`／`split_viewmodel_slots_v2.py`（视模用 `(R⁻¹·v).z + grip_z` 还原世界 z 后套同一规则）。金属占比斧 22.7%（v1 25.7%）、镐 9.3%（v1 23.7%），视模 22.5%/8.8% 与世界一致；复核渲染与重烘图标均通过语义判读。世界网格与视模的 UE 重装在**编辑器关闭后的 commandlet 窗口**执行（见下条）。

**活编辑器与 commandlet 的资产写边界（同日教训）**：运行中的编辑器持有 .uasset 文件锁，外部 commandlet 删除/覆盖报 Error 32；活编辑器里 `StaticMeshEditorSubsystem.import_lod` 异步生效（恒返回 -1、后续 tick 才落地），失败批次排队的任务还会污染同路径重新导入的包。结论：**整包替换安装（删＋全新导入＋LOD）必须在编辑器关闭后的 commandlet 窗口执行**；活编辑器桥只用于槽绑定、save_packages 等短操作。

### 11.5 阶段 D：图标重烘

`render_tool_icons.py` 按原图标脚本的相机／灯光／分辨率（斧 256×768、镐 512×768、AgX、正交）重烘；木槽原 PBR，金属槽近似石制 MI（去饱和 0.85、乘 tint (0.42,0.40,0.37)、粗糙度 ×1.7 钳位、金属度 0）。旧 PNG 备份进 `Before/` 并记散列后覆盖 `Content/ColdSteelData/ProductionTools/{axe,pickaxe_upright}.png`，UE 纹理 `replace_existing` 重导保存。斧旧图标的真实备份来自作者源 `AxeImpactInventory20260919/axe_upright.png`（一次失败运行曾把新图误备为"旧图"，已用源文件修正记录）。

### 11.6 校验与备份

`check_tool_enhancement_consistency.py` 扩展：材质路径接受裸包路径与 `/Game/…/X.X` 两种形式；2 级必须指向原材质（等价基线）；其余各级路径与命名固定；`metal_slot/wood_slot` 必须为 Metal/Wood；**所有材质资产必须真实落盘**。当前 0 问题。备份清单 `before-backup.json` 共 8 条（6 个网格 FBX ＋ 2 个图标 PNG），原件在 `SourceAssets/ToolEnhance20260925/Before/`。

### 11.7 未做实机测试

与阶段 1 相同口径：**未启动 GUI 编辑器、未跑 PIE、未截图验收**。commandlet 回执只证明资产落盘与槽位绑定正确；出厂外观（石制头）、等级切换观感、图标在库存/工作台的实际显示由用户自行验收。阶段 3（cost/stats）仍未授权、未实现。
