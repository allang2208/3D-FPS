# 棕色露指手套：裁片皮革代表样件

2026-09-27。用户同意先制作一份代表模型及其单只空手套图标，确定方向后再推广至不同武器骨架。此次范围为 M4 候选，不发布至当前装备目录。

## 设计与制作

保留五指从指根露出、完整掌背主体和短腕口。以现有 `FingerlessHuntV2/FullShell/M4.json` 的覆盖边界、原生骨架、权重为适配输入；原有指根／腕口共边不移动，不重做已认可的握持和换弹动作。

- 增加虎口裁片接缝、弧形手背拼接、闭合短腕带外观及局部受力褶皱。
- 裁片肩部、腕带和褶皱采用连续外皮的向外起伏；没有额外叠放一层完整手套。腕带是闭合外观造型，此候选没有开合机构或动作。
- 内部细分用于描述起伏；原开口边不细分，保留与现有裸露皮肤的连接位置。新顶点按同一条原边插值权重，不重新分配到邻指。
- 沿用工程现有棕色粒面皮扫描源 `Fabric_Generic_Leather_Top_Grain_Brown_xjghdgl`，作者配方增加裁片色差、缝线压痕、磨光分区与暗内衬。
- Blender 与 UE 使用同一套 2048 像素 BaseColor、Roughness、Normal 烘焙贴图，材质金属度为 0、镜面参数为 0.42。Blender 法线为 OpenGL 约定，UE 导入翻转绿色通道；两引擎灯光与色调映射不宣称完全相同。
- 图标为一只空的右手套，透明 320×320、约 91% 轮廓填充；姿态由现有图标专用松弛手型派生，不写入游戏动画。

## 换手套与动画的关系

当前 `FPSModularOutfitComponent.cpp` 通过 `SetLeaderPoseComponent(Source)` 驱动装备部件，部件自身关闭 Tick，没有另一套装备动画状态机。

柔软手套需要蒙皮到掌骨和手指骨，随着多根骨骼弯曲。单个 Socket 可带动刚性饰品，但无法单独完成手套的指关节变形。日常换装切换装备网格／材质，动作仍由源视模提供。

现有各武器有不同原生参考姿态、骨架或绑定，因此当前目录有多份 `rig_meshes`。它们是同一设计的绑定派生，并非多份新动画。无需为每件薄手套复制射击、换弹或近战动画。

棕色露指款通过 `skin_meshes` 和 `glove_in_base: true` 使用“裸露皮肤＋外皮”的配套网格，让开口、腕部与 LOD 共用接缝；它仍跟随原手动画。不能在这份组合模型外再次叠加完整手套。黑色全指款可使用独立跟随部件和覆盖区隐藏。

同版型换色可复用网格；新版型改外形、蒙皮和覆盖边界。厚重护具如果改变握持空间，再考虑局部修正；目前不把未实现的通用姿态修正层写成现成能力。

## 文件与落盘

作者目录：`SourceAssets/ModularOutfit20260927/TailoredFingerlessCandidate/`。

- `M4_fullshell.json`：原生绑定的连续裁片几何源。
- `M4_baked_fullshell.json`、`M4_worn.json`：烘焙 UV 的空壳／穿戴源。
- `M4_TailoredFingerless.blend`：可编辑几何、原生骨架和共用 PBR。
- `TailoredFingerless_Icon.blend`、`TailoredFingerless_Icon.png`：独立图标源与成图。
- `Textures/`：共用 PBR 及裁片作者字段。
- `saved-assets.json`：UE 资产真正保存完成后生成的回执。
- `M4-reference-fragment.json`：后续接入的 M4 引用片段，位于作者目录，不自动覆盖 `modular_outfits.json`。

制作入口分别为 `Tools/ModularOutfit/tailored_fingerless_candidate.py`、`build_tailored_fingerless_candidate.py`、`import_tailored_fingerless_candidate.py`。

候选网格根为 `/Game/Characters/ModularOutfit20260924/TailoredFingerlessCandidate20260927/M4/`；该根沿用现有 LOD 制作函数的路径合同。候选材质与贴图根为 `/Game/Characters/ModularOutfit20260927/TailoredFingerlessCandidate/Materials/`。正式装备、原动画及数值未改动。

后台导入已完成：独立手套、裸露皮肤组合模型、共用材质及三张 PBR 贴图均已保存，两份骨骼网格各生成 3 级 LOD。完成回执为 `saved-assets.json`；后台制作日志为 `commandlet-final-console.log`。首轮因 LOD 作者函数限定资源根而中止，修正候选网格路径后完成保存；没有为此修改原生代码或动画。

本轮不启动编辑器、游戏或 PIE，不进行动作／穿插／运行验收。图标是用户同意的制作交付物，不能作为握枪、换弹或所有 LOD 无穿插的证明。方向由用户选定，运行表现由用户测试。
