# 色彩增强候选（尚未接入正式游戏）

用户撤回毒液/胖子灰化统一方向后，改为普通、矿工、奔跑及三款换皮增强色彩。毒液和胖子保持原材质。本提交保留候选，不自动改变正式随机换皮的颜色。

base-comparison.jpg、variant-comparison.jpg 每组左原色、右增强。family-comparison.jpg 为三款增强后与原版毒液、胖子的同灯光对照。

Blender Hue/Saturation 节点 Saturation=1.65、Value=1.08、Hue 默认；这些是本候选参数，不是所有怪物的标准。只修改颜色贴图，保持几何、骨架、蒙皮、16 段动画、法线及粗糙度。

运行 `python rebuild.py`，从仓库现有模型和原换皮生成六个 `generated/*-unified.glb`，并断言原几何、骨架、动画及二进制前缀保留。GLB 为可再生输出，不重复存六份几何。随后可用 Blender `--background --python bake.py -- modern`（或 miner、runner、modern-variant 等）重烘焙并生成可编辑 .blend。

本地原始可编辑文件和完整预览保留于 E:/无尽轮回/3d/zombie-color-rich-v01-20260907。正式仓库保留六张最终 2K 贴图、重建脚本、来源许可和三张对照图。历史 preservation.json 来自最初候选；generated/preservation.json 为本次重建结果。

已完成最初六个 GLB 的 Godot 4.7.1 D3D12 正侧背渲染；这不是正式游戏整场战斗验收。胖子仅在对照中显示缩放 1.30。
