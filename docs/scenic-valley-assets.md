# 溪谷植被素材与制作记录（2026-09-06）

## 新增来源

- [Pine Sapling Small](https://polyhaven.com/a/pine_sapling_small)：Poly Haven，Rico Cilliers 建模、Rob Tuytel 摄影；[CC0](https://polyhaven.com/license)。采用官方 1K glTF、bin 和六张贴图，存于 `assets/models/polyhaven/pine_sapling_small/`。下载地址、原始大小和供应方摘要见该目录 `source-download.json`。每个放置点只选择一个变体；用于较矮林缘松树，显示距离 260 米。
- [Pine Tree 01](https://polyhaven.com/a/pine_tree_01)：同为 Poly Haven CC0。只采用针叶枝条的 1K diffuse 与 alpha 图，不下载高面数整树。原始地址：
  - `https://dl.polyhaven.org/file/ph-assets/Models/jpg/1k/pine_tree_01/pine_tree_01_twig_diff_1k.jpg`
  - `https://dl.polyhaven.org/file/ph-assets/Models/png/1k/pine_tree_01/pine_tree_01_twig_alpha_1k.png`
  - 本地为 `assets/textures/scenic_valley/pine_twig_diff.jpg`、`pine_twig_alpha.png`，原图未修改，仅启用 mipmaps。

## 场景自建几何

- `scenes/scenic_conifer.gd`：三种固定种子的分层针叶树，树干、枝干与裁切枝叶网格分离。采用上述贴图左上角枝条 UV 区域，alpha scissor 保留针叶轮廓，避免不透明矩形卡片。几何缓存供实例共享；每棵不足 6500 三角形。碰撞只取主树干，树冠枝叶不参与实体阻挡。
- 树皮复用已有 `fir_sapling_branches_diff_2k.jpg`；林内混入已有 Tree Small 02 / Island Tree 02。
- `scenes/scenic_foliage.gd`：每簇三片不同朝向、长度的分段草叶，根点位于 y=0；弯曲与风摆随叶长增加，草根保持固定。
- 远山自建两层索引网格，坡面/岩层色差由 `valley_mountain.gdshader` 控制。

## 预览与边界

`tests/render_valley_tree_candidates.gd` 用同一光照比较自建针叶树、现有阔叶树和新幼松，输出 `docs/preview/valley_tree_candidates.png`。
正式场景仍使用先实体、后植被的贴地与避让流程。树冠互相接触属于允许的植被叠层，不代表逐三角形完全无交叉。

## 距离分级与性能（2026-09-06）

- 针叶树：0–45 米为 5810 三角形，45–105 米为 2352 三角形，105–450 米为 2 三角形、八方向图集替身。距离按一致的包围盒中心计算；碰撞与贴地仍使用原始树干，分级节点在贴地完成后添加。
- `tools/bake_valley_impostors.gd` 用实际渲染器离线烘焙三个树形，每个图集 4096×512，单方向 512×512。图集启用 mipmaps 和 VRAM 压缩，使用现有 CC0 枝叶/树皮素材。远景为固定日照外观、无动态投影；水平八方向适合本场景地面行走，俯视和动态昼夜需要另行扩展。
- 草：保留 0.25 米采样间距，将网格改为 7×7 个 8 米单元，最大半径 28 米。内圈三叶五段、中圈两叶三段、外圈一叶两段，实际分配 50176 簇、571392 三角形；旧版为 102400 簇、3072000 三角形。根点、地形法线及实体排除蒙版不变。
- 太阳阴影距离 160→55 米；地表植物批次显示距离 125→65 米；导入模型 `lod_bias=0.5` 更早使用导入器生成的简模。大型岩石仍可见至 420 米。
- 分级使用硬切换，避免过渡期重复透明绘制；中景枝条位置和种子保持一致。可以进一步制作抖动过渡，但本轮未实现。

固定入口视角测试：`tests/benchmark_valley.gd`，GTX 750 Ti、D3D12 Forward+、1280×720、关闭垂直同步，预热后采样 240 帧。旧版中位 14.252 ms / P95 16.305 ms；新版复测中位 10.228 ms / P95 12.012 ms。绘制调用 944→510，Godot 渲染图元计数 41339876→20021830（引擎统计，不能等同于唯一场景三角形数）。这是单视角短测，非全程游戏帧率保证，也没有把各项优化收益单独分离。

验证：溪谷 30 项检查通过（含分级预算、贴地、碰撞和返回传送门）；主场景 180 帧、战斗及换弹测试通过。战斗测试中的 ADS HUD 检查因 runner 无状态栏沿用 skip，不作为该项目验收。`docs/preview/valley_perf_baseline.png` / `valley_perf_optimized.png` 为固定视角前后图，`valley_lod_comparison.png` 为同尺度分级外观对比。

近景树形本轮未换：当前规则分层树冠仍有程序生成痕迹。更精细候选为 [Poly Haven Pine Tree 01](https://polyhaven.com/a/pine_tree_01)，CC0；页面标注原始资源约 17M 三角形，不能直接把高模铺满场景。后续应先检查提供的 LOD，选择或制作游戏用近景版本，并从同一模型重新烘焙远景替身，以保证轮廓一致。

## 松树自然化（后续更新，2026-09-06）

本次按用户要求只调整自建松树，其他树种的模型和材质未修改。`scenic_pine_geometry.gd` 提供六种确定性树形：变化的起冠高度、冠幅、偏心方向，每层 4–6 根枝条并错开高度；弯折的主枝、少量下部枯枝、滚转和折弯的针叶卡片打散规则层次。树干采用连续截面、轻微弯曲和根部膨大，树皮 UV 沿高度连续，并复用现有 CC0 树皮法线。

六种近景面数分别为 5464 / 5372 / 5556 / 6016 / 5096 / 5464，全部低于 6500。中景沿相同随机序列保留同位置枝条与更少叶簇；显示距离仍为 45 / 105 / 450 米。六套八方向远景图集另存为 `natural_pine_impostor_0..5.png`，先独立生成验证再切换引用。原始三套图集作为上一版记录保留。

运行时继续按真实树干网格生成碰撞并贴地。新根部范围使局部避让结果略变：本轮接受 518 棵树（408 棵自建松树）、72 块石头、74 个树桩、1573 株地表植物。溪谷 31 项检查覆盖六种树形、近中远预算、树根、碰撞和传送门；主场景 180 帧、战斗和换弹也通过。

独立渲染输出：`valley_natural_pines.png` 为接入前拍摄的旧松树与六个候选对照；`tests/render_natural_pines.gd` 可重建 `valley_pine_variants.png` 六树型图并检查图集取景范围；`valley_lod_comparison.png` 更新为新松树三档效果。游戏入口截图为 `valley_perf_natural_pines.png`。

同配置单次短测（GTX 750 Ti、D3D12、1280×720、关闭垂直同步）：中位 7.633 ms、P95 8.397 ms、553 次绘制调用。背景负载与上一轮可能不同，不将这次结果解读为进一步固定百分比提速。松树仍是使用真实枝叶贴图的程序建模版本，未替换成扫描高模。
