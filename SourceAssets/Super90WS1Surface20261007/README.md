# Super90：共享 WS1 金属母材质替换

用户于 2026-10-07 反馈原贴图／表面仍有问题，要求按 SKILL 改用项目枪械通用金属母材质。

## 当前制作配方

- 直接继承 `/Game/Weapons/WeaponSurface/Presets/MI_WS_*`，共同母材质为 `M_WeaponSurface`；不修改公共母材质及预设。
- 机匣使用 CleanAnodized，枪管／管仓和机瞄使用 CleanSatinSteel，活动钢件独立设置较低粗糙度。原金色小件保持独立色调。
- 护木／后握等聚合物、托垫橡胶和备弹夹各自使用非金属预设。材质区域按源 UV 岛及原金属区域划分。后续 `Super90SurfaceAlignment20261007` 已纠正旧 180° 方案：原始 FBX 配源 PNG 只需转换 V 原点，按正确坐标重新划分区域；不改顶点、骨架或权重。
- 机匣原图只提取白色品牌字样和暖色标记，金属底色替换为 Clean 深色配方。其他槽不混入原底色，所有新实例禁用原粗糙度图；低频斑驳、划痕、握持抛光关闭。
- 保留源结构法线；枪体 PNG 是 DirectX，UE 不再翻转其绿通道，Blender 编辑源单独转换到 OpenGL。UV0 使用原始 PNG 的正确图集坐标。SurfaceMask 为 UV0 的独立 RGBA 数据图，B 使用源 AO；只应用一层 AO 和母材质内置湿润。微纹按厘米采样，不使用枪体图集去覆盖配件。
- Super90 专属镜座、前握把安装座及已有明确金属分区同步使用独立 MountSteel 实例。玻璃、分划及握把塑料外皮沿用其原材质。
- 保留 `FactorySights` 槽名，继续支持装镜隐藏机瞄；更新装备外观的手臂隐藏槽索引。

## 生产入口

1. `prepare_textures.py` 生成新材质输入；Blender 执行 `author_surface.py` 生成材质区域和 FBX。
2. 现有 UE 桥执行 `apply_surface.py`。必须先退出 PIE；脚本导入并保存实例、网格与装备槽配置，不运行游戏。
3. 保存完成后执行 `publish_source.py`，将可编辑文件和 FBX 同步到 Super90 当前制作源。

实际资产保存记录见 `import_receipt.json`，替换前文件保留在 `Before/`。这是一轮用户要求的材质替换尝试，未运行截图、渲染或游戏验收，效果由用户测试。
