# 分节钢甲护手：第一阶段右手结构样件

> 2026-09-29 整理：本页为历史制作记录。旧产物与停用入口已归入 `trash/gloves-chainmail-20260929`；共享建模辅助函数及仍被最终版使用的源保留。恢复清单见 `Docs/Publication/gloves-chainmail-retired-manifest-20260929.json`。

日期：2026-09-27。根据 `metal-gauntlet-plan-20260927.md` 的第一阶段制作。

后续进度：完整双手及独立装备已经交付，见 [钢甲护手](steel-gauntlets-20260927.md)。以下为第一阶段样件的历史制作记录。

## 当前交付

可编辑 Blender 源、FBX 交换文件、原生绑定导入数据及 UE 骨骼网格已经保存。UE 保存通过当时已运行编辑器的 MCP 互斥批次完成，没有启动或重启编辑器、运行游戏、制作验收截图或渲染。

这是一只 M4 原生骨架的右手结构样件。中指、无名指、小指目前只有完整皮革内衬；尚未完成同款双手和其他武器骨架适配，未注册到正式物品目录。

## 几何和绑定

- 10 块独立钢甲：手背主甲、手侧腕甲、前臂侧短护腕、食指三段、食指根护甲、拇指三段。
- 20 颗随所属甲片绑定的铆钉。
- 甲片按当前手套表面和局部手指方向拟合；背侧曲面、指端圆角退让和掌心开放空间由实体几何承担。
- 甲片壁厚起始值 0.9 mm，边缘倒角 0.16 mm，常规外表面距离皮革起始值 1.6 mm；这些是样件制作参数，未作动作接触验收。
- 手背和手侧腕甲绑定 `hand_r`；前臂侧护腕绑定 `lowerarm_twist_01_r`；指甲片各绑定相应 `index_0x_r` 或 `thumb_0x_r`。所有钢甲和铆钉顶点采用所属骨骼 100% 权重。
- 皮革沿用已完成的 OriginalLeatherV2 右手几何、原生软蒙皮和已认可的 TailoredFingerless 材质制作结果。未修改共享裸手、战术手套或动画。
- Blender 源按对象保留甲片；UE 内合并成一个骨骼网格、两个材质槽，沿现有 Leader Pose 路线承接动作。源文件保留完整 M4 原生参考骨架；没有新增动画或独立机械驱动骨骼。

## 材质和制作阶段

`LeatherLiner` 使用项目已保存的 `M_OriginalTailoredLeather`。`ArticulatedSteel` 使用独立钢材样件材质，Metallic = 1、Roughness = 0.34，钢色为线性 RGB (0.32, 0.35, 0.38)。钢材参数在 Blender 与 UE 一致。

当前钢甲使用简单 PBR 参数和几何倒角，未制作正式钢材磨损图集或高低模烘焙。皮革贴图已打包到 Blend 中。钢甲为本次本地参数化建模，没有新增外部模型资源；内衬延续项目现有素材来源。

样件 LOD0 共 31,285 三角，其中皮革内衬 11,713 三角。当前密度用于保留结构源，UE 保存了 3 级 LOD；它不是最终双手版本的面数预算。完整双手阶段需要在已确定的甲片结构上制作游戏低模，尤其减少曲面采样、倒角和铆钉成本。

## 文件

工程根：`D:/FPS3D/FPSGAME`。

- 可编辑源：`SourceAssets/MetalGauntlet20260927/RightSampleV1/M4_RightGauntletSample.blend`
- DCC 交换文件：同目录 `M4_RightGauntletSample.fbx`。UE 使用原生 JSON 绑定导入，避免 FBX 重建原有参考骨架。
- 几何、面角法线、UV 和权重：同目录 `M4_RightGauntletSample.json`
- 部件清单和所属骨骼：同目录 `parts.json`
- 已保存资产回执：同目录 `saved-assets.json`
- 建模入口：`Tools/ModularOutfit/build_metal_gauntlet_sample.py`
- UE 保存入口：`Tools/ModularOutfit/import_metal_gauntlet_sample.py`
- 制作日志：`Saved/metal-gauntlet-right-authoring-20260927.log`
- UE 保存日志：`Saved/metal-gauntlet-right-import-20260927.txt`

UE 骨骼网格：

`/Game/Characters/ModularOutfit20260924/MetalGauntletRightSample20260927/M4/SK_M4_RightGauntletSample`

钢材：

`/Game/Characters/ModularOutfit20260924/MetalGauntletRightSample20260927/Materials/M_SteelGauntlet_StructuralSample`

资产放在现有原生装备 LOD 制作器支持的装备根下，具体子目录独立命名。没有改动物品目录、装备配置、现有装备网格、角色蓝图或存档。

## 后续阶段

下一阶段补齐中指、无名指、小指和左手，完善关节叠片与腕口结构；随后制作正式高低模、钢材 PBR 图集、各原生骨架派生、物品图标和独立装备接入。

本轮未测试。保存完成不代表握拳、扳机护圈、换弹、屈腕或全部武器动作已经无穿插；这些表现交由用户测试，后续按具体反馈修改。
