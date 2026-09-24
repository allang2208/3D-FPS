# 中央白金方形祭坛：UE 资产接入

2026-09-22。用户纠正范围后仅处理中央小祭坛；大型主神空间、台阶和柱廊没有迁移或修改。

## 来源与制作边界

- 正式视觉来源：`E:/无尽轮回/长期备份/2026-7-13-1/game-dev/assets/terrain/defense_base.png`。原项目的 `data/game-config.json` 中 `npcs.altar.sprite.idleKey` 实际引用 `defense_base`。
- 原项目的旧 `assets/npc/altar.png` 是另一张长方形雕花祭坛图片，本次未用它替换正式视觉来源。
- 没有找到与正式图片对应的成品三维模型。本交付是依据原图制作的三维重建，不是原始三维网格的无损搬运。不可见背面采用对应正面的对称结构。
- 复用同一原项目内的 `material_unify_r14/stone-albedo-raw.png` 白石纹理。该纹理的来源说明是参照祭坛制作的原项目材质；本次未新增 AI 生图，也未公开发布原素材。
- 保留白石阶座、金色卷草、蓝宝石、四角短柱及内凹台面的造型身份。短柱采用封闭旋成线脚、20 道真实圆凹槽及轻微收分和卷杀。大理石、抛光线脚、金饰、宝石分别使用独立材质。

## 使用入口

- UE 静态网格：`/Game/Props/SquareAltar20260922/SM_SquareAltar`。
- 建造面板：**大理石 → 其他构造 → 白金方形祭坛**。
- 稳定构件 ID：`square_altar`。
- 活动调色板：`/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette`；仅追加本条目，保留其他条目及其字段。
- 导入时用于计算占格的网格尺寸约 `220 × 200 × 141.015 cm`，占格 `11 × 10 × 8`。纵向余量通过 `pivot_offset_cm.z = -9.49264` 抵消，使模型底部贴地；预览和正式放置沿用同一构件变换。
- 不覆盖材质槽 0，保留完整四材质分区。采用 Nanite 与三角面碰撞，以保留台面凹处的形状。
- 首次接入为独立外观构件；没有迁移旧项目祭品合成、出征或 NPC 对话逻辑。随后用户要求将它作为出征面板交互入口，主场景摆放由下方脚本完成。

## 可编辑源与重制

- `Authored/SquareAltar.blend`：分件、材质、打包纹理的可编辑源。
- `Authored/SM_SquareAltar.fbx`：UE 导出网格，共 139062 个三角面。
- `reference_defense_base.png`：原祭坛视觉参考。
- `author_square_altar.py`：独立制作脚本，不会修改 gamedev 原文件。
- `import_materials.py`、`import_mesh.py`、`register_prefab.py`：分阶段接入脚本。通过项目桥 `Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript ...` 调用，使用同一批次互斥。
- 首次导入脚本在目标网格或构件 ID 已存在时停止，以免覆盖已有修订。重制后需要明确选择重导入范围，不应直接重复整批执行。
- `authoring_manifest.json`、`materials_receipt.json`、`mesh_receipt.json`、`integration_receipt.json`：制作和保存回执。

制作、材质必要编译、导入和保存已经完成。未运行 PIE、游戏测试、截图、渲染或视觉验收，由用户自行测试；操作保存回执不等于实机验证。

## 主场景祭坛与出征面板入口

**2026-09-22 该回合最后回执：祭坛已在编辑器中生成，但主场景文件被占用，保存失败；当次链接也受地牢类缺失实现阻塞。详见 `hub-placement-pending.md`。2026-09-25 仅发布源码，不重新读取关卡或验证运行状态；后续传送门／宝箱的成功原生构建记录不替代此关卡的保存回执。**

- 关卡：`/Game/GameMaps/DayNight_Lighting`；编辑器对象标签 `Expedition_SquareAltar`，目录 `Main Hub/Expedition`。
- 使用原比例方形祭坛，面向出生点；相对 PlayerStart 前方 650 cm、左侧 400 cm，以原关卡 Floor 顶面贴地。
- 放置脚本 `place_hub_altar.py` 只修改主场景，不启动 PIE；若编辑器当前是其他干净关卡，则临时打开主场景、保存祭坛后恢复原关卡。存在未保存关卡改动则停止。同一标记存在时复用，不重复生成。最终保存结果记录在 `hub_altar_placement.json`。
- `ColdSteel.ExpeditionAltar` Actor 标签接入现有准星交互。2.5 m 内瞄准祭坛按 E 打开出征面板，Esc 关闭；O 键入口移除。
- 同一射线判定用于显示提示与执行打开；射线先命中其他遮挡物时不能隔墙使用祭坛。不消耗、销毁或隐藏祭坛。
- 这是当前 UE 面板入口；没有移植原项目的解锁、队伍、钥匙、奖励或出征业务。
