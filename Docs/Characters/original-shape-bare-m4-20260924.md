# M4 原手型裸手版本

后续状态：用户反馈本版仍有手套表面痕迹，当前 M4 候选已切换到 [平滑与毛孔 V2](original-shape-bare-m4-smooth-v2-20260924.md)。以下保留 V1 的制作记录。

2026-09-24：用户指出原版战术手套已经精确匹配武器，新裸手模型改变了手型，因此改为从原版手模派生。本版仅接入 M4，未批量替换其他武器。

## 已落盘的内容

- 原网格：`/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416`，只读保留。
- 新网格：`/Game/Characters/ModularOutfit20260924/OriginalShapeBareM4/SK_M4_OriginalShape_BareHands`。
- 同目录保存独立手部材质、前臂材质实例和三张 4096 贴图；共用原来的皮肤次表面散射配置及衣袖材质。
- `Content/ColdSteelData/modular_outfits.json` 的 M4 `bare_arms_candidate` 已指向新资产。
- `fps.Outfit.BareArmsCandidate=1` 已有持久配置，本次也应用到现有编辑器。
- UE 保存回执：`SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/saved.json`。

## 制作约束

从原版原生 UE DynamicMesh 派生，继承参考骨架、绑定变换、蒙皮权重、UV、法线分片及三角形绕序。仅移除武器面以提取视模手臂，并调整独立候选的手背表面。没有 FBX 重绑、外部手模替换或动画改动。

手背沿原法线做小幅削平，位移上限 0.6 mm。掌面、指腹、虎口、开放边界及其两圈邻接顶点冻结。前臂和衣袖位置保持原版。纹理包含按原手指骨位置定位的指甲、甲缘、掌纹、关节肤色和浅表起伏；微细毛孔使用随屏幕导数衰减的材质细节。这些是程序制作的皮肤素材，不宣称扫描皮肤或已经达到最终写实验收。

单独复制前臂材质实例并将 `GloveCuffStart` 设为 2，撤去裸手版本的三厘米皮革延伸与卷边；共享原版材质不改。较小的手背几何改动保留源法线，避免重算法线改变其他部位的表现。

## 使用范围

重新进入游戏后，M4 在未穿戴模块衣服和手套时使用本版裸手。装备“原版战术手套”时继续恢复完整原版手模和衣袖。已有模块衣服／其他手套组合以及其他枪械保持原配置，本次没有扩展到这些分支。

运行组件在 BeginPlay 读取配置；已开始的游戏不会因 JSON 修改自动重载。无需为这次纯资产修改重新编译 DLL。

## 可编辑来源与复现

- `SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/M4_OriginalShape_BareHands_Editable.blend`：保留原始形态与裸手手背修形 shape key，附作者接触锁分组及已打包的皮肤贴图。
- `M4_original.json`：原生 UE 导出含顶点／面 ID、原权重、UV、角法线和参考骨骼。
- `M4_bare_shape.json`：候选位置、材料分区及解剖贴图坐标字段；不重新计算权重。
- `texture_source.json`：贴图通道和作者来源。

制作脚本顺序：

1. 现有 UE 桥执行 `Tools/ModularOutfit/export_original_shape_m4.py`。
2. Blender 后台执行 `author_original_shape_m4.py`。
3. Python 3.11 执行 `bake_original_shape_skin.py`。
4. Blender 后台执行 `finish_original_shape_blend.py`。
5. 现有 UE 桥执行 `import_original_shape_m4.py`；全部资产保存后才修改 M4 引用。

M4 原始手模及衣袖沿用项目已有资源及其许可边界，本次没有新增第三方模型或贴图。原版恢复装备的说明见 `original-gloves-20260924.md`。

本次完成制作、材质构建、LOD 构建、导入及保存；未运行游戏、播放动作、截图或进行视觉验收。最终手型与外观待用户测试。
