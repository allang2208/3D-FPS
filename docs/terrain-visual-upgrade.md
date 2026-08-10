# 地形视觉升级方法（Terrain3D + Godot 4.7）

本文沉淀对照 trrran 封面参考图（溪流场景）升级地面/水体质感时验证过的方法，
供后续直接复用。

## 1. 地面颜色层次：colormap（RGB 相乘 + alpha 湿润度）

Terrain3D 的 colormap 是官方"颜色变化"方案：

- RGB 在 shader 里与地表贴图**相乘（只会变暗）**，所以值要贴近 1.0、
  变化要克制（subtlety is key），否则出色块。
- Alpha 通道是 **wetness（粗糙度修正）**：0.5 = 中性，0.3 ≈ 粗糙度 -40%，
  0.7 ≈ +40%。河床边降到 0.30 就能做出"湿泥反光"。

程序化生成（见 `scenes/demo_terrain.gd` 的 `_build_colormap()`）：

- 尺寸/位置与高度图严格 1:1（本项目 1024x1024，导入在 -512,-512）。
- 河床走廊（dist < 70m）：暖棕 `(0.88, 0.84, 0.76)` 过渡到岸草绿。
- 大尺度 patch（Perlin freq 0.0045）：暖阳斑 `(0.90, 0.92, 0.84)` /
  冷岩斑 `(0.86, 0.89, 0.90)`，叠加 ±0.04 细噪声。
- wetness：dist < 16m → 0.30，16-32m 渐变回 0.5。

接入方式：`data.import_images([height_img, null, color_img], pos, 0.0, scale)`，
数组顺序是 [Height, Control, Color]。区域文件会变大（colormap 写进去了）。

## 2. detiling 法线对齐检查

官方 channel packer 的规则：开 detiling 旋转前，整张法线图的**平均法线
（归一化后）z 必须 ≥ 0.999**，否则旋转后出反光棋盘格/发灰。

检查/修复工具：`tools/orthogonalize_terrain_normals.py`（默认检查 9 套
`terrain_prepared/*_nrm_rgh.png`，z < 0.999 时用与 channel_packer 相同的
旋转基对齐，保留粗糙度 alpha）。AmbientCG NormalGL 实测全部已对齐。

## 3. Godot 4.7 屏幕空间折射（重要 API 变化）

Godot 4.7 已移除内置 `SCREEN_TEXTURE`，shader 会报
`SCREEN_TEXTURE has been removed in favor of using hint_screen_texture`。
正确写法（见 `assets/shaders/river_water.gdshader`）：

```glsl
uniform sampler2D screen_tex : hint_screen_texture, repeat_disable, filter_linear;
// fragment():
vec3 refracted = texture(screen_tex, SCREEN_UV + wave_distortion).rgb;
```

水面中心 alpha 从 0.50 降到 0.34、深水 0.62 → 0.46，配合折射后
"清澈见底"感明显（GLM 对比确认四项均改善）。

## 4. 渲染对比基线（血泪教训）

- **必须同渲染器对比**：`--rendering-driver opengl3` 走 Compatibility
  渲染器，天空/亮度/SSR/SSIL 全都不一样，会误判为"改坏了"。
  项目真实渲染是 D3D12 + Forward+（project.godot 里 `rendering_device/driver.windows="d3d12"`），
  对比图用不带 driver 参数直接跑。
- 旧预览图可能对应旧环境参数（如天空 energy 1.5 时代），不能当"改动前"基线；
  用 `git show HEAD:...` 还原当前 commit 的代码重新渲染一份基线。
- 像素采样看均值/std 只能确认量级，细节是否改善以 GLM-4.6v 视觉对比为准。

## 5. 回归验证

```powershell
godot --headless --path E:\3d\3-dfps res://tests/test_terrain_regression.tscn
```

断言：216 棵树全部贴地且带碰撞、地形 RID/射线命中有效、4 类资源可加载。

注意：`tests/test_tree_grounding.gd` 这类 `--script` 单测加载不了 HUD
autoload，场景起不来（count=0），不是回归，以 .tscn runner 为准。
