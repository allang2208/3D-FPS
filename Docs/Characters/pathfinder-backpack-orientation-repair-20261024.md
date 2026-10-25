# 开拓者战术背包朝向与衔接修复

> 2026-10-24 后续复查：当前活动 PNG 仍显示贴背面，与 R2 源图散列一致。下文保留制作／保存历史，不作为统一正面图标的视觉通过记录；当前差异见[方向标准与五款盘点](backpack-facing-standard-20261024.md)。

修订：`PathfinderOrientationFitR2_20261024`。两份静态包体、12 套背带与材质已后台保存，男女配置及目录图已本地接入。回执为 `SourceAssets/PathfinderBackpack20261023/OrientationFitR2_20261024/saved_assets.json`、`published.json`。

## 原因与修复

旧 `prepare_source.py` 在 GLB 对象仍使用四元数旋转模式时修改 `rotation_euler.z`，180° 调整没有落实到顶点。展示图因此拍到肩垫／腰封面，穿戴收带算法也处理了错误的一侧。本次改用 `Matrix.Rotation(...) @ matrix_world`，烘入真实顶点与法线：外侧为 −Y，贴背侧为 +Y。显示源与穿戴源分开保存，原 GLB 保留不动。

- 完整展示体及共享 Nanite 穿戴体均保留 193071 个三角面、原 UV 和 PBR 贴图，不减面。旧空载肩腰带向真实贴背面收整，收整函数在连接处保持连续的一阶导数。
- Jason、Kaitlin 各制作裸身、炭灰短袖、野行上衣、锁子甲、法袍、ST6 六套背带，共 12 套。读取当前保存身体、上衣、扎腰款、默认配对及每种身体 22 个普通／靴型裤网格，共 130 份去重的完整或接触带输入。
- 包体后移由实际躯干／衣物表面求解，包络范围延伸到腰臀。腰封两端改用包体真实源顶点的缝接点；肩带、腰封缝接端权重为 spine_03=1、摆动遮罩=1，肩胸固定区维持贴身。
- 女性肩高使用当前骨骼标定；针对本包另修正 8° 局部安装倾角，收近上背间隙，保留下部腰臀避让。该角度只属于本款模型，不推广到其他包。
- 背包栏的实时图标读取 `world_static_mesh`，因此同时更新该显示网格；修复原 `Icons/ue_pathfinder_backpack.png`，保持目录与旧实例使用的路径不变，兼容旧物品快照及运行时固定名称回退。容量、夹层、物品实例和玩家存档不变。

## 制作与接入入口

`Tools/PathfinderBackpack/prepare_source.py` → `read_body_inputs.py`（转 `read_fit_r2.py`）→ `author_r2.py` → `prepare_buffers.py` → `save_assets.py` → `publish.py`。

作者输出、备份与回执均位于 `SourceAssets/PathfinderBackpack20261023/OrientationFitR2_20261024/`；新 UE 资产位于 `/Game/Characters/PathfinderBackpack20261023/OrientationFitR2_20261024/`，继承已有 Cook 根目录。`publish.py` 通过字段事务只写根配置／女性变体中的本款背包表现字段，物品目录字段保持不变。

已有编辑器正在 PIE 时，保留它；本次使用同一桥互斥的后台 commandlet，仅创建未被当前场景引用的新修订资产。`run_stage.ps1 -NewRevisionOnly` 拒绝替换已存在且与作者源不匹配的网格，未关闭、重启或启动交互编辑器，也未运行游戏测试。材质编译属于制作步骤，本次未改原生 C++，无需重建 Editor/Game DLL。

## 检查与使用边界

本次按用户要求检查源模型、当前装备路由、参考姿态接触及离线几何视图。`reference_inspection.json` 记录 12 套背带的顶点／面心包络采样、缝接端位置、蒙皮及摆动遮罩；`Review/` 保存两种身体的裸身、野行上衣及法袍正侧背参考图。它们不等同于运行时全部姿态的无穿模证明。

没有做奔跑、蹲伏、转身、死亡或主客机验收；由用户在游戏中体验。现有 `FPSBodyEquipment::OutfitDefinitions()` 每进程缓存显示源，正在运行的编辑器须由用户重启后查看完整的新图标和穿戴版本；仅重新开始 PIE 不保证刷新旧的实时图标源。

本轮没有 Git 提交／推送。旧 R1 文件与回执保留历史，不再作为当前朝向正确性的依据。
