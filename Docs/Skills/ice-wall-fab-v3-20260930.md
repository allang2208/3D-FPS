# 冰墙 Fab 冰面与破裂块体 V3（2026-09-30）

用户反馈 V2 仍不匹配游戏风格，并已将 Fab 冰材质导入落盘。本次将运行资源切换到 `/Game/Skills/IceWall/FabIceV3`，包含独立材质 `M_IceWall`、颜色贴图副本 `T_IceSurfaceColor` 和四份 `SM_IceBlock_01..04`；原 `/Game/Ice` 包保留。

## 材质与造型

材质从 `/Game/Ice/Materials/M_Ice6` 派生，复用其 normal、roughness 和 AO 贴图；basecolor 使用独立的 `T_IceSurfaceColor` 副本，以颜色压缩和 sRGB 采样。原贴图中的亮蓝／紫色重新映射为低饱和灰蓝冰芯，细裂纹和宽缓冰面纹理保留。金属度设零，法线强度降低到 0.48，白霜按本地顶点掩码局部出现，避免给每块冰勾整圈白边。

材质采用有光照的不透明 Subsurface。第二层同源色图按视角作小幅 UV 位移，提供浅层内部云纹／裂纹的变化；这是冰体层次的近似效果，不是体积透射或透明玻璃。无自发光。`IceTextureScale`、`FrostAmount`、`InternalIceDepth` 和 `IceNormalStrength` 为后续调整入口；实例随机偏移纹理以减少重复。

四份新网格使用不同的斜切断裂面、缺角、小倒角和浅融蚀起伏，保留 Y/Z 中央承接面；每份约 5700 三角面，使用现有 ISM 实例化。墙体从统一横向砖层改为不同宽度的较大冰体，每列高度切分不同，横缝错开。总宽、高度和厚度继续取原技能快照，矮墙承接顶面仍为 100 cm。没有增加运行时几何生成或材质 Tick。

凝聚体继续一块主体、两块小碎冰，主体略加厚、碎冰缩小，并使用同一套新版材质与网格。凝聚阶段、完成后的火球持杖悬浮点和发射原点保持原接口。

## 玩法接口

本次仅调整外观及实例排列，不改变法杖限定、R 切高／矮墙、预览冻结落点、扣蓝／退款、冷却、伤害、寒冷和修炼。连续碰撞盒、导航和机枪脚架仍由现有接口处理。

中立墙体生命保持 `300 + 50 ×（技能等级 − 1）`，凝聚时快照；每面墙共享一份生命。玩家和怪物可摧毁，不显示战斗血条。

## 制作与保存

- `Tools/Skills/read_ice_wall_fab_sources.py`：读取导入材质并提取本地作者参考，不改变原包。
- `Tools/Skills/author_ice_wall_fab_v3.py`：后台生成 Blender 作者源和四份 FBX，不渲染。
- `Tools/Skills/build_ice_wall_fab_v3.py`：派生专用材质、导入网格并保存；运行中的编辑器通过现有桥批次互斥接入。
- `SourceAssets/IceWall20260930/FabIceV3`：本轮可编辑源、导出、几何记录、导入材质记录及本地纹理参考。
- `Saved/IceWallFabV3/assets-saved.json`：本轮五个资产的实际保存结果。

原包参考商品：[Ice Materials 4K](https://www.fab.com/listings/d55d6be8-d627-4381-b88e-e519f394abb4)。Fab 二进制、第三方贴图及其导出参考保持本机使用，不纳入公开源码。新几何和制作脚本为本地作者源。V2 保留为历史版本，不清理原包或共享依赖。

五个资产已通过已运行的编辑器进程保存。编辑器随后已关闭，本轮未主动打开或重启 UE。Game 与普通 Editor Development 后台构建均成功，二进制已落盘，日志分别为 `Saved/IceWallFabV3/build-game-04.log` 和 `build-editor.log`；未使用 Live Coding。

构建期间并行更新的采集接口曾阻断整体编译，随后以当前源码完成增量构建。另对 `HundredEyedSlagMonster.cpp` 两处 C4458 编译错误仅改局部名称：网格查找器 `Mesh` 改为 `SlagMeshAsset`，伤害参数 `Instigator` 改为 `EventInstigator`，保留原逻辑及其他改动。

未运行游戏、PIE、截图、验收渲染或测试，效果由用户判断。

## 用户棋盘格反馈与采样修复

用户提供游戏内图片，墙体显示灰色棋盘格。该次日志明确报告 `M_IceWall` 无法编译：`Sampler type is Color, should be Normal for /Game/Ice/Textures/T_Ice6_basecolor`。原包这张 basecolor 实际设为 `TC_NORMALMAP`、sRGB 关闭；新增内部冰层却强制使用 Color 采样，导致 UE 回退默认材质。先前的 Game／Editor C++ 构建成功与资产保存，没有代表材质着色器编译成功。

本次只修复材质和贴图设置：复制为冰墙专用 `T_IceSurfaceColor`，设为 `TC_DEFAULT`、sRGB 开启，将表面／内部冰层的三处关联采样统一到 Color。原 Fab 包不修改，网格不重导，C++ 与玩法不变。通过当前编辑器的批次桥执行 `repair_ice_wall_fab_material.py`；最初保存因用户仍在 PIE 被 UE 拒绝，当前试玩结束后完成保存，没有启动新的试玩。

`MaterialEditingLibrary.recompile_material` 本轮返回空错误列表，两项资产已保存，结果位于 `Saved/IceWallFabV3/sampler-repair.json`。重建脚本同步加入专用颜色副本及编译错误处理；后续材质编译失败会明确报错，不继续按成功结果交付。未额外运行游戏测试或截图，修复后的实机外观由用户查看。
