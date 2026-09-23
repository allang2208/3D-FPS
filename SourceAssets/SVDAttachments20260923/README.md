# SVD 通用改造件作者源

## 2026-09-23 整理后的当前入口

旧换弹导出已由 `SVDThumbUp20260923` 替代；当前模型与材质入口为 `SVDRefinedFinish20260923`。本目录的旧制作记录保留其历史日期与验收边界。已经移走的旧导出、自动备份及恢复快照位于 `trash/svd-superseded-20260923/SourceAssets/` 下的同名目录，原路径、散列及保留替代物见 [归档清单](../../Docs/AssetArchives/svd-superseded-20260923.json)。当前所需 Blend、脚本、参数与原素材仍保留；不要直接重跑旧导入覆盖用户已认可的抓握。新 checkout 的恢复方式见 [SVD 发布说明](../../Docs/Weapons/svd-publication-20260923.md)。

完整范围与行为见 [开发记录](../../Docs/Weapons/svd-common-attachments-20260923.md)。首次接入时用户要求保留原厂枪托、后握把和弹匣，本目录未制作其替换件。2026-09-23 后续用户授权拆分肩托并通过连接杆更换；当前后托源和新视模入口见 [SVDStockAdapter20260923](../SVDStockAdapter20260923/README.md)，后握把和弹匣继续保留。

2026-09-23 后续手部修复的当前动作源转到 [SVDHandRepair20260923](../SVDHandRepair20260923/README.md)，沿用本目录已接入的运行路径。下列模型、材质和配件源继续有效；本目录的旧动画 Blend/FBX 与 `author_animations.py` 作为修复前版本保留，不直接重放覆盖修复后的动作。

后续弹匣内部与 10 条换弹动作源进一步转到 [SVDMagazineFit20260923](../SVDMagazineFit20260923/README.md)：当前模块化视模增加原厂弹匣口缘、内壁和托弹板。不要重导本目录旧整枪 FBX 覆盖完成后的弹匣内部；通用配件本体及材质源继续有效。

## 当前源与产物

- `sources.json`：当前正式供体模型的导入文件、材质图与纹理参数，以及原 SVD 材质／骨架／动作时长。
- `geometry_inputs.json`、`donor_geometry.json`：制作所需的源连通壳、安装坐标和实际源模型尺寸；不是验收报告。
- `SVD_Modular_Editable.blend`：完整共享手臂、SVD 刚性绑定、原动作和原厂消焰器可替换分区。
- `SM_SVD_*.blend`、`Exports/*.fbx`：各配件、活动倍率环及机匣侧桥。原件 UV0／法线保留，UV2 用于本枪金属涂层。
- `SVD_{vertical,canted,prism,angled}_Editable.blend` 与 `Animations/`：四组本枪适配的完整动作源及 48 份动画 FBX。
- `SVD_Coating_Editable.blend`、`Textures/`：依据当前 SVD Receiver 参数制作的 4K BaseColor／ORM，R=AO（本涂层层为 1），G=Roughness，B=Metallic。原配件 AO 和结构法线继续来自原材质图，不声称重新烘焙结构法线。
- `Icons/`：当前配件与原厂部件的透明、水平左向图标和可编辑渲染场景。Blender 使用原贴图、法线、区域遮罩及 SVD 涂层翻译工作材质；UE 特有光学着色由现有运行材质保留，棚拍图不是引擎成像验收。
- `Before/`：本次共享代码修改前的精确文件快照。不得整批恢复覆盖并行修改。

## 制作顺序

1. `background.ps1 -Script read_sources.py`：在现有 UE 批次互斥下后台读取正式输入。
2. Blender 后台执行 `prepare_geometry.py`、`measure_donors.py`，获得连接面及来源坐标。
3. Blender 后台执行 `author_geometry.py`、`author_animations.py`、`author_coating.py`，写出正式作者源和导出文件。
4. `wire_runtime.py` 以唯一锚点修改当前代码与 SVD 目录条目；这是一次性集成脚本，不能在已完成的共享源码上盲目重放。C++ 入口见 `Source/FPSGAME/Weapons/SVDAttachments.h`。
5. `build_native.ps1` 必要原生构建；`background.ps1 -Script import_assets.py` 导入模型／材质／动作并保存。
6. Blender 后台执行 `author_icons.py` 制作实际模型 UI 素材；`background.ps1 -Script import_icons.py` 同步 UE Texture。已完成图标按 `icons.json` 跳过，制作中断可从缺失项继续。

本机 Blender：`E:/Program Files/Blender Foundation/Blender 5.1/blender.exe --background --factory-startup --python <脚本绝对路径>`。

普通 UE 生产调用都使用 `Local\CodexUeMcp-Port-8000` 批次互斥，已存在项目编辑器时保留现场、不另起资产写入进程。原生构建成功不自动打开编辑器。

## 保存回执与复作

`authoring.json` 保存实际底面、侧面接触点、安装变换、源材质身份与分件规则；`animations.json` 保存每段动作源、帧数和时长。`import_receipt.json` 持续写入保存成功的 UE 网格／材质／纹理／动作及干湿映射；`icons_import.json` 记录实际保存的选项／类别图标。

导入脚本按上述回执续作，会跳过已完成的模型和动作。修改几何／动作后应使用新版本目录，或明确移除本任务回执中的相应条目后重新导入；材质图的再次设计应使用新的材质版本，不把复用已完成图当作重建。基础 SVD 老导入器不会生成本目录的新分区，不能覆盖当前模块化入口。

`build_native.log` 记录本轮 Editor 构建成功；`import_assets.log` 含 `SVD_ATTACH_IMPORT_COMPLETE`。没有运行游戏／视觉／存档测试。

## 来源

SVD 几何来自 LeroyCake 的 CC BY 4.0 作品，见 [原声明](../../ThirdPartyNotices/SVD_DRAGUNOV.md)。通用配件与抓握动作复用当前项目已有来源；逐项资产、源文件和材质路径在 `sources.json`，原许可证随各上游目录保留。本次新增精确安装座和涂层不改变上游模型／动作的公开分发许可。
