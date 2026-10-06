# RSH-12 加重握把

> 2026-10-05 已接入游戏：RSH 专属「握把本体」栏；稳定性 +15%、后坐力 −10%、开镜耗时 +5%，支持三种防滑纹及双持。模型、材质、图标和基础 DLL 已保存；未运行游戏测试。详细记录见 `Integration20261005` 和 `Docs/Weapons/rsh12-heavy-grip-integration-20261005.md`。下文保留 10 月 4 日的建模阶段记录。

用户于 2026-10-04 要求“先做 rsh 加重握把，出图建模”。本轮交付概念图、独立模型、材质、导出件及 Blender 实际模型图。没有导入 UE、改动枪匠目录、调整数值或修改手臂动画。

## 设计与制作

- 黑色橡胶握持区、深灰金属配重底座，少量外扩掌根承托，细金属后脊。倒角与已认可的方形消音器呼应。
- 从 RSH 原件 `9_l` 保留上端安装区域、虎口、扳机护圈附近轮廓与主要手指接触曲线。下部金属座沿原件真实截面连续过渡。
- 源握持区保留 UV0 和面角法线；新增 UV1 为橡胶表面提供物理尺度，握持壳使用新制橡胶材质。新增配重部位独立制作。底座为外观游戏资产，未制作内部机构。
- 防滑纹采用独立网格，沿原来的侧掌轮廓内缩并圆滑收口，另留出新增装饰紧固件的孔位，在新金属肩部上方截止。既有三种防滑纹可在未来接入时共用这份新表面，不能直接套用原握把整张旧覆盖网格。
- 没有改动现用枪体、其他枪械、在用手型或任何游戏参数。

## 文件

- `Reference/RSH12_HeavyGrip_Concept.png`：内置 image_gen 生成的安装概念与三视图；提示词保存在 `Reference/prompt.txt`。图中外形供设计参考，具体接口由原枪三维数据决定。
- `RSH12_HeavyGrip_Editable.blend`：可编辑分件、打包材质、宿主参考及导出网格。
- `Exports/SM_RSH12_HeavyGrip.fbx`：握把本体，6,920 三角形；原生组件参考帧。
- `Exports/SM_RSH12_HeavyGrip_Surface.fbx`：独立防滑表面，11,080 三角形；沿用原覆盖层网格密度。
- `Exports/SM_RSH12_HeavyGrip_Canonical.fbx`：包含默认防滑层的规范枪体坐标模型。
- `Exports/SM_RSH12_HeavyGrip.glb`：含材质的独立展示模型，共 18,000 三角形。
- `Textures/`：新制 2K 橡胶／金属 BaseColor、ORM、OpenGL／DirectX 法线；原件 PBR 保留原分辨率。
- `Preview/RSH12_HeavyGrip_Mounted.png`：实际模型安装图；原有消音器作为装配参照。
- `Preview/RSH12_HeavyGrip_Detail.png`、`Preview/RSH12_HeavyGrip_Rear.png`：实际模型细节图。
- `prepare_panels.py`、`author_model.py`、`render_preview.py`：依次为表面域、模型和出图入口；`authoring.json`、`Preview/preview_receipt.json`：对应产物记录。

## 后续接入约定

拟用 `ue_rsh12` 专属 ID `rsh12_heavy_grip`，本轮未写入目录。需要独立握把本体槽与现有 reargrip 防滑纹槽组合，或按届时用户决定接入。

组件坐标复用 `RSH12GripSurfaces20261004/authoring.json` 的 `canonical_to_component_m`。实际安装继续使用已接受 RSH 防滑层的组件参考帧到 `WPN_root` 的逆绑定方式，不能再额外叠加美术旋转／偏移。完整矩阵保存在 `authoring.json`。

接入时隐藏／替换原 `9_l` 握把分区，并换用本轮的防滑覆盖层；原厂恢复路径须恢复原件及原防滑表面。单持与双持需使用各自既有绑定链。本轮未执行动画、穿模或游戏测试，不宣称已实机适配通过。

## 来源

上半部握持壳及宿主参考源于 **Rsh-12 by Medji**，CC BY 4.0，来源及许可证见 `Docs/ThirdParty/RSH12-Medji-CCBY4.md`。本轮新增下部造型、后脊、图像概念与 PBR 制作；保留原作者署名。源模型许可不扩展为原生 715 动作和手臂资产的许可。

本轮未启动 UE，未导入资产，未接入数值，未运行游戏测试。模型外观及后续游戏效果由用户确认。
