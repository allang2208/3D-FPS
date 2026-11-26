# 公寓正式地图街角接入

2026-11-10 已实际保存至 `/Game/GameMaps/L_CyberpunkApartment`。继续使用原命令：

```text
open /Game/GameMaps/L_CyberpunkApartment
```

上一轮只保存到 `/Game/GameMaps/Design/L_ApartmentStreetCorner_Subject`，正式地图没有接入，因此用户在原地图看到的仍是旧道路。这是交付目标错误，本轮已纠正。

## 本轮读取到的悬空原因

从正式地图加载的网格和实例变换中提取：旧 `SM_ContinuousRoad_*` 路面 Z 为 -10837 厘米，网格局部 Z 厚度为 0。街角道路中心线下的八个取点，现有 `NB28_Bank_12/13` 地基顶面均为 -10897 厘米；旧路面与下方地基相差 60 厘米。

接入的新道路实体底部为 -10920 厘米、顶面为 -10875 厘米，底部进入原地基 23 厘米。人行道、路缘石、坡道和标线沿用同一套制作标高，摆件按安装基准定位。数值来自现有资产几何和变换的排查，不是运行验收结果。

## 实际修改

- 向正式地图接入街角样板的 117 个 Actor，包括实体道路、三块指定建筑用地、人行道、坡道、停车位和街道家具。
- 从正式地图退下 26 个旧近岸原生 PCG 组合；保留其源资产，没有删除资产库，也没有扩建城市。
- 两个近岸摆件单元改用局部裁剪的副本，避免旧散布与街角重复。原地基和滨江护栏保留。
- 保留当前正式地图中的公寓、对岸远景、交互对象和原公寓出生点；没有将整张样板地图覆盖到正式地图。
- `NearBankPCGRepair20261028/install_level.py` 在当前正式接入回执存在时转入新街角升级器；原全公寓恢复链由此复用新配方。没有运行整条历史恢复链。
- 旧样板发布脚本在正式接入后停止重放，避免从已接入的正式地图再生成重复内容。

## 制作与恢复入口

当前制作入口：`D:/FPS3D/FPSGAME/SourceAssets/ApartmentStreetCorner20261110Formal/install_formal.py`。后续重复接入使用已发布的 `placement_manifest.json`，不再要求打开另一张地图。布局、几何与建筑源仍保留在 `ApartmentStreetCorner20261109`。

正式接入回执：`D:/FPS3D/FPSGAME/SourceAssets/ApartmentStreetCorner20261110Formal/formal_saved.json`。

支承标高记录：同目录 `support_datums.json`；原始资产读取记录：`live_inputs.json`。

本轮正式地图备份：`D:/FPS3D/FPSGAME/SourceAssets/ApartmentStreetCorner20261110Formal/Backups/20261110-002104/L_CyberpunkApartment.umap`。

编辑器在接入前已退出。本轮未主动打开编辑器，没有启动游戏、截图、渲染或追加验收测试。正式地图已通过后台保存操作落盘，实际画面与行走体验交由用户测试。
