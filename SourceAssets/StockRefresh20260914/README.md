# 枪托图标与战术伸缩枪托 — 2026-09-14

本轮按用户要求查看现有模型、确认前后方向，并用实际模型重新渲染枪托图标。游戏内测试由用户进行。

## 当前交付

- 五款选项图标：原厂枪托、骨架枪托、高性能后托、镂空轻型枪托、战术伸缩枪托。
- 统一安装端朝左、托底朝右，上部枪托轴线水平，正交侧视；1024 × 1024 RGBA 透明 PNG。
- 图标取自当前 M4 代表模型，与现有跨枪型共用配件图标方式一致；源文件路径记录在 `Icons/stock_*.json`。
- 游戏加载目录：`Content/ColdSteelData/AttachmentIcons20260913`。五张 PNG 均为最终渲染，同名 UE Texture 已同步；战术图标最后的细小法线修整版本已于 2026-09-14 11:52 导入并保存。
- 本轮没有更换现有骨架枪托、高性能后托或镂空轻型枪托的模型。

## 配件属性

以下属性同时写入 M4、AKM、QBZ191 的 `Content/ColdSteelData/gunsmith.json` 配件表。

| 配件 | ADS 瞄准时间 | 后坐力 | 枪械稳定性 | 腰射随机散布 |
| --- | --- | --- | --- | --- |
| 骨架枪托 `skeleton` | -20% | +15% | +10% | 无修改 |
| 高性能后托 `qr_performance` | 无修改 | -20% | +15% | -30% |
| 战术伸缩枪托 `tactical_telescopic` | -5% | -15% | +15% | +25% |

ADS 使用现有 `ads_percent` 时间加法字段；其余使用 `recoil_mult`、`stability_mult`、`hip_spread_mult`。用户原文“散步”在面板中写为“散布”。镂空轻型枪托保留先前后坐力控制 +10%、枪械稳定性 +5%、无 ADS 减益的设置。

## 战术伸缩枪托

用户指定源文件：`D:/FPS3D/资产/Meshy_AI_Adjustable_Rifle_Stoc_0914030720_generate.fbx`。原件复制于 `TacticalTelescopic/Source/`，可编辑导入场景为 `TacticalTelescopic/Imported_Source.blend`。

源文件有 3,048,660 个三角面，无 UV、材质或贴图。本轮保留造型，制作约 80,000 面的游戏主体、UV0 和 4096 × 4096 PBR 图集，法线从指定高模烘焙。新制作的表面分为金属机构、聚合物贴腮壳体和橡胶托底；金属通过 UV1 使用各枪的现有机匣涂层。M4 的 UE 材质沿用现有 Phong 转换函数，Blender 工作场景使用同一颜色纹理及代表性粗糙度。

主体按 23 cm 长制作，前套管中心由原模型前端切片确定。保留既有各枪的 WPN_root 安装合同，新增短渐变套环衔接原模型较窄的椭圆套管；AKM 与 QBZ191 带各自机匣接口。

| 枪型 | 导出三角面 | UE 目录 |
| --- | ---: | --- |
| M4 | 81,536 | `/Game/Weapons/TacticalTelescopicStock20260914/M4` |
| AKM | 82,752 | `/Game/Weapons/TacticalTelescopicStock20260914/AKM` |
| QBZ191 | 81,912 | `/Game/Weapons/TacticalTelescopicStock20260914/QBZ191` |

每个目录中的 `SM_TacticalTelescopicStock` 已接入枪托切换。源码为 `Source/FPSGAME/Weapons/SkeletonStockVisual.cpp` 和 `QBZ191Attachments.h`，打包目录已加入 `Config/DefaultGame.ini`。

五个细长三角面的平均角点法线曾产生零切线，已将这些面的法线独立并重新烘焙，其余面保持原有平滑方式。UE 保留这些法线并在最终网格上重新生成切线，最终导入不再出现近零切线提示。生产导入记录见 `TacticalTelescopic/import_results.json` 和 `TacticalTelescopic/import_assets_console.log`。

## 文件与完成边界

- 图标实际模型场景：`Icons/stock_*.blend`。
- 五款总览：`stock_lineup.png` / `stock_lineup.blend`。
- 新枪托可编辑高低模与烘焙场景：`TacticalTelescopic/`。
- 各枪可编辑模型与 FBX：`TacticalTelescopic/M4`、`AKM`、`QBZ191`。
- 原数据、源码、图标与贴图资源的范围备份：`Before/`。
- 必要原生编译通过：`Saved/BuildEditor/build-20260914-113600.log`；本轮构建记录为 `build_editor_retry.log`。首次构建遇到并行新增怪物源文件的链接错误，后续完整构建已纳入该源文件。
- 已执行用户要求的模型与图标方向查看。没有启动游戏、PIE 或运行玩法回归；不将导入和构建结果表述为游戏内验证。

图标 Texture 曾在重复导入时被打开的编辑器占用。用户关闭编辑器后，已单独重新导入并保存 `stock_tactical_telescopic` 的最终版本；2026-09-14 11:52 的导入任务正常结束，0 错误、0 警告，记录见 `import_tactical_icon_console.log`。镂空轻型枪托图标后续未再改动，之前成功导入的 Texture 已是最终内容。改造面板通过 `FImageUtils::ImportFileAsTexture2D` 直接加载 PNG；五张 PNG 与对应 Texture 的交付现均完成。此次仅同步图标资源，没有重新编译或运行游戏测试。
