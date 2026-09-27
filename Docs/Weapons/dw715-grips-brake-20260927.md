# Dan Wesson 715：握把与制退器（2026-09-27）

用户选择制作防滑橡胶握把、加大型靶射木握把和左轮专用制退器。沿用在用 715 几何、手部接触和单持／双持装填动作；本轮不开发新准星，也不恢复已取消的枪管改造。

## 枪匠目录

| 槽位 | 配件 ID | 名称 | 游戏数值 |
| --- | --- | --- | --- |
| reargrip | dw715_rubber_grip | 防滑橡胶握把 | 后坐 ×0.90，稳定性 ×1.10 |
| reargrip | dw715_target_wood_grip | 加大型靶射木握把 | 枪械稳定性 ×1.35，开镜耗时 +10% |
| muzzle | dw715_muzzle_brake | 左轮专用制退器 | 后坐 ×0.80，开镜耗时 +5% |

握把二选一，枪口独立选择；每槽保留原厂恢复选项。沿用 `gunsmith.json` → `Normalize/Calculate` → 实例配件／装备存档的现有链路，没有新增存档字段。数值是游戏平衡设定。伤害、射程、六发容量和装填规则不变。同步修正 715 旧特性中“固定 6.8 秒且不能补弹”的过期文案。

## 模型与表面

- 直接取已接受的 `SourceAssets/DanWesson715MetalFinish20260914/DanWesson715_MetalFinish_Editable.blend` 中 `DW715_RubberGrip`，在 `WPN_root` 坐标下保留安装端和握持区；不采用已退役几何。
- 橡胶握把：细颗粒与侧面防滑格纹，保留原厂完整握持轮廓和底缘。
- 靶射木握把：纵向木纹、侧面菱形格纹；只在外露后下缘扩宽、向后延长底托，托掌下表面保持原厂轮廓。底部新增截面环，避免长面片把后端变形传入握持区。
- 制退器：715 专用短型圆角金属壳，双侧开口及可见内孔，固定在枪体而非弹巢；原枪枪管材质分区保持完整。
- 橡胶握把 1,384、木握把 1,750、制退器 11,056 三角面。每件两个材质槽。每种表面使用 2048² BaseColor、Normal、ORM，10 cm 物理 UV；贴图由原创程序材质生成，法线按 UE 导入约定转换。
- 三件模型、18 张贴图、6 个表面材质和专用湿润映射已实际导入并保存至 `/Game/Weapons/DanWesson715/GripBrake20260927`。材质包含现有雨滴图和 `WeaponWetness` 参数，沿用天气系统实例池。
- 已生成 1024² 透明灰度枪匠图标，包括三件选项、握把原厂选项及两个分类图标。图标来自本轮模型；3D 木握把保留木色。

## 程序接入

`DanWesson715FittedParts.{h,cpp}` 负责新网格路径、安装变换和原厂握把分区恢复。使用与现有 715 瞄具相同的参考姿态前／上轴，FBX +X 指向枪口；握把原点为 `WPN_root`，制退器原点为原枪口标记。

- `PhantomRearGripVisual.cpp`、`M4MuzzleVisual.cpp` 增加 715 专属分支。
- 原握把只隐藏 `M_DW715_Hero_Grip`，卸下配件恢复；加载失败时保留原厂握把。
- `PistolDualWieldComponent.cpp` 同步左手原厂握把可见性，再沿用静态配件复制流程。
- 枪口出口沿新制退器本地 +X 延伸 3.4 cm，接入单持与双持现有火光／烟雾出口。不标记为消音器。
- 枪匠预览、背包武器图标、掉落装配沿用共享安装入口；`ColdSteelIconResources.cpp` 加入配件异步预加载路径。
- `WeatherViewEffectsComponent.cpp` 合并新部件自己的湿润映射。既有 `/Game/Weapons/DanWesson715` 打包目录已覆盖本轮资产。

## 制作文件与来源

`SourceAssets/DanWesson715GripBrake20260927/` 保留可编辑 Blender 母版、FBX、PBR、作者脚本、目录更新脚本、UE 导入脚本和实际导入清单 `installed.json`。

现实外观参考来自 Hogue 小框架 .357 橡胶／木握把目录和 EWK 小框架 Dan Wesson 制退器目录；仅借鉴品类与外观语言，没有下载、复制品牌网格或商标贴图。所有安装坐标服务于当前游戏模型，不是实物加工设计。

- https://www.hogueinc.com/firearm-accessories/handgun-grips/dan-wesson/small-frame-357-square-tang/overmolded-rubber-nylon-grips
- https://www.hogueinc.com/firearm-accessories/handgun-grips/dan-wesson/small-frame-357-square-tang/hardwood-grips/cocobolo
- https://www.ewkarms.com/zen8/index.php?cPath=67_29&main_page=index

## 交付状态

源码、目录、模型、贴图、图标和 UE 资产已落盘。现有常规 Editor 构建 `Saved/BuildEditor/build-20260927-164845.log` 已编译本轮六个修改单元（包括新 `DanWesson715FittedParts.cpp`），完成 `UnrealEditor-FPSGAME.dll` 链接并报告 `Result: Succeeded`；后续共享构建继续包含这些对象。本轮尝试的构建命令遇到已有 Build.bat 后已撤下，没有追加重复构建。

未启动编辑器、PIE、游戏测试、验收截图或效果预览；资产通过既有编辑器的互斥桥导入保存，制作的图标属于正式 UI 资产。最终外观、手部接触、换弹与数值由用户测试。

## 用户要求的装配检查与修正（2026-09-27 续）

用户纠正：镜头震动不应作为本件独立属性，改为枪械稳定性 +10%。已移除木握把 `shake_mult`，与原先 +25% 合并为 `stability_mult: 1.35`，显示「枪械稳定性提高35%」；开镜耗时仍 +10%。同时把三件提示统一为「枪械稳定性」「后坐力降低」的现行措辞。目录和作者更新脚本同步修改。

本节是用户明确要求的定向装配检查，更新上面的首次制作未测状态。后台只读导出 UE 已保存的枪身、三件配件、当前 `BarePalmV7/DW715` 手臂和压缩动画，在与 `DanWesson715FittedParts::Configure` 相同的坐标变换下测量、蒙皮和渲染；未启动 PIE。枪身检查渲染使用中性诊断材质，配件使用作者 PBR，因此图片证明几何装配，不作为 UE 最终光照／材质效果验收。

发现并修正：初版木握把的下部扩宽和向下延长侵入托掌区域，最坏抽样新增交叠约 8.86 mm；橡胶下缘初版扩缘也增加最多约 0.70 mm。橡胶恢复全部原厂轮廓；木握把保留托掌面，仅扩大外露后下缘，并插入截面环约束变形。两件已重新导入保存，正式图标同步重新生成。

对**重新导入后的实际 UE 网格**再次读取和检查：

- 两握把安装端／受保护握持区相对原厂表面的最大误差约 0.00009 mm，属于坐标浮点误差。
- 待机、瞄准、开巢、速装器插入、换弹回握五个压缩动画抽样姿态：相对原厂基线，新增手部穿入最大值约 0.0001 mm，没有新增超过 0.5 mm 的顶点。原厂已有的手掌／握把交叠保持原样，本次未声称其为零，也未改动既有手臂。
- 制退器接口近景连续，无可见悬空或堵孔；原枪口标记与实际内孔中心偏差约 0.184 mm，模型装配未发现需修正的可见问题。
- 原厂握把的实际材质槽为 `M_DW715_Hero_Grip`（索引 2），与单持／双持隐藏、恢复代码的目标一致。

证据在 `SourceAssets/DanWesson715GripBrake20260927/FitInspection/`：`fit_measurements.json` 标明 `parts_origin: saved UE assets`，并保存六张装配近景；`*_before.json` 保留初版两握把的 UE 几何。保存记录为 `fit_revision_installed.json`。本次仅修改目录、作者脚本和静态网格，不涉及原生源码，无需重新编译。检查范围不包括全动画逐帧扫查、双持专属动画或实战数值回归。
