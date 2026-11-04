# 战斧装备栏／背包图标留白修正

用户反馈两个位置都偏大。本轮依据武器工作流和 UE UI 的 `runtime-icon-pipeline.md`：使用实际装配/PBR、正交镜头、轮廓居中、主轴约 91%、2×3 作者画幅，并按各卡片的可用区域等比显示。

原因是战斧继承了细长单手近战的 `FrameImportedTexture` / `FrameVisiblePixels` 处理：目录 PNG 虽有正确留白，加载成画刷后 UV 被裁到 alpha 轮廓附近，ImageSize 也被缩至紧边大小。装备栏和背包再拟合时会将轮廓放大，运行时动态图就绪后同样如此。

修正仅针对 `ue_tactical_hatchet`：目录图与动态图保留 256×384 原画布及透明留白；继续使用既有装备槽独立拟合、背包横竖转向的等倍率计算及拖拽显示。不添加人为缩放倍率，不改占格、模型、动画、材料或改造选项。法杖、弯刀及其他武器保留原处理。

- 源码：`ColdSteelInventoryWidget.cpp` 的目录图导入、`ColdSteelWeaponIconReadback.cpp` 的动态图发布。
- `export_icon.py` 通过正式 UE 目录管线重新出图并部署到运行 PNG 与当前作者源目录；`Before` 保存本轮开始时的图标。
- `editor_build_receipt.json` 记录已复用的共享 Editor 成功构建，`build_receipt.json` 记录接续的目标构建；`export_receipt.json` 记录实际出图及部署状态。初次编译期间并行修改导致的旧报错保留在 `build-FPSGAMEEditor-first-attempt.log`，不是最终构建结果。
- 本轮未启动编辑器界面或运行游戏测试，实际界面效果由用户测试。
