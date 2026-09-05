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
