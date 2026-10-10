# 四种杖头改造模型与材质 V37

后续用户指定的三款替换已接入 [V38](staff-element-heads-v38-20261009.md)：熔岩改为不规则熔岩球，冰晶改为不透明白色，风暴改为持续变幻的闪电核心。翠灵继续使用本页 V37。下文保留 V37 的制作记录。

2026-10-09，按用户“其他所有的杖头改造也要优化，提升材质和模型表现”制作并接入。范围为永冻冰晶、熔岩晶核、翠灵水晶、风暴核心四款；当前目录的四个 `head_crystal` 非默认选项全部包含。

## 已落盘内容

| 杖头 | 几何调整 | 材质调整 | 作者三角面 |
| --- | --- | --- | ---: |
| 永冻冰晶 | 六棱主晶面保留；双段微倒角；内部矿物针缩细 | 冷蓝晶体、纵向生长纹、清透面与纹理分区粗糙度、克制的斜视覆盖率 | 3612 |
| 熔岩晶核 | 黑曜岩板块边界下沉，真实凹槽；板块边缘小倒角 | 熔融信号直接烘焙自凹槽面，岩壳微蚀坑、干湿粗糙度差、局部橙红发光 | 9664 |
| 翠灵水晶 | 三段抛光倒角、面积加权法线，保留主要切面 | 深浅翠绿矿物层、稀疏浅脉、低强度次表面散射和细微抛光纹 | 4500 |
| 风暴核心 | 晶壳双段倒角、切面核心、六条主雷弧及六条分叉，封闭六边形管体 | 烟紫晶壳、低粗糙度、雷弧按顶点相位错开闪动 | 7020 |

四款连接座保留原底部安装面，在上部硬边补充 0.28 mm 倒角并增加青铜加工纹。沿现有 V33 向内收缩的轮廓重制，沿用 V21 母版中相同的部件原点、厘米坐标、颈部和杖冠连接关系。默认白水晶 V36、杖冠、杖杆、握持、施法尖端、技能数值、改造说明、存档和 C++ 均未改动。

## 资产与重制入口

- 可编辑母版：`SourceAssets/ApprenticeStaff20260927/ElementHeadsV37/Staff_ElementalCrystals_V37.blend`。四款都有独立 Editable 集合与打包贴图。
- 作者：同目录 `author_blender.py`；`build_author.py` 从现有 V33 烘焙器构建独立 V37 作者脚本，制作输入是 `BarkRebuildV21/Staff_NaturalBark_V21.blend` 中同形原始头部。`Inputs/` 保存修改前从实际 UE 正式资产导出的四款 V33。
- 导出：`Export/` 四份 FBX；`Textures/` 为 15 张 1024 方形贴图；`meshes.json` 与 `materials.json` 记录网格和材质绑定。
- 引擎新资源：`/Game/Weapons/ApprenticeStaff20260927/ElementHeadsV37`，7 件材质、15 件贴图、4 件导入网格。
- 正式运行仍用 `/Game/Weapons/ApprenticeStaff20260927/Meshes/SM_Staff_head_crystal_<id>`，四个 ID 为 `frozen_crystal`、`magma_core`、`jade_spirit_crystal`、`storm_core`。
- 导入入口：同目录 `install_ue.py`。使用现有编辑器内的批次互斥桥完成导入、材质编译、网格内容替换及逐件保存，没有另起 UE 进程。
- `BarkRebuildV21/import_model.py` 在 V37 安装回执 complete 后优先使用 V37 FBX 与材质，后续整杖重导不会回退到 V33。

每款保留原有 2 或 3 个材质槽；连接座材质共用。半透明晶壳继续使用 Default Lit / Surface Per Pixel Lighting / Before DOF，保留现有预览覆盖率路径，不混入 Thin Translucent 输出或 Substrate 图。未增加透明壳层或折射层。

材质继续暴露 `StaffLightAmount`，母材质默认 0，沿用 V32 曝光补偿及单点光源。常驻发光局限于凹槽、矿脉和内部雷弧；没有提高点光源亮度、增加组件、动态加载或游戏 Tick 逻辑。

## 保存边界与备份

`author-receipt.json` 记录四份模型及贴图烘焙完成；`install-receipt.json` 记录 4 件正式资产已安装、7 件材质编译调用无错误以及全部逐件保存结果。桥输出 `install-01.txt` 返回 `STAFF_CRYSTAL_CRAFT_V37_SAVED heads=4`。本批次安装日志未报告材质编译失败或默认材质回退。

修改前的正式网格及其实际绑定材质包保存在 `ElementHeadsV37/Before/Content/`；引擎内旧网格另保存在 `/Game/Weapons/ApprenticeStaff20260927/ElementHeadsV37/PreviousMeshes`，仍绑定 V33 材质。

这是制作、材质编译与接入完成记录。没有启动游戏、执行测试或制作验收渲染；新外观未获用户视觉确认，由用户测试。
