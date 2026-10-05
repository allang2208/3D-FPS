# M-25 游戏网格与 LOD — 2026-10-05

用户授权对涡电匣进行减面和性能优化，并已保存、关闭 UE。所有制作通过后台 Python commandlet 完成，不启动编辑器界面、PIE、截图、渲染或性能采样。

## 实际交付

2026-10-05 19:58 已完成资产导入、LOD 构建和原怪物蓝图保存。最终导出及导入 commandlet 均正常退出；实际保存回执为 `asset_receipt.json`。

| 级别 | 三角形 | 渲染顶点 | 屏幕尺寸阈值 |
| --- | ---: | ---: | ---: |
| LOD0 | 349,998 | 298,231 | 1.00 |
| LOD1 | 119,998 | 126,034 | 0.55 |
| LOD2 | 39,996 | 55,550 | 0.22 |
| LOD3 | 9,984 | 18,553 | 0.08 |

近景三角形相对原 6,524,740 面减少约 94.6%。全部 LOD 各一个材质区段，共用原 148 骨 UE 骨架。新 FBX 为 17,421,792 字节，四级 LOD 的游戏网格资产为 102,202,048 字节；原高模编辑源不包含在新网格的导入源中。光追最低使用 LOD1。

正式资源：`/Game/Monsters/VortexCofferM25/OptimizedV01/SK_M25_VortexCoffer_Game_V01`，LOD 设置为同目录 `DA_M25_GameLODs_V01`。原 `BP_VortexCofferM25` 的 `VisualMesh` 和 Mesh 组件均已接入，F6 入口保持原怪物。

同次保存的移动参数：55 cm/s、转向 75°/s、加速度 240、制动减速度 360；动画源速度保持 16 cm/s，满速蠕动为 3.4375 倍、周期约 0.815 s。详细回执同步在 `../MovementV02/asset_receipt.json`。

没有进行视觉、碰撞、动作或 FPS 验收，不能把几何降幅当成帧率增幅。

## 制作合同

- 原制作高模：6,524,740 个三角形，原件及 `RigV01` 保留。此前直接以高模作为唯一游戏网格，漏做了游戏网格预算和 LOD。
- 新游戏网格预算：LOD0 350,000、LOD1 120,000、LOD2 40,000、LOD3 10,000 个三角形；实际生成数量以 `asset_receipt.json` 为准。
- 保留原骨架和骨名、蒙皮驱动、材质 UV、贴图、专用物理资产与现有动作。减面重算新顶点权重，每顶点最多四骨骼；不移除骨骼。
- 优先保留嘴部、口缘、背部电极及触须末端，开启骨骼分区惩罚、重合点权重合并和体积保留。近景/中景锁定网格开口边界；LOD2/3 允许这些边界继续简化，骨骼和 UV 属性约束继续保留。
- 现有法线贴图继续使用，本轮没有新做高低模法线烘焙；减面后的近景外观和变形由用户体验。
- 光追最低使用 LOD1，不改变全局硬件光追或 Lumen 设置。
- 现有撕咬/魔法、嘴部弱点、AI、背部电流和 F6 怪物目录沿用。补齐此前用户要求的沉匣参考移速/转速，并保留蠕动源速度 16 cm/s 作为动画调速分母。

## 重建与文件

1. `reduce_master.py`：复制原网格，只对副本应用减面参数并保存。
2. `export_reduced.py`：通过离屏后台 commandlet 导出减面后的蒙皮 FBX。UE 5.8 的骨骼 FBX 导出器内部需要 RHI，即使材质烘焙关闭仍不能使用 `-nullrhi`；使用 `-AllowCommandletRendering -RenderOffscreen`，不产生验收画面。
3. `import_and_bind.py`：复用原骨架导入独立游戏网格，生成距离 LOD、设置光追 LOD，保存原怪物蓝图的新引用及移动设置。
4. `author_common.py`：共用减面配置、FBX 导出和保存接口。UE 5.8 必须通过反射 `SetLODSettings` 应用到 LODInfo；只写 `lod_settings` 属性指针不足以应用参数。无界面导出关闭 FBX 材质自动烘焙，继续引用既有 PBR 材质。
5. `reduction_receipt.json` / `export_receipt.json` / `asset_receipt.json`：生产阶段和真实保存结果；中断时不会把脚本存在当作已完成接入。
6. `BackupBeforeOptimization/BP_VortexCofferM25.uasset`：第一次正式替换前的原蓝图备份。

新资源位于 `/Game/Monsters/VortexCofferM25/OptimizedV01`。正式怪物仍为 `/Game/Monsters/VortexCofferM25/BP_VortexCofferM25`。

首次生成新 LOD 后还须重新应用各级配置，因为新建 LODInfo 会先继承前一级参数。脚本已包含这一步；最终四级实际面数见上表。初次 NullRHI 合并导出在网格保存后因 UE 导出器的 `MeshObject` 断言中断，随后独立离屏导出成功；最终资产保存结果不依赖该失败导出。

此轮为资产制作，不需要原生 C++ 构建。未执行游戏、视觉或帧率测试，不将减面比例等同于 FPS 提升。

2026-10-05 整理：上文旧备份已移入仓库根 trash/m25-retired-20261005 的同阶段相对目录；逐文件映射见 Docs/AssetArchives/m25-retired-20261005.json。生产源与当前资源保留。
