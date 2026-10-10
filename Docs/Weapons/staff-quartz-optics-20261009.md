# 默认法杖水晶 V36：晶面与几何厚度吸收

用户要求写实、不要过于透明，并提醒此前相似调整效果不佳。本轮接续 V35，优先处理默认白水晶；四种元素晶头继续保留 V33。V22 的整体过白和 V34 被否决均作为约束，不恢复旧羽片、密集裂纹或折射升级。

## 本轮制作

- 模型、晶面法线、0.35 mm 倒角、UV、握点、安装端和碰撞保持 V35。材质通过原有世界／UI 路径接入，不重导模型。
- 从实际安装的 `SM_Staff_head_crystal_false` 读取默认水晶材质槽的三角形，生成以厘米为单位的光学支撑面。按面积保留主要晶面，补齐边界平面；小倒角仍正常渲染，光学厚度中作近似。
- 每像素从当前观察方向和几何法线求入射折弯方向，再求光线离开该有限凸包的距离。该距离用于 Beer-Lambert 衰减，不读取场景深度，不把晶体后方墙壁距离当作内部厚度。
- 世界材质改为单个 Substrate Slab / Simple Volume，完整表面覆盖。晶体透光由厚度和消光系数控制，介质散射反照率保持低值，避免高不透明度与白色漫反射叠加的旧路线。
- 内部光程先换算为等效法线厚度，再交给 Substrate 的透射角修正，避免重复计算斜视衰减。`TransmittanceToMFP` 使用底层 Slab 的 0.01 cm 归一厚度；实际晶体厘米光程已包含在透光计算中。
- 大晶面粗糙度 0.085–0.14，沿用 V35 两张微表面贴图，法线强度降为 0.3，细纹／蚀点／倒角粗糙度追加分别为 0.008 / 0.018 / 0.012。不增加内部羽片、雾絮噪声、体积纹理或屏幕折射。
- 初始消光系数为 `(0.195, 0.184, 0.180) / cm`，介质散射反照率为 `(0.16, 0.17, 0.175)`；这些是本候选制作参数，不是用户已认可的透明度标准。保留独立 `QuartzDensity`、`QuartzExtinctionPerCm`、`QuartzMediumAlbedo`、`QuartzIOR`、`QuartzNormalStrength` 参数。
- G 键仍只驱动现有 `StaffLightAmount`，保留 V32 逆曝光处理。材质发光按局部吸收量分布并抑制根部，增益为 0.38；现有单个点光源、强度、照明动作和开关生命周期不改。
- UI 继续独立 Default Lit / Translucent / Before DOF。覆盖率取同一光程、消光和 Fresnel 的近似，避免双源混合再次造成背包／工作台水晶消失。它是捕获适配，不宣称与世界的体散射逐像素一致。

## 制作源与正式路径

作者目录：`SourceAssets/ApprenticeStaff20260927/QuartzOpticsV36/`。

- `parameters.json`：光学、晶面和照明参数。
- `install_ue.py`：保存原包与 UE 副本，提取现用水晶几何，执行厚度制作，先制作独立候选材质，再写回两件正式材质。
- `author_optics.py` / `optical-geometry.json` / `OpticalChord.hlsl`：几何支撑面与有限光程作者链。
- `ue_material.py`：世界材质与 UI 捕获材质的共用配方。
- `author_editable.py` / `Staff_QuartzOptics_V36.blend`：基于 V35 未修改几何保存的可编辑材质源。Blender 使用自身吸收／散射体积节点；UE 用上述有限光程近似，二者不宣称完全相同。
- `run_install.ps1`：已运行编辑器走现有互斥桥；无编辑器时等待当前构建／commandlet 后执行 D3D12 无界面资产制作。没有 PIE、截图或预览渲染操作。
- `restore_offline.py`：仅在明确需要回退且 UE 已正常关闭后手动运行，恢复两件材质；不自动执行，不关闭进程。

正式世界路径仍为 `/Game/Weapons/ApprenticeStaff20260927/QuartzAimV22/Materials/M_Staff_QuartzDenseV22`；UI 路径仍为 `/Game/UI/GunsmithWorkbench/M_StaffQuartzPreviewV23`。独立候选与 UE 回退副本位于 `/Game/Weapons/ApprenticeStaff20260927/QuartzOpticsV36/`。

V22 材质入口与 V35 现用材质重建入口在 V36 回执 `complete=true` 后委托新配方；V35 继续提供几何。旧源不删除，物品 ID、改造数据、技能、存档、C++ 与静态 PNG 图标不改。

## 制作与验收状态

V36 可编辑 Blender 源已后台保存。本轮 D3D12 无界面资产 commandlet 已完成，退出码 0。两个独立候选材质与两个原路径正式材质均已编译并保存；`install-receipt.json` 为 `complete=true`，四项 `saved_assets`、两项 `installed`。从现用默认水晶的 422 个三角面提取了 26 个光学支撑面，几何未改。两个原材质分别保留 UE 副本和原路径磁盘包。

实际日志：`SourceAssets/ApprenticeStaff20260927/QuartzOpticsV36/install-20261009-122221-commandlet.log`。替换旧 Thin Translucent 图时，设置属性触发过一次中间态警告（旧模式已没有薄透明输出）；完成新图后的 `recompile_material` 返回空错误列表，随后保存成功。作者脚本已把切换旧着色模式移到删除节点之前，避免后续重建再次产生该中间态。没有把此过程描述为零警告，也未据此追加运行测试。

这是有限凸包光程与单层介质近似，没有实现多界面折射、全内反射或离线级体积积分。不以模型名称或编译成功保证观感。没有运行游戏、测试、截图或验收渲染，交由用户测试。
