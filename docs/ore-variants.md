# 矿脉形态变体

铁、铜、银、金矿脉共用 8 种独立网格：块状 rounded、薄片 slab、斜立 leaning、尖脊 ridge、楔形 wedge、双峰 saddle、高柱 tall、长条 long。每种保留现有矿石材质，共 32 个材质/形态组合。普通石块不改。

源几何为项目已有 Poly Haven CC0 boulder_01 和 rock_09 扫描。离线脚本 tools/basic-tools/bake_ore_variants.gd 归一化源网格，通过局部峰谷、剪切、收窄等方式修改轮廓，保留 UV 并重建法线与切线。结果在 assets/models/ore_variants/*/model.scn，可直接在 Godot 中编辑实例；脚本是可重复生成源。每形态配套 fragments.res，包含与完整模型一致的 8 块预烘焙碎片，采集时无需现场切割。

scenic_valley 按候选坐标稳定哈希选择变体，沿用既有随机朝向、尺寸，不额外消耗地形随机数。碰撞凸包使用新网格，贴地限于模型底部 12% 的实际采样点，避免高处朝下凹面把斜立矿脉压入地下。碎片资源提前加载，碎片凸包点也离线烘焙，避免采集时读取全部三角形顶点。采集仍为矿镐三击、碎裂散落、对应矿石 +1。

旧矿石源路径及原始贴地位置组成 harvest_identity，沿用旧采集存档键。新网格路径仅用于渲染、碰撞与碎片加载；已采集的旧矿脉不会因变体切换复活。

tests/render_ore_variants.gd 生成 tools/basic-tools/ore-variants-preview.png（实际 Godot 渲染，四行依次为铁/铜/银/金）。tests/test_ore_variants.gd 校验全部 8 个凸包与 64 块碎片重组边界。tests/test_scenic_rock_harvest.gd 沿用正式旷野三击、奖励、存档、相邻实例验证。
