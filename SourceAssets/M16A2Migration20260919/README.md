# M16A2：Godot 模型迁入 UE5

2026-09-19。本目录记录首阶段模型、材质和机械分件迁移。后续用户已授权完整枪械开发并选择三连发，正式接入见 [M16A2 玩法](../../Docs/Weapons/m16a2-gameplay-20260919.md)。

已通过 UE 5.8 后台导入脚本保存到 `/Game/Weapons/M16A2Migration`。

当前 F6 入口：`F6 → 基本调参 → 生成物品 → M16A2 → 生成`，复用原下拉与数量框，正式武器进入背包并可装备。首阶段的模型展示条目已被替换，没有独立物品页签。面板说明见 [F6 原物品下拉接入](../../Docs/UI/development-items-m16-plan-20260919.md)。

## 打开入口

- `SM_M16A2_Assembled`：已经装配好的整枪静态模型，可直接在内容浏览器打开或拖入关卡。
- `SK_M16A2_Mechanical`：纯枪机械骨骼模型；配套 `SK_M16A2_Mechanical_Skeleton`。
- `Parts/`：13 个独立静态零件，机械零件采用对应原始骨骼枢轴。将其作为独立组件组合时，位置使用本目录 `manifest.json` 的 `assembly_location_cm`，旋转为零、缩放为一。
- `Materials/M_M16A2_PBR`：共用可编辑材质，连接 BaseColor、Metallic、Roughness、Normal 和 AO。
- `Textures/`：五张源 4096 × 4096 贴图；BaseColor 为 sRGB，其余为线性数据。法线按源 Blender/OpenGL 约定在 UE 翻转绿色通道。

## 分件

| UE 名称后缀 | 内容 | 骨骼 |
| --- | --- | --- |
| Receiver | 机匣、提把机械瞄具和原固定枪管部分 | m16a2_base |
| Magazine | 弹匣 | magazine |
| Bolt | 枪机 | m16a2_bolt |
| Trigger | 扳机 | m16a2_trigger |
| BoltCatch | 枪机释放件 | m16a2_boltcatch |
| ChargingHandle | 拉机柄 | m16a2_chargehandle |
| ChargingHandleLatch | 拉机柄第二活动件 | m16a2_chargehandle2 |
| MagazineRelease | 弹匣释放钮 | m16a2_release |
| EjectionPortCover | 抛壳窗盖 | m16a2_ejection_port_cover |
| Stock | 原厂固定枪托 | M16FactoryStock |
| PistolGrip | 原厂后握把 | M16FactoryGrip |
| Handguard | 原厂护木 | M16FactoryForeend |
| Muzzle | 原厂枪口件 | M16FactoryMuzzle |

保留原拓扑与 UV，导出源合计 31,499 个三角形。枪身使用单一机械根，原有 8 个活动件保留单独刚性权重，枪托/握把/护木/枪口增加可单独驱动的骨骼。骨架共 18 根骨骼，含原有前准星、后照门、枪口和抛壳口标记。新增家具骨骼原点取自各自连接侧几何，仅为资产编辑原点，尚未制作枪匠安装参数。

单位统一为厘米，枪口朝 +X，向上 +Z；模型原点为原枪身骨骼原点。转换同时作用于所有网格、骨骼与标记；FBX 导入关闭场景轴转换，仅进行左右手坐标转换。独立零件的装配位置以 `manifest.json` 为准。

## 作者文件与重建

- `M16A2_Mechanical_Editable.blend`：纯枪可编辑源，13 个独立网格、机械骨架及打包贴图。
- `Source/M16A2_Godot_Modular.blend`：旧模块化源的本机保留副本。
- `Source/M16 A2 Rifle - Animated.fbx`：旧项目下载的原始源包 FBX，作为追溯材料保留；其中手臂与动画不导入本次 UE 资源。
- `Source/legacy_m16_attachment_mounts.gd`：旧 Godot 原厂分件名称和挂点代码参考。
- `Export/`：整枪骨骼 FBX、整枪静态 FBX及各零件 FBX。
- `../../../Tools/AssetPipeline/export_m16a2_migration.py`：Blender 后台导出入口。
- `../../../Tools/AssetPipeline/import_m16a2_migration.py`：UE Python 后台导入入口，仅写入上述独立 Content 目录。
- `manifest.json`：模型分件、装配位置和骨骼清单。
- `import_result.json`：本次导入脚本保存的实际资源路径。

旧源位置为 `E:/3d/m16-staging/m16-modular-editable.blend`，原贴图来自同目录 `source/textures/m16a2_*.png`。旧 `m16_attachment_mounts.gd` 的 FACTORY 映射对应本次保留的原厂分件。另读取过裸手正式版本的 `m16.blend`，其枪械分件命名一致；本次不涉及手模，采用保留原多边形与 UV 的模块化作者文件。

## 首阶段交付记录

首阶段未修改角色、武器目录、背包、枪匠、存档、音效或其他武器，也未迁移手臂与动作。后续玩法资产独立保存在 `SourceAssets/M16Gameplay20260919` 与 `/Game/Weapons/M16A2/Gameplay20260919`，本目录继续保留纯枪机械源。

只完成必要导出与导入。没有渲染、截图、PIE、自动测试或视觉验收，由用户自行测试。

`import.log` 记录全部资产保存及 `M16A2_IMPORT_COMPLETE`。该 commandlet 的汇总同时记录 MCP HTTP 监听器无法绑定 `127.0.0.1:8000`，因此进程汇总为 1 个错误；它出现在 MCP 服务启动阶段，Python 资产导入脚本随后执行至完成。此处不将进程退出状态描述成验证通过。

来源与署名见 [ATTRIBUTION.md](ATTRIBUTION.md)。
