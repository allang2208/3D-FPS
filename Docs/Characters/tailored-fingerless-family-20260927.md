# 棕色裁片露指手套：全骨架接入

2026-09-27，用户在代表样件完成后要求继续。承接 `tailored-fingerless-candidate-20260927.md` 的裁片、短腕带和皮革方向，接入现有 `ue_field_gloves`，不新增物品或修改动画。

## 作者源与适配

作者根：`SourceAssets/ModularOutfit20260927/TailoredFingerlessV1/`。

当前范围为 Body、M4、AKM、QBZ191、ASH12、M16、M1911、DW715、A762、SVD、PKM、RuneSword、FrostSword、FrostArms、Axe、Pickaxe、DW715_l/r、M1911_l/r、Traversal、Bow，共 22 套原生骨架适配。

每套以其当前 `FingerlessHuntV2/FullShell` 外皮为拟合输入，保留已有覆盖边界和原生权重，插值内部新增顶点，加入代表样件的裁片起伏。组合网格继续使用同一版本的 `SkinCoverage/<Profile>_review.json` 裸露皮肤；指根及腕口边不另行移动。

同拓扑型号共享代表样件烘焙 UV 和贴图。第三人称 Body 与左手局部封口拓扑不同，分别烘焙；M1911_l 与 DW715_l 共享后者的布局。共 3 组 2048 像素 BaseColor／Roughness／Normal 输入，避免为全部武器复制贴图。材质无皮肤散射、金属度为零；UE 对 OpenGL 烘焙法线翻转绿色通道。

动画由现有主视模提供，装备部件继续使用 Leader Pose。`glove_in_base=true` 让露指皮革与保留的裸露皮肤作为一份组合外观，避免再叠加一份手套。新增独立手套派生也落盘保留，当前穿戴路线使用组合网格。

## 制作与保存入口

1. `Tools/ModularOutfit/author_tailored_fingerless_family.py`：拟合各原生骨架，继承或分类建立烘焙布局。
2. `Tools/ModularOutfit/save_tailored_fingerless_family.py`：烘焙两个特殊布局，保存 22 份可编辑 Blend、穿戴 JSON、对应单只空手套掉落模型。
3. `Tools/ModularOutfit/import_tailored_fingerless_family.py`：保存材质、独立手套与裸露皮肤组合网格，各配置 3 级 LOD；保存掉落模型后，只更新棕色物品的外观引用和正式图标。

UE 家族根：`/Game/Characters/ModularOutfit20260924/TailoredFingerlessV1/`。

每个型号的保存回执为 `Saved/<Profile>.json`；全量已保存清单为 `saved-assets.json`；完成引用切换后生成 `published.json`。中断后按源与材质散列续接已完成型号，不把只有脚本或源文件当成已保存资产。

原生导入期间保留其他 commandlet，由现有桥批次互斥与进程占用条件串行化；不关闭他人进程，不打开编辑器，不发送跨任务协调消息。

## 配置与保留项

仅更新 `modular_outfits.json` 的 `items.ue_field_gloves` 外观字段：`rig_meshes`、`skin_meshes`、`material`、`appearance_family` 等。`items.json` 仅更新该物品的掉落网格和材质，图标路径继续为既有棕色 PNG。发布前保存该物品原配方、目录字段和旧图标到 `BeforePublication/`。

黑色手套、装备 ID、槽位、库存与存档身份、说明快照、既有防御与速度加成不变。此次动画修改数量为 0。

旧物品的 `Data` 包含创建时的目录快照，掉落显示直接读取其中 `world_mesh`／`world_material`。因此在 `ColdSteelProfileRuntime.cpp` 的现有读档迁移中，仅为 `ue_field_gloves` 同步目录的 `ue_icon`、`world_mesh`、`world_material`；字段实际变化才写回，沿用现有 A/B 存档事务。覆盖背包、装备、仓库和地面物品，不直接改写本机存档文件，也不改物品属性或实例 ID。这项代码需对应 Game／Editor 构建完成后生效。

`render_field_glove_icons.py` 已按活动 `appearance_family` 分流，后续棕色图标制作读取当前裁片模型与共用 PBR，避免恢复旧光滑壳。规则同步到项目及个人 `ue5-item-asset-workflow/references/glove-inventory-icons.md`。

配置由下一次游戏会话加载。本轮只做后台制作、烘焙、导入和保存，不启动游戏／PIE，不进行穿插、动画或性能验收；运行表现由用户测试。

## 本轮交付结果

22 套骨架适配、44 个骨骼网格、3 组皮革材质及贴图、单只空手套掉落模型均已通过后台 commandlet 导入并保存；正式棕色装备的外观引用与图标已切换。`published.json` 已记录 `profiles=22`、`active_equipment_changed=true`、`animations_changed=0`、`balance_changed=false`、`runtime_tested=false`。

Game Win64 Development 构建成功，包含 `ColdSteelProfileRuntime.cpp` 的旧物品外观同步修改，记录为作者根下 `build-game-console.log`。Editor Win64 Development 构建亦成功，目标为最新状态，记录为 `build-editor-console.log` 与 `Saved/BuildEditor/build-20260927-114533.log`。这些结果仅代表必要构建和资产落盘完成，不代表运行或穿模验收通过。

下一次启动游戏后将加载正式外观，并在现有读档流程中刷新旧棕色手套物品的外观字段。未启动编辑器、游戏或 PIE，未追加测试。

2026-09-27 用户随后反馈“基本 ok”，并授权整理发布；参见 [手套整理与源码发布](tailored-gloves-publication-20260927.md)。此为用户反馈，本轮未追加游戏测试。
