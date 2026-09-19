# ASH-12 贴合式托腮板

为当前 ASH-12 原厂后托制作独立托腮板。新增件包覆顶部与上侧面，原厂后托和枪体保持原样。枪匠入口：ASH-12 → 枪托 → ASH-12 贴合式托腮板；选择原厂后托可移除。配件 ID 为 `ash12_cheek_rest`，仅在 `ue_ash12` 目录登记，当前是外观件，`stats` 为空。

## 造型与装配

- 外观：低矮鞍形聚合物底壳、独立软质托腮垫、四块侧面金属固定片及凹入式紧固件。
- 连接面来源：当前 `ASH12Surface20260919/ASH12_Surface_Editable.blend` 中 `ASH12_Export` 的真实后托表面。使用表面射线采样构造包覆面，包括靠近托底处的宽度变化；不以总包围盒充当连接面。
- 枪体参考坐标：照门为原点，照门至准星为 +X，照门骨骼上向为 +Z。建模段 X 为 -0.307 至 -0.141 米，长度约 16.6 厘米。
- 模型安装原点在该参考系 `(-0.224, 0.0002, -0.065)` 米；FBX 横向反射后的 UE 座位为 `(-22.4, -0.02, -6.5)` 厘米。运行时转换至 `WPN_root`，复用本枪瞄具/握把的参考骨骼变换算法。
- 托腮板跟随枪根，安装不隐藏原厂后托；原枪换弹、机械轨道、冲刺和近战动作继续使用现有资源。

本件采用已有宿主尺寸明确的规则几何分支，在 Blender 内完成曲面取样、壳体与固定片建模；无需生成器猜测后托接口。没有新增武器功能机械设计。

## 材质

三个独立材质槽：`ASH12Cheek_Shell`、`ASH12Cheek_SoftPad`、`ASH12Cheek_Steel`。外壳使用 ASH 当前聚合物色调，固定片匹配 Upper 枪钢，软垫保留橡胶身份。每组均有独立 BaseColor、ORM 和 DirectX 法线贴图，UV0 使用 4 厘米物理尺度；软垫带浅斜纹与细颗粒。

三个湿润材质叠加现有 `WeaponBeads.hlsl`，合并进 ASH 私有 `DA_ASH12_WetMaterials`。没有覆盖现有枪体、瞄具、握把及消音器映射。

## 文件与重建入口

- `read_stock_surface.py` / `stock_surface.json`：制作所需的后托表面数据。
- `author_model.py` / `authoring.json`：模型、UV、贴图、FBX 和正式配件卡片图标的作者入口与参数。
- `ASH12_CheekRest_Editable.blend`：独立可编辑零件、合并导出网格，以及隐藏的后托装配参考。
- `SM_ASH12_CheekRest.fbx`：游戏静态网格。
- `Textures/`：PBR 源贴图；GL 法线仅用于 Blender，UE 导入 DX 版本。
- `ue_ash12_stock_ash12_cheek_rest.png`：实际模型的水平左向、透明背景正式配件图标；并非游戏或验收截图。
- `import_assets.py` / `import.json`：在完整 UE 编辑器、非 PIE 状态下导入、保存和记录实际材质绑定。该脚本不能作为无头 commandlet 运行。
- `install_catalog.py`：只登记 ASH 选项与对应 Cook 目录。

运行目录为 `/Game/Weapons/ASH12/CheekRest20260919`。挂载入口为 `SkeletonStockVisual.cpp`，路径常量位于 `ASH12WeaponAssets.h`。沿用现有枪匠预览、实例装备/保存、整枪图标与掉落装配入口。

## 来源与完成状态

新增外观几何与程序化 PBR 为本地原创制作；宿主参考来自项目现有 ASH 资源，其原始许可保持原有范围，不据此声明可公开分发宿主模型。未新增网络素材。

模型、材质、天气映射及图标已导入保存，`import.json` 为保存完成后的回执。正式 Editor 模块构建成功，日志 `Saved/BuildEditor/build-20260919-213803.log`。

资产导入日志 `Saved/ASH12CheekRestImport.log` 在 `ASH12_CHEEK_REST_IMPORTED` 后进入退出流程，并发生 `ModeManagerInteractiveToolsContext` 编辑器清理错误，后台进程退出码为 3；不能把这一进程称为正常退出。保存函数已成功返回，模型、图标和天气表均在错误前完成保存。

未进行实机测试、动作回归或验收渲染，由用户测试。
