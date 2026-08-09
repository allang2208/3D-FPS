# 原生体素搭建：大小体素混合管线（方案 C）

解决"AI 网格切分体素不满意"的问题：不用 Blender/MagicaVoxel 手工建模，而是
**程序化原生搭建**——直接在体素网格里按数学放方块，解剖比例完全可控，且支持
"大+小体素混合"（主枪 4mm + 弹匣 2mm 合并导出同一个 OBJ）。

## 三条"原生搭建"路径对比

| 路径 | 说明 | 是否适合全 AI 工作流 |
| --- | --- | --- |
| 程序化原生（本方案） | `voxel_ak_builder.py` 直接生成体素网格，`--pitch` 控制粒度，可混尺寸 | 是（主推） |
| Godot GridMap + MeshLibrary | 引擎内搭积木，cell_size 可设不同大小（大小体素=两个 GridMap） | 否（编辑器手工） |
| MagicaVoxel / Goxel | 专业体素编辑器，固定网格（MagicaVoxel 单模型不能混尺寸），.vox 我们已支持导出 | 否（人手编辑） |

OBJ 里每个体素就是一个独立立方体，所以"大小体素"在本管线天然可行：
粗体素（8mm）打底定轮廓，细体素（4mm/2mm）铺细节面。

## 生成器用法

```powershell
cd E:\3d\3-dfps
# 全枪 4mm 均匀（游戏用，~30MB OBJ）
python tools/ai-gen/voxel_ak_builder.py --out assets/models/ak/akm_hand_built_v6
# 弹匣单独 2mm 精细（混合版，~43MB OBJ，弹匣香蕉弧更顺滑）
python tools/ai-gen/voxel_ak_builder.py --mag-fine 0.002 --out assets/models/ak/akm_hand_built_v6_fine
```

输出：
- `.obj`：带面明暗 + AO 的顶点色 OBJ（Godot 直连，枪口默认 +X）
- `.vox`：MagicaVoxel 可开的固定网格（细弹匣不进 .vox，MagicaVoxel 不支持混尺寸）

## v6 弹匣几何（香蕉形关键参数）

- 主体：顶 y=-0.05 → 底 y=-0.28；前缘从 x=0.035 后倒到 x=-0.05（~25°），后缘 -0.085→-0.12
- 底部大半圆弧：圆心 (x=-0.105, y=-0.28)，半径 55mm，最低点 y=-0.335，尾部上收成"香蕉尖"
- 黄铜底板：弧下部 dy > 0.55r 的行用 BRASS
- 扳机护圈在弹匣后方（x -0.165..-0.105），握把在护圈后方（x -0.215..-0.160）

## 已修复 Bug：调色板索引偏移（重要）

2026-08-09 修复：`grid_to_palette` 之前往调色板头部多加了一个黑色槽（0 号），
与 `write_obj_with_colors` 的 `pal[c-1]` 约定不一致，导致**所有颜色错位一位**：
弹匣 STEEL 渲染成 WOOD2 棕色、枪托 WOOD 变灰、DARK 变纯黑；`.vox` 同样错位。
现在与 `voxelize_glb.py` 主流程统一：索引 1..N，调色板不含黑色槽。

受影响文件：修复前的 `akm_hand_built*.obj/.vox`（v5 及更早）。重新生成即修复。

## 验证闭环

```powershell
$env:GUN_VOX_OBJ='res://assets/models/ak/akm_hand_built_v6_fine.obj'
$env:GUN_VOX_TAG='v6fine'
& E:\3d\Godot_v4.7.1-stable_win64.exe\Godot_v4.7.1-stable_win64_console.exe `
  --rendering-driver opengl3 --path E:\3d\3-dfps --script res://tests/render_voxel_gun.gd
```

渲染图在 `user://`（%APPDATA%\Godot\app_userdata\无尽轮回 3D FPS\），复制到
`docs/preview/` 后做：像素轮廓校验（弹匣谷底应前高→中低→后收）+ GLM-4.6V 评审
（`node tools/ai-gen/glm-analyze-image.mjs`）。

## 当前结论（2026-08-09，v7）

- **v7 造型升级**（2mm 全枪高精度）：弹匣香蕉弧加深（前缘后倒 24° + R50mm 圆弧 + 香蕉尖）、
  枪托加长到 -0.50 并收窄、护木改薄 + 6 道散热槽、握把分片前倾、准星加高、枪口制退器加长带侧槽、
  8 色调色板（3 木色 / 3 钢色 / 深色 / 黄铜）
- GLM-4.6V 对照评审：v7 造型 7/10、打磨 6/10；v6(2mm) 仅 4/3。剩余"粗糙感"主要来自体素介质本身，
  以及部件微细节（护木曲线、枪托纹理、机匣小件）
- 文件体积：2mm OBJ ~135MB（文本格式）；Godot 导入后的 .mesh 仅 ~44MB，游戏加载的是后者
- **2mm OBJ 属可再生成构建产物，未提交 git**（太大）；需要时一条命令重建：
  `python tools/ai-gen/voxel_ak_builder.py --pitch 0.002 --out assets/models/ak/akm_hand_built_v7_2mm`
- 候选置入游戏：`assets/models/ak/akm_hand_built_v7_2mm.obj`（等用户确认后替换 weapon_data）
- 若仍嫌粗：下一档是 1.5mm/1mm（.mesh 翻倍到 80~150MB，不建议）；更划算的是继续堆
  微细节（护木曲线、握把纹路、机匣小件）+ 光照/贴图优化
