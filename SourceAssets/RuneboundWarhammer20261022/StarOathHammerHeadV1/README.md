# 星誓·封界之砧 · 精细模型 V1

本阶段按已选概念图制作符文战锤专属的成对外锤头，采用本地 Blender 精确建模。不是概念图贴片，也不是图生 3D 候选。此目录记录模型、材质、UV 与静态导出；后续改造台与被动接入已在 `../StarOathIntegrationV1/` 完成，数值和正式交付见该目录。

## 交付入口

- `StarOathHammerHead_Assembled_PBR.blend`：完整 PBR 装配源，新锤头安装在原装中央锤座、锤颈、长柄、握持与配重上；旧原装锤头隐藏保留。
- `StarOathHammerHead_Editable.blend`：逐件可编辑制作源，保留分层甲片、压爪、刻字工具、布尔凹刻、倒角与程序化材质。
- `Export/StarOathHammerHeads_V1.glb`：自包含的成对锤头模块，含表面贴图、宝石和能量材质。
- `Export/SM_RuneboundWarhammer_StarOathHammerHeads_V1.fbx`：静态模块导出，显式三角化并导出作者法线与切线。
- `Textures/`：4096² BaseColor、切线 Normal 与 ORM。全部贴图已打包进 PBR 装配 Blend。
- `production_receipt.json`：实际制作输出、面数、包围盒、材质分区、贴图通道与未测试状态。

## 几何制作

左右锤头各采用连续承力锻铁芯、六层有厚度的八棱甲片、凹陷分层缝及窄黄铜束带。正反侧面各一处圆形封印核心，两个外端面各一处核心，共六处。每处包括闭合承台、金属包镶、凹刻符带、双道细嵌线、逐枚珠边、实体压爪与沉头紧固结构。

符带使用 24 种独立角形符号组合：四个侧面各 28 枚、两个端面各 32 枚，共 176 枚。符纹由实际布尔凹刻形成，并在槽内嵌入细金属线；不是烘在底色上的黑色字样。光学核心采用 32 分段多层切面，内部有独立的星形封印与发光丝。拱形支肋、分支能量槽、轴向脊条与细线追刻均有实体厚度。

保留第一人称近景的轮廓和装饰层次，没有全局减面或自动 LOD 缩减。最终实际三角形数量以生产回执为准，面数不代表运行帧率或用户视觉验收。

## 材质

正式模块有四个材质分区：

| 材质 | 用途 |
| --- | --- |
| `M_StarOath_PBR_Surface` | 暗铁、旧银护边、宽黄铜束带及原装接口的 4K 烘焙表面 |
| `M_StarOath_FineInlay_Brass` | 符槽嵌线、微型珠边与细束线，保留近景细线辨识度 |
| `M_StarOath_Optical_Crystal` | 非金属蓝色切面晶体，IOR 1.52，透射与清漆分层 |
| `M_StarOath_Rune_Energy` | 核心内封印和蓝色导能槽，`EnergyTint`、`AwakeIntensity` 独立控制 |

锻铁锤击凹凸、金属细颗粒、方向性细划痕、凸缘磨亮和局部氧化以同一实际米制坐标制作，并烘焙至正式表面贴图。低起伏细节不会改变安装面和主体轮廓。

`T_StarOath_BaseColor.png` 使用 sRGB；`T_StarOath_ORM.png` 为线性数据，R=AO、G=粗糙度、B=金属度；`T_StarOath_Normal.png` 为 OpenGL 切线法线，接入 UE 时应设置法线压缩并翻转绿色通道。细嵌线保持独立材质，避免小于毫米的图形依赖极小图集岛。

## 装配合同

作者空间为米制、Z 向上。锤头沿 X 轴成对分布，模块 pivot 为原作者空间 `(0,0,0.916)`，导出模块自身原点归零，UE 装配偏移为 `(0,0,91.6)` 厘米。原装连接面为左 `X=-0.0354452141m`、右 `X=0.0345547859m`，内侧 9mm 接口带由当前原装网格直接保留，包含原 UV；新承力芯在接口外重建。

宿主引用来自 `../ModulesV1/RuneboundWarhammer_Modular_Editable.blend`。原中央锤座和其他五件原装模块未改写；宿主参考只存在于本轮独立 Blend 中，不包含于单独锤头 FBX/GLB 导出。

## 重建与状态

后台重建入口：

```powershell
& 'E:\Program Files\Blender Foundation\Blender 5.1\blender.exe' --factory-startup -b --python-exit-code 1 --python 'D:\FPS3D\FPSGAME\SourceAssets\RuneboundWarhammer20261022\StarOathHammerHeadV1\author_model.py'
```

原概念图位于 `../LegendaryHammerHeadConcept20261023/`；`design_contract.json` 固化造型与安装范围，`host_contract.json` 保存原模块与接口采样，`author_model.py` 保存完整可重建的制作过程。

建模阶段没有打开 UE、进行游戏测试或生成验收渲染。后续接入阶段已保存新 UE 资源、发布改造台条目并实现最终确定的“封界震荡”与两项攻击力加成，详见 `../StarOathIntegrationV1/delivery_receipt.json`；原有动画配置继续复用，未进行游戏测试。
