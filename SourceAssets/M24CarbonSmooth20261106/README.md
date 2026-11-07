# 玄脊接头曲面与贴图修复 — 2026-11-06

用户截图显示接头折面、凸起，碳托整体变成单色。本次修复针对这两处问题。

## 原因

1. 前次合并按不同 UV 层名保留了多个通道。Native 的碳托图集在 UV2，Advanced 在 UV1，而材质的底色、粗糙度、金属度和法线都读取 UV0。实际 UE 源网格上的碳托 UV0 固定为 `(0, 1)`，因此失去纹理变化。记录见 `source_read.json`、`material_read.json` 和 `ue_uv_before.json`。
2. 原截面包含凹形轮廓。按极角排序会打乱局部边界顺序；在已有细碎三角形上强行形变进一步造成折面。前次“焊接完成”不能代表表面质量合格。

## 修复

- 从未经过 DirectFlush 形变的 Meshy 托身恢复主体。
- 接头沿真实边图排序并按弧长参数化，局部重建 34.5 mm 曲面。主体位置沿用前版，不继续移动抵肩面。
- 机匣接面 Y=-20 mm，碳壳接面 Y=-54.5 mm。规律曲面使用 41 条纵向截环、中间每环 192 个采样；两端接回真实边界，焊成同一网格。
- 端部形状与相邻轮廓斜率决定曲面；限制曲线过冲，继承端部作者法线，重制曲面法线和切线。
- 内腔单独收口，不参与外壳拼接。
- 合并前统一主 UV 层名称为 `UVMap`，保留它为 UV0。主体使用原图集坐标，新曲面从原 Meshy 表面转移图集坐标。
- 沿用原材质的底色、粗糙度/金属度及 DirectX 法线贴图。

## 交付文件

- `smooth.py`：曲面与 UV 制作脚本。
- `M24_Carbon_SmoothUV.blend`：可编辑源。
- `Exports/SM_M24_CarbonSpine_Native.fbx`、`SM_M24_CarbonSpine_Advanced.fbx`：导出件。
- `Before/`：本轮接入前两个正式包的副本。
- `publish.py`：接入原游戏路径、生成三档 LOD、保存资产。导入时读取碳托 UV0 的范围以防止再次塌为常量。
- `saved.json`：实际保存回执；`complete: true` 表示两个正式网格均已保存。

正式引用：`/Game/Weapons/M24/CarbonSpine20261104/Meshes/SM_M24_CarbonSpine_Native` 和 `SM_M24_CarbonSpine_Advanced`。

本轮未启动游戏或生成验收渲染。资产制作及 UV 数据修复不等于用户已认可游戏内观感。
