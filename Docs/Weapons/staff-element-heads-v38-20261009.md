# 杖头定向替换 V38

后续 [V42](staff-element-polish-20261009.md) 已在这些稳定材质路径保存清洁表面与反射调整；本页的 V38 几何和风暴内部闪电继续保留，翠灵几何仍为 V37。

后续尝试的 V39 已被用户否决并要求撤回。冰晶、熔岩和风暴恢复本页 V38，翠灵保留 V37，原厂白水晶恢复 V39 之前的版本；实际回退保存结果及归档路径见 [整理发布清单](../Publication/StaffAndRunes20261010/README.md)。

2026-10-09，按用户最新要求替换三款杖头。已完成模型、贴图、材质编译、正式路径接入与逐件保存。翠灵水晶继续沿用 V37。

| 杖头 | 本次结果 |
| --- | --- |
| 熔岩晶核 | 不规则圆球；多尺度起伏的圆形轮廓、冷却岩壳、橙红熔融纹路与局部流光；去掉 V37 规则板块造型。 |
| 永冻冰晶 | 不透明白色冰晶；使用 Opaque / Default Lit，白色晶面、霜纹和微倒角；删除内部晶针，不再透出后方物体。 |
| 风暴核心 | 保留晶壳，删除中央实体晶核；改为八股主电弧和四条分叉组成的动态核心，路径持续变化，同时包含亮芯、紫色辉光和沿弧移动的电流。 |

## 风暴核心实现

参考 `Tools/Skills/build_lightning_assets.py` 和 `FPSLightningArc.cpp` 的紫色电弧、亮芯、折线与随机放电特征。技能原版一次生成路径、短时保持后淡出；杖头按本次要求持续变幻，专门制作小尺寸常驻版本。

中心是有体积的封闭六边形电弧管体，核心和辉光共用一个材质槽。材质在 GPU 上每秒 12 次刷新路径扰动，刷新间短暂过渡；另有缓慢端点漂移、错开的二次放电与沿弧移动的亮点。不是只让固定线条明灭，也没有保留旧中央实心球。

`core_displacement.hlsl` 使用 UV0 的轴向参数与分支 ID，同一管环的所有顶点得到相同位移。FBX 的 V 翻转在材质里还原。局部位移经 Local→World 转换后写入 WPO，随整个杖头移动与旋转；动画处于原晶壳包围范围内。`core_radiance.hlsl` 控制核心/辉光、短脉冲与电流移动。运行无需新增 Actor、Tick、Niagara 组件或资源加载；正式网格在持械、掉落和动态预览中共享材质动画。

冰晶和熔岩保留原安装面、资产路径与改造 ID。全部材质保留 `StaffLightAmount`；风暴核心继续使用 V32 曝光补偿，没有调整 G 键点光源。未改技能数值、存档、C++、默认白水晶或杖冠。

## 作者和安装

- 作者目录：`SourceAssets/ApprenticeStaff20260927/ElementHeadsV38/`。
- 可编辑源：`Staff_ElementalCrystals_V38.blend`；Blender 内保留三款独立 Editable 集合，实时闪电动画以 UE HLSL 作者文件为准。
- `author_blender.py` 输出 3 份 FBX、12 张 1024 贴图与两个清单；作者三角面分别为冰晶 3552、熔岩 8184、风暴 8404。
- `install_ue.py` 创建 5 件材质，并把三款模型写入原 `/Game/Weapons/ApprenticeStaff20260927/Meshes/SM_Staff_head_crystal_<id>`。
- 新材质/贴图位于 `/Game/Weapons/ApprenticeStaff20260927/ElementHeadsV38`。
- `BarkRebuildV21/import_model.py` 按安装回执依次保留 V33、V37、V38 最新的对应部件；V38 只覆盖三款，翠灵仍绑定 V37。
- 通过已运行编辑器的互斥桥保存；未打开、关闭或重启编辑器。

首轮安装在创建 CustomInput 时遇到 Python 属性写法错误，随后改用 `set_editor_property` 并恢复本批创建的未保存材质。最终 `install-02.txt` 返回 `STAFF_CRYSTAL_CRAFT_V38_SAVED heads=3`，`install-receipt.json` 为 complete，5 件材质最终编译调用无错误；本次 V38 未出现材质编译失败或默认材质回退日志。

修改前实际 UE 网格保存在 `Inputs/`，原资产包保存在 `Before/Content/`；引擎内另保留 `ElementHeadsV38/PreviousMeshes`。没有启动游戏、运行测试或制作验收渲染，动态效果与外观由用户测试。
