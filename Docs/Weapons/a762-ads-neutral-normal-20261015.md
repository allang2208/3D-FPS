# A762 ADS 配件墙面法线误用修复（2026-10-15）

用户反馈 A762 的全景红点、机瞄与侧面激光外壳在 ADS 下表面粗糙，出现明显砂粒状起伏和棕色反光。本轮修正实际材质输入，已保存资产；没有重新建模、启动游戏或进行画面验收。

## 根因

当前 `/Engine/EngineMaterials/DefaultNormal` **不是平坦法线**。从现用引擎资产导出的 1024×1024 原图具有砖缝、墙面砂粒和较强凹凸。RGB 范围分别为 58–196、53–202、222–254，RG 标准差约 10.79／10.45。前期制作将该引擎素材当作中性占位图，导致本来平整的配件表面被叠加墙面纹理。

导出原图：[DefaultNormal.png](../../SourceAssets/A762ADSSurface20261015/Input/DefaultNormal.png)。

本轮读取用户已在运行的 A762，红点外壳、后机瞄和激光外壳的天气动态材质均使用该图，`WeaponWetness=0`，`SourceColorWeight=0`，因此这次问题不来自雨滴层或旧底色。激光当前使用 `TacticalDevices20260913/DualFit20261008/A762/SM_laser_1`，其外壳引用同一 A762 专用实例；也纳入了本轮制作定位。

## 已落盘

- 新建 A762 专用中性切线法线 `T_A762_FlatNormal`，16×16、RGB 恒定 128/128/255、Normalmap/BC5、关闭 sRGB 和绿色通道翻转，沿用武器法线纹理组。
- 仅替换实际 `SurfaceNormal` 指向错误占位图的 66 个材质输入：其中 63 个为 A762 已有实例，3 个共享握把实例复制成 A762 私有版本。
- 均衡、幻影、防滑后握把的 A762 网格仅更新相应材质槽绑定。其他枪上的共享原材质保持原样。
- 保留匹配网格的结构法线、Refine06 微法线、细微粗糙度、原色彩与金属身份、玻璃、准星、发光、天气参数和既有几何。没有修改共享母材质或引擎 DefaultNormal 资产。

新增资产位于 `/Game/Weapons/A762/ADSSurface20261015/`。现有 A762 材质继续使用原运行路径，3 个握把私有副本通过原网格的材质槽接入。

## 制作记录

源目录：`SourceAssets/A762ADSSurface20261015/`。

- `capture.json`：实际网格、材质、参数和法线输入。
- `runtime.json`：用户原有运行中的材质参数读取；不是本轮启动的测试。
- `references.json`：停止运行模式后读取的包引用，用于限定 A762 修改范围。
- `recipe.json`、`produce.py`：66 个材质输入及 3 个绑定的制作配方。
- `install.py`、`install_receipt.json`：逐项保存记录、原文件备份及产物哈希。
- `install_saved_bridge.json`：既有编辑器桥返回 `success=True`、`A762_ADS_SURFACE_SAVED 66 materials 3 bindings`，回执 `complete=true`。

首次保存被 UE 的运行模式限制拒绝，只产生未保存的新纹理；用户原有运行随后结束。本轮复用该纹理完成保存，没有关闭、重开编辑器或启动游戏，也没有改动地图。保存完成时没有运行实例，因此 `live_refresh` 为空；下一次运行加载已保存修复。

**已完成资产导入和保存，未进行运行测试、截图或渲染验收，由用户确认 ADS 观感。**

后续制作不得把 Engine `DefaultNormal` 当作中性法线使用；A762 本轮修正优先于旧 Refine06 输入快照里的对应占位值。
