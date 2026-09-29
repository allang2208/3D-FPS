# 原版战术手套：独立皮革装备

> 2026-09-29 当前外观已为 `TacticalDetail20260928`，图标、烘焙材质和生产入口见 [三款手套细节升级](glove-companion-detail-20260928.md)。以下 V1/V2 为仍需保留的作者依赖与历史接入记录，不作为当前材质回退目标。

2026-09-27 更新。物品仍为 `ue_original_gloves`，显示名“原版战术手套”，手套槽、2×2 格、不可堆叠。此次保留物品身份、价格、稀有度和实例属性。

## 皮革制作路线更新

同日用户明确认可露指款 `TailoredFingerlessV1` 的皮革材质，并要求移到战术手套。后续材质以 `OriginalLeatherV2` 为准，替代下文 V1 的 triplanar/HLSL 材质。保留现有全指几何、原生绑定、动画和独立换衣合同。

新制作链直接复用露指款 `build_tailored_fingerless_candidate.py` 的 `authored_material()`：相同 25 cm 扫描、掌背颗粒、裁片染色、线迹、接触磨亮及 `.42` 高光参数。按战术手套 UV 重新烘焙 BaseColor、Roughness、OpenGL Normal，UE 使用普通法线采样并翻绿；不能直接把露指款的不同 UV 图集贴到全指网格。

第一人称保留现有网格和 UV0，烘焙为 4K 图集；第三人称 Body 的旧 UV 全部折叠在一点，因此单独展开并烘焙 2K，保留其几何和权重。配方的空 `material` 字段让各网格保留自己的材质槽，避免将第一人称图集覆盖 Body。装备图标与 UE 第一人称共用新烘焙贴图，图标保留单只空全指手套构图。

- 作者源：`SourceAssets/ModularOutfit20260927/OriginalLeatherV2/`，含 `Authoring`、`Baked`、`Textures`、可编辑 Blend、FBX 和保存回执。
- 材质及 Body 新资产根：`/Game/Characters/ModularOutfit20260924/OriginalLeatherV2/`；第一人称沿用 V1 手套资产并更新材质槽。
- 制作：`prepare_original_tailored_leather.py` → `bake_original_tailored_leather.py` → `import_original_tailored_leather.py`。V1 的两个制作入口在 V2 发布后转到此链；注册器优先读取 V2 回执。
- 不修改露指款的资产、战术手套平衡或动作。无需新增 C++；运行配置由新游戏会话读取。本轮未运行游戏或验收。
- V2 已保存并接入 22 个骨架配置、两组 PBR 材质和专属图标/掉落模型；接入回执为 `OriginalLeatherV2/published.json`，后台保存日志为 `Saved/original-tailored-leather-commandlet-20260927.log`。Body UV 与 LOD 最终在后台 commandlet 完成保存。未打开新编辑器，未做运行验收。

## 当前穿戴行为

- 使用当前 V7 手型的全指拟合手套，露出当前裸臂。取消该物品旧的 `first_person_mode=source_arms` 配方，不再恢复整套旧衣袖及其材质。
- 上衣和手套独立搭配。覆盖只作用于裸手基底的手部区 2；卸下后由原有装备组件恢复当前手部外观。
- 配方包含 22 个原生骨架系列（含 Body 与 Bow）；LMG201 等使用既有 profile 别名。各系列直接派生自当前已保存的 fitted glove 网格，保留各自绑定、权重及已有 LOD，继续跟随原有动作。
- 第一人称可编辑母版沿用 V7 掌指包络和腕口；这次没有修改裸手母版、源动作或给每件装备复制动画。

## 材质、图标和掉落

原棕皮革继续使用本机已许可的 Quixel `Fabric Generic Leather Top Grain Brown` 扫描，来源见 `SourceAssets/HandEquipmentAppearance/source_maps.json`。新建独立父材质，细化掌背粗糙度差、较细掌面皮纹、暖色缝线和腕口高光，并减轻大面积磨损；黑色及露指款的材质不受影响。

- UE 资产根：`/Game/Characters/ModularOutfit20260927/OriginalLeatherV1/`。
- 独立材质：该目录 `Materials/M_OriginalLeather`。
- 图标：`Content/ColdSteelData/Icons/ModularOutfit20260927/ue_original_gloves.png`，320×320 RGBA，单只空手套、自然分指、透明底，按 91% 几何轮廓构图。图标姿态独立于穿戴动作。
- 掉落模型：该目录 `Pickups/SM_OriginalLeatherGloves_Pickup`，使用本款空手套外形，已导入并保存。
- 资产目录已加入 cook 路径；PNG 沿用 `ColdSteelData` 的既有打包规则。

Blender 图标与 UE 材质复用扫描和分区输入，但两者光照与材质求值不同；没有据此宣称游戏视觉已验收。

## 旧存档与使用

现有存档读取时，`ColdSteelProfileRuntime.cpp` 的外观同步现在包含 `ue_original_gloves`，刷新 `ue_icon`、`world_mesh`、`world_material`。名称与说明沿用已有目录同步机制；数量、位置、装备状态、强化及其他实例数据保持原流程。

重新进入游戏后，在 F6 开发面板的“服装与手套”分类领取“原版战术手套”，也可使用原先已经持有的同 ID 物品。没有自动赠送或直接写玩家存档。运行配置在新游戏会话读取。

## 作者源与重制

作者目录：`SourceAssets/ModularOutfit20260927/OriginalLeatherV1/`。

- `M4_OriginalLeatherV1.blend`：带原生绑定的双手可编辑母版。
- `M4_OriginalLeatherV1.json`：拟合几何与权重源。
- `OriginalLeather_Icon.blend`：单只空手套、灯光与相机。
- `SM_OriginalLeatherGloves_Pickup.fbx`：独立掉落网格源。
- `original_leather.hlsl`：实际保存的材质代码。
- `Saved/<Profile>.json`、`saved-assets.json`、`published.json`：逐资产保存和最终接入回执。
- `before-publication.json`：旧物品及旧配方快照。

制作入口为 `Tools/ModularOutfit/save_original_leather_gloves.py`（Blender 后台）；接入入口为 `import_original_leather_gloves.py`（通过 `Run-Authoring.ps1` 的后台资产窗口）。共用参数为 `original_leather_gloves.py`。注册器 `register_original_gloves.py` 现在读取已发布配方，不再创建恢复衣袖的旧配方；历史 `register_equipment.py` 不应拿来重建整个当前换装目录。

## 本次交付状态

可编辑源、PNG、FBX、22 个原生手套网格、独立材质、掉落资产及运行配置均已保存。普通 Editor DLL 已完成必要构建，记录为 `Saved/BuildEditor/build-20260927-222038.log`；资产制作记录为 `Saved/original-leather-import-20260927.log`。

未主动打开交互 UE 编辑器，未启动游戏、PIE、动作检查、截图、存档回归或打包测试。仅制作了用户要求的装备图标。穿戴、切枪、换衣、握持和读档效果由用户测试；后台构建及保存不代表这些运行效果已经通过验收。
