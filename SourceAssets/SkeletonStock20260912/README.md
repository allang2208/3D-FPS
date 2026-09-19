# 三角镂空骨架枪托 skeleton

> 视觉验收已于 2026-09-12 被用户否定：模型过于粗糙。下文仅记录这一轮制作和功能测试，不是已接受资产。当前重制目录为 `../ReferenceStock5080_20260912/`，按用户新参考重做三视图并使用 RTX 5080。四组旧版运行测试共 1883 项通过，但不能替代新模型的视觉验收。

2026-09-12，UE 5.8.2，宿主 `D:/FPS3D/FPSGAME`。用户明确选择三角镂空 `skeleton`，保留独立的 `precision` 身份。游戏入口：装备 M4A1 或 AKM → 装备改造 → 枪托 → 三角镂空枪托 → 应用并保存。

## 制作结果

- `three_views.png`：按旧参考制作的统一侧/顶/后视图；`model_input.png`：同一造型的单张 3/4 建模输入。
- `skeleton_raw.glb`：混元 PBR 原始输出，500,000 三角面、311,141 拆分顶点，焊接后 249,998 顶点。
- `ReducedGenerated/`：对真实生成几何焊接减面的中间参考。规则边缘仍波动、材质区不清晰，因此最终采用按三视图及生成轮廓进行的硬表面重建，并非把最终网格称作原模直接减面。
- `SkeletonStock_SeparateParts.blend`：可编辑分件源；`SkeletonStock_Editable.blend`：最终 UV/烘焙网格和渲染场景；`SM_SkeletonStock.fbx`、`SkeletonStock.glb`：引擎与通用导出。
- 作者源 15,496 三角面；UE 导入 15,494 三角面（导入整理差异）；1 材质、1 UV，四张 2048² BaseColor / Metallic / Roughness / Normal。真实开口、连续三角框架、腮托、带凹槽肩垫、接环与背带孔。生成纹理已由本次制作的程序材质烘焙替代。
- 作者源几何检查：开放边 0、非流形边 0、零面积面 0。UE 读回尺寸约 23.03 × 4.80 × 12.56 cm。检查作用于配件网格，不宣称全枪全臂零相交。

## 来源与许可边界

`legacy_reference.png` 复制自 `E:/3d/stock-refine/candidate-hk416-skeleton.png`，为本项目旧候选渲染；未向外发布旧整枪资源。三视图及建模输入由本次内置图像生成制作。提示语义：统一同一支三角镂空游戏枪托的正交侧、顶、后视图；深灰金属三角架、低位腮托、黑色橡胶肩垫及圆形前接环，保留旧候选身份；再生成同款独立 3/4 视角，白底且无整枪。

5080 主机 `192.168.3.142` 的 ComfyUI 和 SSH 均超时；本轮走已配置的混元图生 3D 管线，单图输入启用 PBR，并非多视图融合。任务 `1490295790647640064`；请求与结果见 `generation_manifest.json`，本地原始任务在 `Saved/Hunyuan3D/Candidates/skeleton_stock_20260912`。最终规则硬表面、UV 与烘焙为本次作者脚本制作。

现有 M4、AKM 和 Manny 资产沿用各自既有本地许可与导入来源；枪托工作不增加其源包公开再分发授权。含原枪的 Blend、FBX、uasset 保留本地，不作为可公开独立售卖资源。

## 原算法与 UE 衔接

核对 `E:/3d/attachment-upgrade-20260909/before-files/stock_variants.gd`：旧版缓存原 mesh，以各枪 `stock_cut.json` 三角索引白名单替换原厂部分并保留材质槽，拆卸恢复；`E:/3d/stock-refit-staging/build_unified_stocks.before.gd` 使用统一枪托尺寸、每枪单独转接。

UE 采用同一合同，以材质 section 可逆隐藏代替运行时重建三角数组。M4 使用现成 Classic Stock section；AKM 在当前附件作者源中添加 `M_AKM_FactoryStock`，包含连通部件 1/45/46/47/48 和机匣尾舌白名单。白名单与未改变的顶点/权重 SHA-256 记录于 `fit_preparation.json`。原弹匣已在作者源分为单独对象，导出包含该对象，导入读回保留 Magazine、PBR、两种 Manny 材质并增加 FactoryStock。

共用模型以连接面为原点，Blender +X 指向肩垫；M4 根局部安装位置 `(0, .0385, .0725)` m，AKM `(.0008, .091, .035)` m；Blender 旋转 +90° Z。FBX 的 Y 反向映射到 UE，`WPN_root` 的 100 倍继承缩放由相对 `.01` 抵消一次。每枪独立测量，不按原厂枪托 AABB 缩放共用模型。

`SkeletonStockVisual.cpp` 是装配和拆卸唯一入口；角色配方、枪匠、独立展览、库存图标、地面掉落共用。AKM 当前候选位于 `/Game/Weapons/AKMIntegration/SovietFab/StockV2/SK_AKM_MannyNative`；保留旧附件网格作为回退。早期 Stock 候选被其他并行进程加载，故最终使用独立 V2 路径完成验证，没有关闭其他任务的游戏进程。

属性以实际旧代码为准：ADS 时长 ×0.8、后坐 ×1.1、镜头晃动 ×1.1、腰射散布不变。旧历史记录中的毫秒描述不作为当前数值。

## 复现与证据

`inspect_sources.py → prepare_fit.py → inspect_generated.py → optimize_model.py（中间参考）→ build_model.py → render_fit.py → import_assets.py → run_validation.ps1`。原生编译后必须启动新进程，不能用老进程判定更新。

`m4_interface.png`、`akm_interface.png` 与完整装配渲染为实际模型渲染。运行结果和动作预览见 `acceptance.json` 与 `stock-v2/`；自动脚本只在 `StockAudit` 隔离存档下运行。`run_validation.ps1 -RunId <唯一标签>` 依次启动 M4/AKM 写入及跨进程重载四组测试。按实际完成结果记录，旧 `stock-v1` 是测试槽位配置修正前的失败记录。

导入 `import_final.log` 有 `SKELETON_STOCK_IMPORT_PASS` 且无 Python 错误，但 commandlet 退出码为 **1**：项目既有的 GameFeatureData AssetManager 两条错误仍在。本轮不修改该并行项目配置；导入回读与游戏运行验证分开记录。编译结果在 `build_final.log`。本轮未做完整打包；静音 GIF 仅提供可见动作证据，未改动画或声音。
