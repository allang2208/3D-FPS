# 螺柱 M-14：下拍背后突出结构修复 V15

> 此为该阶段的制作记录。当前版本、归档位置与恢复依赖见 [整理发布](SpiralPillarM14Publication20261005.md)；不将中间方案视为当前安装入口。

用户要求排查并处理下拍时身后结构突出的现象。针对正式 V14 网格与 V13 下拍片段读取骨骼、权重和变形数据，未启动游戏或渲染。

## 原因

V13 依据材质将所有小块金属色面片并入最近的大铁链区域，却未限制连接距离。根裙附近的一些小块与真实铁链相距数十厘米，仍被赋予 `chain_L_2` / `chain_R_2`；下拍时根裙支撑留在地上，这些面片却被链骨拽到高处。其周围的 6 cm 过渡区也受到同样牵拉。

原蒙皮四权重截断还会突然在第四条根部支撑与 `base` 之间切换，在大幅前倾时产生三角突起。仅重新分配金属面片不能处理这一圈过渡缺口。

## 修改

- 对低于 45 cm、与真实铁链区域的中位距离超过 8 cm 的小块取消远处链骨归属，保持所有原始面、UV 和材质。
- 沿焊接后的实际表面做局部权重连续求解，固定未修改边界；同时覆盖相邻根裙原有的四权重跳变带。材料切缝和 UV 重复顶点共享同一结果。
- 局部最多保留八个权重，网格构建也使用相同上限，避免导入时再次截断为四个。
- 保留原骨架和下拍片段，因此命中 1.20 秒、起手距离、碰撞范围、伤害及冷却不变。V14 九个死亡形态与时序、30 m 喷吐及其提前量/中毒参数不变。

本次更新 64,139 个源顶点，处理 19 个错误归属小块；未删面。

## 针对性源数据排查

原下拍接触帧（1.20 秒）中，背后三个原本贴近根裙的小块中心被拉到约 0.766、0.780、0.787 m 高；修复后约为 0.068、0.069、0.069 m。右侧另一小块从约 0.705 m 回到 0.172 m。

本次修改范围内，大于 3 mm 的源边最大伸长倍率从约 49.15 降至 4.90。剩余最高倍率边长度约 1.5 cm，不能将该数值描述为整身完全无形变或游戏观感已通过。详细范围、面索引与前后数据见制作记录。

## 交付

源文件：`SourceAssets/SpiralPillarM14Meshy20261004/ProductionV15/Authoring/M14_SupportSkin_v15.blend`。

正式蓝图 `BP_SpiralPillarM14` 已切换到 `/Game/Monsters/SpiralPillarM14/SK_M14_SupportSkin_v15`。网格和蓝图均已实际保存，Editor / Game 构建完成。仅做用户要求的源数据问题排查，未启动 PIE、游戏测试或验收渲染，最终观感待用户体验。

制作链：`diagnose_slam_back_v15.py` → `resolve_slam_support_v15.py` → `author_support_skin_v15.py` → `import_support_skin_v15.py`。C++ 静态作者入口 `ASpiralPillarM14::ApplySupportSkin` 只用于离线资产制作，不新增运行时 Tick 或顶点计算。

后台构建最初遇到 UBT 源文件列表缓存未更新；作者函数已归入现有 `SpiralPillarM14Hardware.cpp`，通过 `Build-M14.ps1 -Gather` 重建文件列表后两目标构建完成，保留各次日志。

[问题与修复记录](../../SourceAssets/SpiralPillarM14Meshy20261004/ProductionV15/Records/support_repair.json) · [资产保存回执](../../SourceAssets/SpiralPillarM14Meshy20261004/ProductionV15/Records/ue_revision.json)
