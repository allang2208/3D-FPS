# 可挖掘旷野与材质调校

本项目案例入口：`scripts/voxel_lab/wilderness_world.gd`、`wilderness_editor.gd`、`terrain_material_bridge.gd`、`scripts/wilderness_materials.gd`。仅在涉及 Terrain3D 挖掘混合或旷野材质时读取；不是要求所有场景体素化。

## Terrain3D 与平滑挖掘面

- 保留未编辑区域的 Terrain3D；编辑附近按需创建 Surface Nets 网格与碰撞。原始地形和稀疏编辑分开保存，不预生成整张地图的体素。
- Terrain3D 的 `get_height` 在 hole 像素会返回 NaN；密度源必须读 region 的原始 TYPE_HEIGHT 图并插值。否则挖洞后再采样会污染密度、坐标和碰撞。
- 区块共享世界坐标密度与法线。洞口边界要对齐实际 Terrain3D hole 删除的三角形范围，负边界和对角角点都测射线，不能只看中心截图。
- 完成替代网格后再更新原 control hole 与地形碰撞。退出恢复源 control 像素；退出保存放在仍持有世界数据的节点退树阶段，避免父编辑器退出时子节点已释放。
- 回填后的裸土痕迹独立于几何 edits 保存：几何恢复原高度不等于草皮自动长回。撤销同时恢复痕迹和材料；读档验证完成后才变更世界。
- 挖掘后同步更新草遮罩、植被支撑显隐和树干碰撞。不要把这种支撑检查描述为承重或倒树物理。
- 正式旷野采集结果进入 RPG 背包，不再同时增加体素实验场的填充库存。先确认背包可接收，再修改地形；地形与背包分别落盘但属于同一事务，任一保存失败都撤销地形并恢复旧背包。
- 同一旷野可挂载正式 BuildingSystem，但通过显式 Terrain3D 源、地图格边界和独立旁车后缀配置，不复制建造实现。坡地首层按构件底面多点采样；挖掘前拒绝破坏仍承托建筑的单元。建筑模式与地形/采集模式必须互斥，避免同一次鼠标输入同时放置和挖掘。

## 材质与渲染诊断

- 同机位对比原配置、调校旧材质、生成材质，再选组合。不要把 AI 颜色图当作完整 PBR；由颜色推导的法线、粗糙度和高度标明艺术近似。
- GPT Image、5080/ComfyUI 等生成端统一把原始正方形颜色图交给 `tools/build_wilderness_pbr_candidates.gd`；命令参数、命名规范和提示词合同见 `assets/textures/wilderness_generated/README.md`。生成端不得直接覆盖默认材质，必须经 `tests/review_wilderness_materials.gd` 固定近景/远景/混合边缘筛选后，再在 `scripts/wilderness_materials.gd` 注册。
- Terrain3D 的贴图数组要求尺寸一致；兼容数组而放大的 4K 图不增加真实细节。保留源图、生成提示词、处理脚本和 mipmaps；颜色 alpha 为高度，法线 alpha 为粗糙度。
- `Terrain3DTextureAsset.roughness` 是贴图修正量；还要考虑地形颜色图 alpha 的湿度修正。草、土、碎石、岩石分别校准尺度与凹凸，不能把一组参数套给所有材质。
- Terrain3D 色图 RGB 会乘到底色，不是普通覆盖色。草地避免使用接近白色的色图值；本溪谷以低明度暖草绿作草地宏观变化，湿岸只向较冷的深绿偏移。调色必须同时检查 `Terrain3DTextureAsset.albedo_color`、Terrain3D 色图 RGB 与 `macro_variation1/2` 三层乘数，综合色亮度回归应保持低于 0.62，且明确草绿方案的绿色通道至少为蓝色通道的 2 倍，避免重新偏成蓝灰。修改高度、control 或色图公式后必须提升 `scenic_valley.gd::CACHE_REVISION`，否则旧缓存会掩盖调整。
- 平滑挖掘面用三向投影；颜色和法线使用相同尺度、偏移及混合权重，减少重复时也要保持配对。
- 复用 Terrain3D 生成 shader 时保留完整控制图、色图、去重复和双尺度逻辑。用实际渲染相机位置计算距离；旧 `_camera_pos` 在独立 MeshInstance 上不可靠，曾产生大块矩形纹理差异。升级插件后重新检查桥接锚点并实机验证。
- 河流条纹先隔离水面和河床：本例隐藏水面后条纹仍在，最终替换的是 ground092c 粗沙纹河床，水波也单独调校。不要仅凭截图把所有条纹归因于水波。
- 当前溪谷河床以 `gravel041` 偏白灰鹅卵石为主：河床色图使用独立的中性浅色乘数，Terrain3D shader 还会按 texture ID 1 的权重移除草地宏观绿染；水下只混入少量坡积碎石，水线外直接渐变到草地。`loam` 深棕壤土只供挖掘断面使用，不再铺成连续河床。程序化区块通过顶点颜色 alpha 标记河流基底，由 `chunk_presenter.gd` 使用同一鹅卵石 PBR，避免离开中心场景后材质突变。
- 溪谷水体使用 `assets/shaders/valley_water.gdshader`：一份屏幕颜色采样做轻折射，深度图控制浅水透明度/深水吸收，双尺度解析噪声驱动法线，顶点 alpha 与交界深度生成岸边及接触泡沫。不在十倍旷野使用逐像素 SSR ray march；远处程序化区块复用相同 shader 或降级材质参数，不能退回完全静止的半透明色块。
- 草叶形体与贴图分辨率分开判断。本例近景从 3×5 段改为 5×3 段，总计仍 30 个三角形；保留中远档较小网格和根部落地检查。实际看覆盖度，避免单纯缩窄叶片后变得光秃。
- 草地扩展入口分三层：`scenes/scenic_foliage.gd::grass_mesh()` 只负责单簇轮廓与三角形预算；`assets/shaders/valley_grass_process.gdshader` 负责草甸斑块、河岸湿润度、坡度存活率及实例参数；`assets/shaders/valley_grass.gdshader` 负责枯绿到湿绿的调色和风摆。新增草种优先扩展实例参数或合并网格，不新增逐株节点；新增生态规则需保持世界坐标确定性，并继续以 Terrain3D control map 和 `solid_exclusion` 作为河床、岩石与建筑的硬排除层。
- 当前近景草采用 7×7 个 8m 跟随单元，0.28m 基础间距，外两圈分别使用 2 叶/1 叶低面网格；宏观草甸遮罩只在同一 GPU 粒子批次内剔除和缩放，不额外增加材质批次。若扩大可见距离，先补中景草颜色/法线烘焙或低密度 impostor 环，不能直接放大近景粒子网格。

## 验证与交付

- 固定相机时关闭玩家物理、鼠标输入及 CameraFx；相机移动后等待地形更新再截帧。测试存档使用独立路径，不能依赖无头退出码判断材质效果。
- 本例测试：`test_voxel_lab`、`test_smooth_voxel`、`test_wilderness_world`、`test_wilderness_scene`、`test_scenic_valley`；覆盖材料守恒、撤销/保存/恢复、共享法线、坡地和边界射线、植被遮罩、武器切换、Terrain3D 建筑锚点及采集事务。只改草簇或草 shader 时先运行 `tests/test_valley_grass_contract.gd`，它不加载完整溪谷资产，可快速检查三档面数、根部坐标、生态分区参数和硬排除接口。
- 溪谷通过覆写 `scenic_valley.gd::_build_mouse_king()` 禁止生成小鼠大王；公共演示地形仍保留 `demo_terrain.gd::_build_mouse_king()`。后续新增旷野入口时若同样不需要该 NPC，应显式覆写为空，不要删除公共实现。
- 正式旷野不得自行拼装 Player、Camera 或 Gun；统一调用 `scripts/gameplay_player_factory.gd::create(spawn)`，移动参数与输入由 `scripts/player.gd` 唯一负责。`WildernessEditor` 默认必须处于普通战斗模式，仅在玩家明确按 F7 后接管鼠标；关闭工具时恢复原 Gun 的 `process_mode`、可见性和 `terrain_editing=false`。
- 帧耗样本记录设备、分辨率、机位、帧数和中位数/P95；单次场景采样不代表连续挖掘性能，也不代表提升百分比。当前已编辑区域常驻，远处卸载和后台重建尚未实现。
- 共享仓库发布先检查 WORKFLOW.md：分离同文件中其他会话后来接入的工具、昼夜等功能，在独立发布工作区从远端基线组合本任务必要改动并重新验证；不回退共享工作区，不整批推送无关提交。
