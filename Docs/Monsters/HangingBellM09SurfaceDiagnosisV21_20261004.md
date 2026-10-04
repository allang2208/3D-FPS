# M09 主体表面缺失排查 V21

范围：用户要求排查主体看似缺失贴图及同类问题。本轮只读检查 M09 的制作源、正式网格材质槽、PBR 图节点及贴图资产；没有修改或保存 UE 资产，没有启动游戏。

## 确认的问题

正式网格 `/Game/Monsters/HangingBellM09/V04/SK_M09` 的以下槽为空：

| 槽索引（从 0 开始） | 槽名 | 正式材质引用 |
| --- | --- | --- |
| 4 | M09_Body_SourcePBR_001 | None |
| 5 | M09_Closure_SourcePBR_001 | None |

当前源模型 `M09_Body_RootBand` 使用 `M09_Body_SourcePBR.001`（420327 面）与 `M09_Closure_SourcePBR.001`（5093 面）。这两处覆盖主体源表面和主体封口，与正式空槽对应。

## 首个错误环节

`Tools/HangingBellM09/finish_arm_continuity_v16.py` 从 V15 库载入主体并复制网格。当前文件已有同名材质，载入后主体使用 Blender 自动追加的 `.001` 材质；V15 原主体使用无后缀名称。FBX 导入 UE 后后缀成为 `_001`。

`Tools/HangingBellM09/import_claw_continuity_v16.py` 只以完全相同的槽名恢复旧材质，而旧槽只有无后缀名；新主体的两个槽没有命中恢复映射。正式网格皮肤版本元数据仍为 V16。

## 同类范围及已排除项

- 正式 0–3 槽（原身体、封口、眼球、膜片）均绑定原 `M_M09_Body`；源模型中的眼冠、钩指、主眼、六片背膜和两侧小臂使用这些槽，未发现同类空引用。
- `T_M09_Base`、`T_M09_Normal`、`T_M09_ORM` 均能加载，尺寸均为 2048×2048；Base 使用 sRGB，Normal 和 ORM 为线性及相应压缩设置。
- `M_M09_Body` 的 BaseColor、Normal、Roughness、Metallic 及 Substrate 根连接存在，纹理节点指向上述资产；骨骼网格用途已启用。
- 当前主体源文件保留 `UVMap`，228764 个按五位小数去重的 UV 角点，数值有限；其他部件也保留 UV。此证据证明 UV 层没有整体丢失，不等于对每个三角形的拉伸做了视觉验收。
- NullRHI 下 get_used_textures 返回空数组；本结论依据实际表达式连接和可加载纹理引用，不把该结果误判为纹理丢失，也不声称进行了渲染/着色器视觉验收。
- 原生 CDO 网格组件没有材质覆盖；实际网格由角色 AlignVisual 设置，未修改该流程。

## 最小修复范围

将正式槽 4、5 补绑到现有 `M_M09_Body`；同时修正制作源的材质复用或导入映射，以免后续重导入再次生成空槽。本轮是排查，未执行此修复，模型、权重、骨架、动作均保持现状。

证据：`SourceAssets/HangingBellM09Meshy20261003/SurfaceDiagnosisV21/Records/blender_surface.json` 与 `ue_surface.json`。
诊断入口：`Tools/HangingBellM09/diagnose_surface_blender_v21.py`、`diagnose_surface_ue_v21.py`。
第二次 UE 只读诊断完整完成、errors 为空，commandlet 正常退出。第一次调用因 Python 未直接暴露 imported_material_slot_name 属性而中断，改用 get_editor_property 后重读；两轮都未写入资产。
