# 模块化手部装备制作入口

本目录脚本面向 `D:/FPS3D/FPSGAME` 本机 UE 5.8.2 工程，不是带完整素材的独立工具包。执行前按脚本具体输入恢复已许可作者源，并按本次款式设定输出；不要按文件名排序执行整个目录。

当前合同见 [第一人称装备标准](../../skills/ue5-fps-arms-animation/references/first-person-equipment-workflow.md)；完整本机依赖和归档记录见 [发布／恢复说明](../../Docs/Characters/modular-outfit-publication-20260925.md)。

## 当前制作顺序

| 内容 | 制作 | 可编辑源 | 导入／接入 |
| --- | --- | --- | --- |
| V7 裸手 | `author_bare_palm_v7.py` | `save_bare_palm_v7_blends.py` | `import_bare_palm_v7.py`，然后 `bake_native_bare_defaults_v7.py` 写入基础视模 |
| 贴合薄皮手套（黑） | `author_fitted_field_gloves.py` | `save_fitted_field_gloves_blends.py` | `import_fitted_field_gloves.py`（只发布黑色） |
| 猎装短手套（棕） | `author_hunt_field_gloves.py` | `save_hunt_field_gloves_blends.py` | `import_hunt_field_gloves.py` |
| 贴合衣袖 | `author_fitted_sleeves.py` | `save_fitted_sleeves_blends.py` | `import_fitted_sleeves.py` |
| 背包图标 | `render_equipment_icons.py` | `ItemPresentation.blend`（由 `author_item_presentation.py` 产出） | 直接写 `Content/ColdSteelData/Icons/ModularOutfit20260924/*.png` |

## 装备背包图标（2026-09-25）

`render_equipment_icons.py`（Blender 无头）取代 `author_item_presentation.py` 的出图部分，按背包统一规则重出上衣与手套图标：画幅按 `BaseFootprint` 的占格推导（3×3 与 2×2 都是 320×320，`grid_w/grid_h` 在 `ColdSteelInventoryRules.cpp:37` 优先于槽位默认，所以 `armor` 的 3×4 默认不参与），主轴填满 91%，轮廓中心落在画幅中心，透明底。装备按用户确认保持**竖直**，不做近战／工具那种横置。

出图部分单独成脚本是因为 `author_item_presentation.py` 同时会重导拾取 FBX，图标返工不应连带改动已导入的模型。

旧图标过曝 2.1–2.9 倍：`Standard` 视图变换之外，0.5 强度的环境光与 160/90/130 W 面光把深棕（0.18,0.085,0.035）冲成肤色、近黑（0.026,0.03,0.034）冲成浅灰，所以"棕革短手套"看起来像裸手。新脚本把本体色与 `import_equipment.py` 建的 UE 材质取同一组线性值，渲染后按不透明区均值自校准曝光（读回时强制 `Non-Color` 再反解线性，避免色彩管理把修正方向搞反），实测成图平均 RGB 94,101,80／60,64,70／113,82,57／45,48,50 对应材质目标 95,103,80／60,65,72／118,82,53／45,48,52。原件备份在 `SourceAssets/ModularOutfit20260924/IconsBefore20260925/`。

`ue_original_gloves` 与棕革共用拾取网格与材质，因此继续共用同一张图。

V7 包装器复用 `author_bare_arms_family.py`、`save_bare_family_blends.py`、`import_bare_arms_family.py`。原生绑定输入来自 `BareArmsFamilyV6/Sources`；掌面上游仍用 `OriginalShapeBareM4` 的 V3／V6 对应数据。皮肤表面链保留 V4 烘焙、V5 材质及 `skin_surface_v5.hlsl`。这些旧版本是依赖，不因日期旧而退役。

`export_sleeve_fit_inputs.py` 为衣袖作者输入及布料状态读取入口；仅在需要重新提取源或用户要求相应状态检查时执行。Body 继续使用既有 NativeSkin 与 Profiles 装备，未随本轮第一人称重制。

## 历史工具与后台执行

`author_all.py`、`import_all_equipment.py`、`register_equipment.py` 和 `register_native_skin.py` 是初版装备链。尤其两个登记脚本会重建旧配方，不保留全部 V7 字段和 Fitted 资源；不能在现有配置上直接重跑。新增装备使用当前标准，精确更新本次物品与 profile，保留原生默认和其他装备。

获取脚本保留来源／许可，诊断脚本用于明确请求的排查。已完成的一次性“结束 PIE／热编译”文件归档，不作为常规入口。

后台 UE 导入使用 `Run-Authoring.ps1 -Script <脚本路径> -Log <专用日志>`，它使用已有批次互斥并拒绝与已运行的 FPSGAME 编辑器并行写资产；存在编辑器时使用现有 MCP 桥，不强制关闭进程。几何制作／Blend 保存需脚本对应的 Blender、NumPy／SciPy 环境；不要把 Unreal Python 脚本当普通 Python 执行。

仅有脚本不等于已经导入。资产成功保存后才接入配置；公开仓库不含 UE 包、网格或材质贴图。默认不启动游戏、不自动测试。
