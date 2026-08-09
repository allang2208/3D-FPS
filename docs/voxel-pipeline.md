# 枪械体素像素风格管线（方案 A + B）

## 方案 A：程序化体素化（全自动，已完成）

`tools/ai-gen/voxelize_glb.py`：把 AI 生成的枪模 GLB 切成高精度体素，
颜色从贴图按最近表面点 UV 采样，量化到 <=256 色调色板。

```powershell
python tools/ai-gen/voxelize_glb.py `
  --input assets/models/akm_trellis.glb `
  --pitch 0.005 --out assets/models/ak/akm_voxel_m --palette 96
```

输出：
- `.vox`：MagicaVoxel 原生格式（方案 B 精修用）；
- `.obj`（带 0..1 顶点色）：Godot 直连预览。

参数：`--pitch` 体素边长（0.005=0.5cm，枪长 ~200 格，属高精度）；
`--palette` 调色板颜色数（风格统一用）。

## 方案 B：MagicaVoxel 手工精修

1. 下载 MagicaVoxel（免费单文件）：https://ephtracy.github.io/
2. 打开 `.vox`，直接改体素（垫高准星、加长弹匣、修轮廓）；
3. 保存回 `.vox`；
4. 若直接用 Godot：装 Godot 插件
   https://github.com/cschram/godot-vox-import 导入 `.vox`；
   或从 MagicaVoxel 导出带顶点色 OBJ 替换 `akm_voxel_m.obj`。

## 接入游戏

`weapon_data/akm_voxel.tres` 已配好（model_scene → 体素 OBJ，顶点色无光照材质）。
换枪：gun.gd 的 `data` 换成 `akm_voxel.tres` 即可；ADS 自动校准照常生效
（枪口方向默认 +X、前准星缺失时水平瞄线兜底）。

## 已知注意

- OBJ 顶点色必须是 0..1 浮点（Godot 按浮点解析，0-255 会全白）；
- 体素模型网格 ~14.6 万顶点，视模可用；更多武器批量生成时注意仓库体积；
- 渲染风 = 无光照 + 顶点色（像素感）；如需立体感可改 Flat/Toon 光照。
