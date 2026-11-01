# 骨架狙击枪托

独立 `stock / sniper_skeleton_stock` 改造，适用 `ue_svd`、`ue_svch`、`ue_m24`。不并入 M24 先进枪机系统，不替换枪管、握把接触面或动作。

数值沿用现有枪匠乘数：后坐力 ×0.85、稳定性 ×1.20、开镜耗时 +5%。存档继续使用原有 stock 槽位机制。

## 来源与适配

- 用户提供 `C:/Users/allan/Downloads/Meshy_AI_Adjustable_Tactical_R_1031040412_texture.glb`。完整原件保存在 `Original/`，SHA256 与 glTF 信息记录于 `source.json`。
- Meshy 外形保留 198545 个源三角面及原 UV、法线、PBR。三个作者场景分别按原装后托的安装端和肩垫位置等比适配，接口补为真实封闭几何。
- M24 保留手握区域，以 `Inputs/m24_factory_stock_faces.json` 的 1208 个原生面中心拆出 `M24_FactoryStock`。只改材质分区，不重导手臂、骨骼、蒙皮、Morph 或动作。`M24_FactoryFront` 仍由原先进枪机系统控制。
- SVD 使用已有 `SVD_FactoryStock` 分区；SVCH 使用 `KVInhibitor_stock` 分区。三者仅在安装此改造时隐藏原后托，切回原装恢复。
- M24 使用现有 `M24Attachments::Mount`；SVD/SVCH 导出到各自 `WPN_root` 的局部坐标，以 0.01 组件缩放补偿 FBX 根骨骼的 100 倍继承。每枪矩阵及连接锚点记录于 `authoring.json`。
- 新接口与 Meshy 材质分开。专用母材质继承现有 `M_WeaponSurface`，保留天气湿润接入；使用原始金属度、粗糙度、基色及法线。OpenGL 法线只在 UE 导入时翻转绿色通道一次。
- SVD 导入报告过局部近零切线：修整连接端封口、重做连接端三角面 UV，并按 0.01 mm 阈值合并重合顶点（主体仅消除 5 个微小面）。最终把各 LOD 已有几何和有效法线、UV 固化为独立源网格，仅对无效切线补齐正交方向；装配坐标不变。`svd_baked_basis_receipt.json` 是这一步的保存回执。
- LOD0 保留近景细节，LOD1/2 三角面比例为 0.5/0.2；不生成配件碰撞。

## 改造图标

实际读取路径：`Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms`。

依当前 UI 解析顺序检查 M24 的 25 个现有选项及 8 个分类入口。原装栓机、碳纤维栓机、原装握持区、原装枪身、先进枪机系统五张选项图使用旧细框，本次从实际部件重做。栓机与枪身的分类入口同步更新；枪身分类实际优先加载共享 `category_body`。

本次制作 8 张独立母图，部署 14 个实际/兼容键：

- 通用骨架狙击枪托一张共享图，三把枪复用，不逐枪复制。
- 上述 M24 五张不符合样式的选项图。
- M24 原装后托及 SVCH 原装后托各一张，用实际形状区分。

图标由对应作者场景实际渲染，沿用认可的 `FirearmFramedIcons20260930/muzzle_brake_framed_v2.png` 厚金属框。灰阶、枪前朝左、正交侧视；图标专用去色不改变运行材质。`Icons/production.json` 保存模型来源，`Icons/updated_contact_sheet.png` 包含 64/48 像素视图。`Icons/current_mapping.json` 与 `category_mapping.json` 保存修改前解析清单；原图备份在 `Before/`。

## 制作与落盘入口

1. `prepare_source.py` 归档 GLB 并提取贴图。
2. Blender 后台运行 `read_hosts.py`、`author_fitted.py`、`author_icons.py`。
3. 使用项目 `Tools/Build/Build-Editor.ps1` 构建正式 Editor DLL。
4. `run_assets.ps1 -Stage install_assets` 在既有互斥下导入网格、材质、贴图、UI 纹理并保存。
5. `run_assets.ps1 -Stage finish_install` 拆出 M24 原装后托分区并保存，更新现有枪匠目录中的三个选项。
6. SVD 连接端修整入口为 Blender `repair_svd_interface.py` 和 `run_assets.ps1 -Stage install_svd_finish`，最后执行 `-Stage bake_svd_basis` 固化各 LOD 的有效切线。中间的 `finish_svd_basis` 是排查阶段记录，不作为最终步骤。

正式资产根目录：`/Game/Weapons/SkeletonSniperStock20261031`。

`install_receipt.json` 记录已保存资产与图标映射；`delivery.json` 仅由最终落盘脚本成功后写出。后台制作、构建与图标检查不代表游戏验收；本轮不启动 UE GUI、PIE 或游戏测试，由用户测试装配和实战表现。

2026-10-31 本轮落盘完成：正式 Editor DLL 构建成功，25 项网格/材质/贴图资产保存，M24 后托分区及枪匠目录保存成功。最终构建日志为 `Saved/BuildEditor/build-20261031-131809.log`；首轮导入与目录落盘分别见本目录 `install_assets-20261031-125743-180.log`、`finish_install-*.log`，SVD 最终表面落盘见 `bake_svd_basis-*.log`。

SVD 最终保存的三层 LOD 分别为 198782、99391、39756 三角面，分别补齐 103、93、52 个无效角点切线。最终构建保存日志不再报告此前的近零切线/副法线提示；这仅是资产构建结果，不代表游戏内视觉验收。
