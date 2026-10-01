# SVD 原装弹匣浅压纹修订（2026-10-01）

本记录为 Satin02 当次范围；随后已在 [Refine03](svd-refine03-and-reload-return-20261001.md) 中将浅压纹扩展至加长弹匣，并加入整枪分层与局部倒角法线。

用户反馈 WS1 升级后的原装弹匣表面偏粗，防滑纹设计不好。本轮只修改原装弹匣的两个现有材质实例，已通过当前编辑器的批次互斥接口保存。未启动游戏、截图、渲染或另行测试；视觉效果由用户测试。

## 已修改

- 侧板原有较鼓的横纵交叉法线，改为三条连续、圆头的浅纵向压纹。按弹匣独立 UV0 图集的两个侧板区域处理，等效压纹高度 **0.06 mm**、半宽 **2 mm**；这是材质法线的制作尺度，没有增加模型厚度或面数。
- 侧板以外继续使用完整原法线；上部边带、口部、底板、卷边和其他图块不重画。原几何的纵槽与外轮廓保留，侧板边缘渐隐衔接。
- 在同一侧板区域减弱旧浮雕 AO，避免新浅纹下仍残留很黑的交叉纹阴影。
- 原装弹匣壳粗糙度从 **0.42 → 0.34**，弹匣自身接口／底板槽从 **0.46 → 0.37**；细颗粒粗糙度幅度 **0.03 → 0.009**，低频粗糙度幅度 **0.02 → 0.004**，同时减弱凹部反差和边缘磨损。

## 实际资产

新的独立母材质：

`/Game/Weapons/SVDDragunov20260922/SurfaceStandard20261001/Master/M_SVD_WS_FactoryMagazineSatin02`

保留以下实例路径，修改其父材质和局部参数：

- `MI_SVD_WS_SVD_SM_SVD_Magazine_001`
- `MI_SVD_WS_SVD_SVD_InterfaceSteel`

实例均位于 `/Game/Weapons/SVDDragunov20260922/SurfaceStandard20261001/Materials/`，仍绑定当前 `StockAdapter20260923/SK_SVD_ModularStock` 的对应槽。

现有天气表中的实例自映射继续指向相同资产。浅压纹接在 `WS_WetNormal` 的原法线输入之前，水膜及水珠仍由 `WeaponWetness` 驱动；没有修改天气代码或追加一层水膜。

本轮没有改动网格、UV、骨架、动作或扩容弹匣，也没有覆盖公共纹理和原 WS1 母材质。扩容弹匣继续使用原版本的母材质与独立实例。

## 可编辑制作入口

`SourceAssets/WeaponSurface20260930/SVD/MagazineSatin02/`：

- `PanelNormal.hlsl`：侧板区域及浅纵纹形状。
- `recipe.json`：两个目标实例、粗糙度和压纹尺度。
- `apply_finish.py`：新私有图、实例修改与保存。
- `Before/`：两个实例修改前的原包备份。
- `apply_receipt.json`：两个实例的实际保存结果，`complete: true`、`tested: false`。

SVD 的 `install_all.py` 已将这一步加入最后阶段，后续完整重装材质时会继续应用本次修订。
