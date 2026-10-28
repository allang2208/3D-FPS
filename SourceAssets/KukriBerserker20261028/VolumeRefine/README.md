# 狂战士符文与狼首能量柱优化

**当前状态：刀身投射保留；下文整体狼首能量柱被用户退回，已停用。** 活动 HUD 保留原下段玻璃柱，截掉上端尖顶后拼接新的立体狼头设计图，见 `../WolfHeadComposite/README.md`。`install_refine.py` 已转接新 HUD 导入器，不再导入本目录能量柱或 `RuneRelief` 线稿浮雕。

## 刀面检查与处理

- 读取六款源网格、UE活动材质及实际LOD0网格；UE坐标与作者坐标对应为米转厘米，未发现对象非等比缩放或重复UV坐标冲突。
- 原符文固定约1.726×3.799cm，源狼纹长宽比0.4543；旧图集分配约41～63像素/cm，因此横向只占约70～109像素，细线、边缘和弧面遮罩容易丢失。
- 当前改为 `PreSkinnedLocalPosition` 的本地厘米投射，横纵共用同一尺度，直接采样源狼纹；不再通过旧刀面UV重采样。物理镜头透视仍正常保留。
- 用户要求游戏截图时发现 UE 5.8 的该坐标仅供顶点阶段使用。现通过 `VertexInterpolator` 的 `VS → PS` 接入像素投射；六款父材质同修，避免在游戏中编译失败回退默认材质。落盘见 `vertex-interpolation-receipt.json`。
- 每款独立拟合平整刀腹，同时检查正反面、保留边界余量。原装／迅刃／厚背／均衡／猎手约3.225×7.099cm，犬牙约2.793×6.147cm以避开锯齿区。
- 保留原刀面PBR与法线，移除原UV位置的符文高度叠层，避免旧位置留下起伏。接口、模型、战斗参数、存档与图标不变。

## 已归档的整体能量柱

整体重做版本已被用户退回，其模型、贴图、作者脚本与 HUD 着色器已移入 `trash/kukri-mods-retired-20261028/SourceAssets/KukriBerserker20261028/VolumeRefine`。此目录只保留正在使用的刀面投射供体；当前 HUD 使用 `../WolfHeadComposite/README.md` 所述局部拼接方案。归档路径与哈希见 `Docs/Publication/KukriMods20261028/archive-manifest.json`。

## 制作与恢复

- `inspect_projection.py` / `projection-diagnosis.json`：源网格检查。
- `read_runtime_material.py` / `runtime-materials.json`：实际UE材质读取。
- `read_blade_meshes.py` / `runtime-blade-geometry.json`：UE实际刀身网格。
- `fit_rune_projection.py` / `projection-layouts.json`：六款几何拟合及旧UV密度。
- `RuneProjection.hlsl`：当前刀面投射材质源。
- `install_refine.py`：保存到活动符文父材质和HUD；实际完成以 `install-receipt.json` 为准。
- 后台：`run-background.ps1`；已有编辑器时使用项目MCP桥，尊重批次互斥与未保存资产。

本轮仅进行用户要求的符文与HUD定向检查、制作和材质编译，未运行游戏战斗测试。实机观感由用户确认。
