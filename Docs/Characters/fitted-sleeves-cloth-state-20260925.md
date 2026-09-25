# 衣袖贴合与巫婆布料接入状态

用户要求优化衣服与手臂、袖口的匹配，并检查是否加入此前巫婆的布料物理。沿用已认可的 V7 裸手、裸臂基准，不修改其形状或动作。

## 查到的现状

后台读取当前衣服和巫婆网格的 `mesh_clothing_assets`：21 个衣服配置（20 个第一人称及 Body）的衣服资源均为 0 个；当前 `SK_WitchRebuilt` 有 `LowerDrape07`、`UpperDrape07` 两个布料资产。记录为 `SourceAssets/ModularOutfit20260925/FittedSleevesV1/cloth-state-before.json`。这是资产检查，没有运行模拟。

`FPSModularOutfitComponent.cpp` 通过 `SetLeaderPoseComponent(Source)` 让衣服跟随源手臂骨骼，随后 `SetComponentTickEnabled(false)`；当前衣服没有独立的布料模拟更新。原 `author_equipment.py` 的衣物厚度来自 Solidify，属于几何厚度，不是实时物理。

巫婆的实际实现见 `WitchRebuiltAuthoring.cpp`、`WitchRebuiltClothingAsset.h`、`WitchRebuiltMonster.cpp`：显示衣物由独立低密度代理驱动；肩口、袖口等固定，身体使用专用碰撞形体；专用 ClothingAsset 在重新绑定时处理不稳定的重心映射。当前上袍配置为目标 4 次迭代、最多 6 次、1 子步，不开 CCD 和自碰撞；运行时按 20/24 m 迟滞及 0.35 秒混合处理暂停、恢复。这些是巫婆参数，不能直接照搬到贴近相机的玩家袖口。

## 本次袖口制作

读取现有 M4 毛衣网格后发现，旧袖口最前端沿前臂方向超过腕关节约 2.64 cm，进入手掌附近；V7 保留腕部皮肤的分界在腕关节后约 4.33 cm。旧袖口与现有裸手分区不匹配。

- 保留既有毛衣的上臂造型、主体 UV 与材质，从腕关节后 13 cm 处重建末段前臂和袖口。
- 仅焊接本次重建段的重合接缝。初次制作时整体焊接误合并了肩部独立封口，UE 拒绝部分三角形；已限制焊接区域并保留上臂原有面角法线。导入在三角形被拒绝时直接停止，避免继续保存缺面资源。
- 新袖口末端位于腕关节后约 3.68 cm；与保留的腕部皮肤／手套区重叠 6.5 mm，避免直接对接形成缝隙。
- 按当前裸臂腕围建立收口，内侧留约 3 mm 余量，已有内外层间保持 2 mm 布料厚度，并连接端面。没有再次整体加厚。
- 渐变区保留小幅压缩褶皱；袖口蒙皮从对应侧裸臂表面用三角形重心插值转移，向原前臂权重平滑过渡。
- 以同一母版生成 20 个第一人称原生骨架派生，包括参考姿态不同的 ASH12、M16 及双持左右侧。保留各原生骨架与动作，不新增动画。
- 绿色 `ue_field_sweater`、炭灰 `ue_field_sweater_charcoal` 共用新衣袖外形，保留各自已有材质。第三人称 Body 毛衣、原版战术手套恢复入口和存档不在本轮重制范围。

## 布料物理处理

**本次没有为玩家毛衣新增 Chaos 布料。** 用户要求的现有接入状态已经查明；本轮修复的是袖口几何与蒙皮。贴身收口要稳定跟随手腕，不能套用巫婆长袍的大范围活动距离。

采用巫婆工作中的连续几何、固定袖口、避免重复加厚及按真实身体制作余量的经验。未来宽松袖身、披风、下摆需要物理时，另外制作低密度模拟代理、身体碰撞与显示映射，固定袖口及肩部，再给衣物建立适用的模拟更新和显隐/距离停用路径；不能只给当前关闭 Tick 的 follower 挂一个 Cloth 资产就称为接入。紧手套继续纯蒙皮。

本次没有增加实时布料解算。未采样帧率或运行模拟，不宣称任何性能提升或全部动画已通过。

## 制作入口

- `Tools/ModularOutfit/export_sleeve_fit_inputs.py`：读取原衣袖与用户要求的布料接入状态。
- `Tools/ModularOutfit/author_fitted_sleeves.py`：保留既有衣物内外层，重建袖口并生成原生绑定派生。
- `Tools/ModularOutfit/save_fitted_sleeves_blends.py`：保存 20 份可编辑 Blend。
- `Tools/ModularOutfit/import_fitted_sleeves.py`：保存 UE 骨骼网格、三级 LOD 后更新两件毛衣配方及 profile 衣袖路径。
- 作者源：`SourceAssets/ModularOutfit20260925/FittedSleevesV1/`；UE 路径：`/Game/Characters/ModularOutfit20260924/FittedSleevesV1/`。

旧袖口源记录在 `M4_shirt_before.json`，旧装备引用保存到 `previous-shirt-paths.json`。导入成功后每个资源有 `Saved/<Profile>.json`，整批接入写入 `published.json`。未启动游戏、截图或动作测试，交由用户测试袖口实际表现。

本轮已完成 20 份可编辑 Blend、20 个 UE 衣袖资源及三级 LOD 保存，并接入两件毛衣的第一人称配方。最终构建记录为 `Saved/FittedSleevesV1/import-02.log`，结束标记 `FITTED_SLEEVES_PUBLISHED 20`，commandlet 退出码 0。初次导入的缺面产物已由修正版本重新构建覆盖。日志仍提示原肩部重合封口在 LOD 简化时存在少量多面共边；保留了这些旧上臂结构，不能把资源构建成功等同于所有距离和动作的视觉验收。
