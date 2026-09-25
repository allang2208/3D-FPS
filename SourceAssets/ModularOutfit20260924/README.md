# 模块化长袖与手套：作者工程

**当前入口（2026-09-25）**：默认与新增动画基准已更新为用户认可的 V7 裸手／裸臂；第一人称手套为 FittedFieldGlovesV1，衣袖为 FittedSleevesV1。后续制作读 [标准工作流](../../skills/ue5-fps-arms-animation/references/first-person-equipment-workflow.md)、[工具入口](../../Tools/ModularOutfit/README.md) 和 [恢复／发布说明](../../Docs/Characters/modular-outfit-publication-20260925.md)。

以下保留初始制作和失败迭代历史，不代表当前默认。NativeSkin 的 Body 仍被配置引用，V3／V4／V6 数据仍参与 V7 制作，不能整目录删除。旧 `register_equipment.py`／`register_native_skin.py` 会重建早期配置，不能对当前配置直接重跑；恢复需按版本顺序保留 V7 的原生默认与新装备引用。自动备份及已完成的一次性编辑器操作见发布说明的 trash 清单。

## 历史制作记录

本包保留原武器动作与绑定，以当前实际姿态源生成独立的身体基底、衣袖和手套。第一套款式为连续长袖与短手套，衣服、手套分别占用现有 armor / gloves 槽。没有布料模拟。

未穿戴本套装备时使用原有手模；替换基底仅在穿戴本套上衣或手套时启用。脱下全部本套装备会恢复原模型，取消尚未完成的换装加载。

2026-09-24：21 组 profile 的 63 个骨骼网格及 LOD、材质、掉落模型均已实际导入并保存；四件物品与运行配方已登记。接入记录见 `Docs/Characters/modular-equipment-implementation-20260924.md`。未做游戏测试。

## 作者源和来源

- `Donor/sweater_fisherman.obj`：MakeHuman Community 的 MargaretToigo / MRT fisherman sweater，CC0。来源页和压缩包、mhclo 许可头、SHA-256 保存在 `Donor/`。[原始素材包](https://static.makehumancommunity.org/assets/assetpacks/shirts01.html)。
- `Donor/BareHands/base.obj`：MakeHuman hm08 真实裸手表面；文件头明确 CC0。`default.mhskel` 与 `default_weights.mhw` 均声明 CC0。网址、散列见 `Donor/BareHands/provenance.json`。[原始人体表面](https://github.com/makehumancommunity/makehuman/blob/master/makehuman/data/3dobjs/base.obj)。
- 衣服重新适配 Manny 体型，转移蒙皮，增加布料厚度与袖口内壁。裸手按腕、掌、指关节拟合，保留解剖手型；原始 Manny 手套形状没有用肤色冒充裸手。裸手近腕段与现有前臂几何/权重渐接。
- 手套由拟合后的裸手生成独立薄壳、短腕口与内壁。棕色 / 黑色使用不同材料资源，上衣为橄榄色 / 炭灰色。
- `Inputs/*.fbx` 包含工程已有武器与 Manny 绑定，仅为本工程派生来源；它们及其原材质仍遵循各自原许可，不能因为衣服来源为 CC0 就把整个包标成 CC0。

## 可编辑交付

- `FieldEquipment_Master.blend`：全身长袖作者源。
- `AnatomicalHands_Master.blend`：解剖裸手作者源、当前身体与参考骨架。
- `<RigProfile>_Equipment.blend`：每个实际骨架的独立 Base、Shirt、Gloves。
- `Exports/SK_<RigProfile>_*.fbx`：带蒙皮派生件，保留姿态源的完整骨骼层级。
- `ItemPresentation.blend`、两个 `SM_*_Pickup.fbx`：物品图标与掉落形态。
- `inputs.json` 登记源资源和材质；`authored.json` 登记实际蒙皮侧和制作输出；`imported.json` 仅在 UE 保存成功后登记资源。

## 重新制作顺序

所有脚本在 `D:/FPS3D/FPSGAME/Tools/ModularOutfit/`。

Blender 的 `author_all.py` 可按顺序完成下述第 3–5 步。制作时使用 `--python-exit-code 1`，使脚本错误直接中止批次。

1. `export_sources.py`：从实际工程网格导出参考骨架。已存在的源 FBX 默认保留。
2. `acquire_shirt.py`、`acquire_bare_hands.py`：保留来源与原始许可。
3. Blender 后台运行 `author_equipment.py`，生成连续袖子、初始分区基底。
4. Blender 后台运行 `author_bare_hands.py`，替换裸手并生成真正独立的手套。必须在上一步之后运行；上一步会重建派生 Blend。
5. Blender 后台运行 `author_item_presentation.py`，生成正式库存图标和掉落模型。这是内容制作，不是游戏预览测试。
6. 常规 Editor 构建后，用 `Run-Authoring.ps1 -Script Tools/ModularOutfit/import_all_equipment.py -Log <专用日志>` 后台导入。不要同时运行 FPSGAME 编辑器。采用离屏 RHI：UE FBX 导出不能使用 NullRHI。
7. `register_equipment.py`：全部派生资产保存后登记四个物品及外观配方；不直接改玩家存档。

导入是可续接的：每个成功保存的 profile 单独写入 `imported.json`。重新制作已保存 profile 时，应先将旧输出作为版本保留，并用新的版本目录导入；不要把续接导入误认为强制更新旧网格。

## 后续新增款式

物品拥有权、仓库与存档继续使用现有 Definition。新模型在 `modular_outfits.json.items.<Definition>.rig_meshes` 中逐 profile 指定；同模型仅改配色可以复用网格并指定独立材质。派生缺失时保留当前完整表现，不先隐藏身体。

当前基础分区为 SkinArms / SkinHands / SkinTorso / SkinRest，适用于本套长袖与短手套。短袖、长筒手套或独立护臂需要新增适合其边界的基底分区和覆盖配方，不能直接套用整臂遮挡。

第一人称肩部切口封闭，衣服与手套腕口均有实体内壁。LOD0 保留近景制作网格；LOD1/2 目标三角面比例 50% / 20%，保留边界和骨骼边界。它们是制作参数，不代表实测帧率。

原 FBX 的 Body 手骨世界 basis 含 0.01 单位缩放，而 M4 / PKM / SVD 手骨世界 basis 为 1。顶点已换算成米后，派生计算使用去单位的旋转、平移框架，不能再把两者的完整缩放比套到衣物偏移量上。实际 rig / bind matrix 保持原样，不统一根缩放。

本轮不启动游戏、不截图验收、不执行性能或联机测试。实际抓握贴合、各动作穿插和联机表现由用户后续体验确认。

## 当前默认裸手入口：NativeSkin

默认裸手改用 UE 原生绑定派生资产，替代上方 FBX 重绑基底。现有 Shirt / Gloves 仍为独立装备资源，原武器和动画未修改。

1. `Tools/ModularOutfit/export_native_skin_sources.py` 经现有 MCP 桥提取各源网格原生骨骼及前臂表面，保存到 `NativeSkin/*_source.json`。
2. 后台 Blender 运行 `author_native_skin.py`：保留原布袖和前臂，拟合 CC0 手掌五指，切出闭合腕环并桥接，接缝继承原前臂扭转权重；保存 `*_BareSkin.blend` 与 `*_skin.json`。
3. `import_native_skin.py` 经现有编辑器保存，每批最多 4 组。新资产复制原 UE 参考骨架和逆绑定，仅替换表面；保存后记录 `saved.json`。作者 JSON 散列变化时会重新制作本任务资产。
4. `register_native_skin.py` 在全部资产保存后登记 `base`、`native_bare_skin`、覆盖分区与默认裸手开关。通用 `register_equipment.py` 也保留该入口。

UE 资产目录 `/Game/Characters/ModularOutfit20260924/NativeSkin`。未穿戴上衣时显示保留的原生布袖；手套槽为空时显示皮肤手掌和五指。无额外布料求解或动画状态机。

本次接入当前编辑器采用 Live Coding，结果记录 `native-skin-livecoding-result.json`；不代表基础 Editor DLL 已常规重建。资产保存回执与游戏视觉验收分开，未运行后者。

### 表面导出 v2

用户报告 v1 裸手全黑。根因为坐标转换后多反转了一次三角绕序，面朝向与外向法线相反。`author_native_skin.py` 现生成 `surface_export_version=2`；已制作的 JSON 用 `repair_native_skin_winding.py` 原位迁移后，重新运行分批导入以构建全部 LOD。该迁移保留顶点位置、法线、权重和 UV，不修改原武器、共享皮肤材质或动画。导入读取 `inputs.json` 的正式 profile 清单，不扫描同后缀的配方备份文件。
# 当前状态：M4 写实候选阶段

2026-09-24 后续：用户反馈全局裸手导致多套动画扭曲、穿插，已关闭 `native_bare_hands_default`，未穿戴本套装备时其他武器回到原手模。当前采用单独的 [M4 写实裸手/裸臂候选](RealisticM4Candidate/README.md)，后续已按用户反馈在 `Config/DefaultEngine.ini` 持久化 `fps.Outfit.BareArmsCandidate=1`，M4 默认显示候选。此前 21 个 NativeSkin 资产保留为迭代记录，尚未通过全武器动作确认；下方历史制作完成不等于视觉验收完成。
