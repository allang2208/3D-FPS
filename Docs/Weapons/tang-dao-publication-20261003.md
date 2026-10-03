# 唐刀源码发布与本地素材恢复

2026-10-03 按用户授权从 `D:/FPS3D/FPSGAME` 发布到 `https://github.com/allang2208/3D-FPS.git` 的 `main`。本次范围是唐刀制作、模块目录、刀身符文修复、燕翎第三段竖劈、祥云击杀体力恢复、限定卡片及相关制作经验；共享文件只提交对应改动，保留其他任务的工作区修改。

## 发布与许可

公开保留 `SourceAssets/TangDaoMeshy20261002` 中的作者／导入脚本、文字说明、小型 manifest、表面配方和图像提示词；运行数据保留 `Content/ColdSteelData/tang-dao-modules.json` 等唐刀目录变更。`.gitignore` 对本系列采用白名单，原始 GLB、Blend、FBX、参考图、PBR、图标、UE 资产、密集顶点／UV 坐标、机器回执和日志不进入 Git。

原始唐刀由用户提供的 `Meshy_AI_Dragonforged_Saber_1002040045_texture.glb` 制作，未取得本次公开再分发的许可证明。龙凤护手和新配重采用本地 Blender 实体建模与内置 imagegen 纹饰高度图，不称为 Meshy 图生三维。用户参考图和项目既有 Manny 手臂、动作、声音及材质供体分别沿用自己的来源边界。本提交是源码和恢复说明，不是可独立运行的完整素材包，也不表示用户已经接受最终视觉效果。

## 当前保留版本

| 部分 | 运行身份／版本 | 当前制作入口 |
| --- | --- | --- |
| 基础唐刀 | `ue_tang_dao`，局部长轴持握调转 | `author_tang_dao.py`、`holding_orientation.json`、`SurfaceV2/` |
| 破锋燕翎刀身 | `blade_1/yanling_edge` | `YanlingBlade20261002/author_blade.py` |
| 腾云游龙刀身 | `blade_1/tengyun_dragon`，`SolidV4` | `TengyunBlade20261002/PlanarRepair20261002/author_planar_blade.py` |
| 璇云龙璧护手 | `guard/xuan_cloud_dragon` | `XuanCloudGuard20261002/author_guard.py` |
| 凤仪华羽护手 | `guard/phoenix_feather` | `PhoenixFeatherGuard20261002/author_guard.py` |
| 破锋燕翎配重 | `pommel/yanling_breaker`，八面锥 `ConeV3` | `YanlingPommel20261002/ConeV3/author_pommel.py` |
| 虎啸镇岳配重 | `pommel/tiger_mountain`，`ConnectorV4` | `TigerPommel20261002/author_pommel.py` |
| 祥云符文 | `blade_2/auspicious_cloud_rune` | `CloudRune20261002/import_assets.py` |
| 背包图标 | `ue_tang_dao`／`ue_tang_dao_surface_v2` | `InventoryIconRules20261002/` |

游龙当前网格为 `/Game/Weapons/TangDao20261002/TengyunBlade20261002/Meshes/SM_TangDao_Blade_tengyun_dragon_SolidV4`，沿用 `JointRepair20261002/Materials/M_TangDaoBladeRuneSurface_CloudTengyunJoint`。名称含旧修订的材质仍然有效，不能整目录删除。新版刀身厚度 7 mm，刀根独立收口，龙纹由既有 PBR 与法线保留。

虎首当前网格为 `/Game/Weapons/TangDao20261002/TigerPommel20261002/Meshes/SM_TangDao_Pommel_tiger_mountain_ConnectorV4`。上部球形、局部折面下颌、封闭口腔、实际柄尾安装端与分层云纹接座在同一可编辑源中；六组材质及三档 LOD 保留。卡片制作输入为 `Icons/ue_tang_dao_pommel_tiger_mountain_source.png` 和 `Icons/frame_style_reference.png`，后者从旧备份目录迁移，提示词同时保留原路径记录。两款配重均沿用真实接口与握柄 `pommel_offset_cm`。

燕翎刀身第三段复用冲刺竖劈动作、第三段伤害 ×1.40、前方矩形，攻击耐力 ×1.10、格挡减伤倍率 ×0.90；竖劈前进距离与突刺共用 100 cm。祥云符文攻速 ×1.10、攻击体力消耗 ×0.85、韧性伤害 ×0.90，任意归属击杀按当前最大体力恢复 15%。未批准的游龙与新配重效果保持现有目录值，不在整理期间添加玩法。

## 本地依赖与恢复顺序

1. 在本机保留／恢复 `SourceAssets/TangDaoMeshy20261002/Original`、当前 Blend、纹理、参考、高度图、图标和 `Content/Weapons/TangDao20261002` 已保存资产。原始 TangDao、模块和 SurfaceV2 的 Blend 是后续精确接口供体；不能按版本日期判为废案。
2. 缺失原始坐标输入时，先从合法持有的 Meshy GLB 运行 `read_source.py`，再制作基础模块和 SurfaceV2。有效 `interfaces.json`、`source_coordinates.json` 等密集输入仍在本机，未公开。
3. 按当前 manifest 制作燕翎刀身、游龙 PlanarRepair、两款护手、燕翎 ConeV3 和虎首 ConnectorV4。制作配方读取本机原始接口和纹饰；重新生成高度图属于新制作，不能宣称与当前源逐字节相同。
4. 基础材质、原生刀身符文及祥云材质依次恢复，游龙保留上述 JointRepair 材质包。按新增件脚本后台导入保存，再合并当前模块目录。不要重跑历史修订准备脚本去覆盖最终 manifest。
5. 父级安装器可能重建基础目录，后续专属改造必须重新合并；界面 PNG 与 UE Texture 分别部署和保存。后台命令使用现有 UE 桥批次互斥；没有必要时不启动交互编辑器。

作者脚本制作的 `.blend`、导出的 FBX／GLB、脚本执行成功、实际保存的 `.uasset` 与实机效果是不同状态。之前的最终导入回执保留本机，当前虎首记录为 32 个已保存资产；本次整理没有再次构建、导入或开展游戏测试／视觉验收。

## 退役清单与 SKILL

废案归档在工程 `trash/tang-dao-retired-20261003`。`manifest.json` 包含旧路径、新路径、字节数、SHA-256、原因及替代入口；历史文档和回执中的 `Before`、旧日志、ReferenceV2 路径按清单查找。迁移记录不公开模型文件。

已归档 462 个文件，共 1,386,152,434 字节（约 1.29 GiB），其中 16 个退役 UE 资产包在用户关闭编辑器并要求剔除后移动。所有移动文件的 SHA-256 与原文件一致；清单 SHA-256 为 `4347662FD3EE8982D2119D78C6BE3F65743B74CC4601CB86E1B7ADA54D9BBDED`。当前模型、有效材质和本机制作输入保留；框样式输入属于有效依赖，迁移至当前 Icons 目录，没有判废。

纹饰、主体形状、下颌和接座技法沉淀到 [纹饰浮雕与立体轮廓](../../skills/asset-model-workflow/references/ornamental-relief-and-solid-shapes.md)，刀身符文、第三段动作替换和限定身份沉淀到 [模块化近战武器](../../skills/ue5-weapon-workflow/references/modular-melee.md)。相同新增内容已同步个人 SKILL 维护源；没有覆盖其他技能修改，也没有更新个人记忆。

发布前检查范围为仓库／origin／分支、待推送历史、明确暂存范围、完整暂存差异、空白、源码语法、JSON、文件大小、敏感信息、许可和新增文档链接。没有追加游戏回归或启动应用；实机效果由用户测试。
