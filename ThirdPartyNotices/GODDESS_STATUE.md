# 女神石像（Diana）第三方素材声明

本声明用于 CC BY 4.0 的署名要求，随项目对外分发时保留。

## 模型

- **作品名**：Diana
- **作者**：noe-3d.at（<https://sketchfab.com/www.noe-3d.at>）
- **来源**：<https://sketchfab.com/3d-models/diana-ea77e1d0442244aeb3d558a08ccdfc1a>
- **许可**：**CC BY 4.0** — <https://creativecommons.org/licenses/by/4.0/>
- **获取日期**：2026-09-22
- **用途**：地牢场景中作为「女神像」事件道具的静态网格（`/Game/Dungeons/GoddessStatue20260922`）

要求的署名文字：

> "Diana" by noe-3d.at, licensed under CC BY 4.0.
> Source: https://sketchfab.com/3d-models/diana-ea77e1d0442244aeb3d558a08ccdfc1a

## 修改说明

按 CC BY 4.0 的要求记录对原作的改动，本项目对该素材做了以下加工：

1. 等比缩放到 2.05 m 总高，并把底面中心移到原点（未改动比例与形状）；
2. 漫反射图集由 8192×8192 降采样到 4096×4096 作为游戏贴图；
3. 在 UE 内新建材质 `M_GoddessStatueDiana` / 实例 `MI_GoddessStatueDiana`（原 glTF 材质只有 baseColor），
   粗糙度、金属度、高光为项目设定的参数值；
4. 关闭 Nanite，碰撞改用三角面（`CTF_USE_COMPLEX_AS_SIMPLE`）。

网格拓扑、UV、法线与贴图内容未修改，未重新烘焙。

## 边界

本项目其他素材的许可不受本声明影响；本声明不覆盖该模型页面上的任何第三方衍生内容（该模型为作者自行扫描，Sketchfab 页面未列出额外来源）。
