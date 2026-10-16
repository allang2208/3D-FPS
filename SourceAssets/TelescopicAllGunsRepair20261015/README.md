# 全枪型伸缩后托配对恢复 — 2026-10-15

用户确认 M16 修复合格后，授权继续修复其余 9 把枪，并延续上一轮逐枪检查范围。

## 完成内容

已替换并保存 M4A1、AKM、QBZ-191、HK416、A762、PKM、SVD、LMG201、M4 Super90 的 `tactical_telescopic`。M16 保持已认可的独立修复版，文件散列未变。

- 主体几何取自各枪 R1 平滑之前的真实装配版本，与最初 `TacticalStock_Game_Body.blend` 的原低模进行逐面匹配，恢复全精度 UV0 和原角点法线。
- 8 把主体面均可直接对应原低模。Super90 保留原前端裁切，其中 79,055 个三角形直接对应，312 个裁切三角形在对应原三角面内插值 UV/法线，没有新增封板或改变轮廓。
- 安装端、支杆、原厂保留件和其它非主体面从本轮修改前的实际资产导出完整复制，保留法线、UV、顶点色及材质分区。各枪其它 UV 通道继续沿用自己的装配/涂层数据。
- 共享 `T_TacticalStock_Normal_Game` 恢复为与原低模对应的原始 4K 法线。其文件内容与 M16 合格版本的法线源相同，强度为 1；Normalmap 压缩、关闭 sRGB、一次绿色通道转换。
- A762 的 3 个后托主体材质实例由中性 `DefaultNormal` 改为匹配结构法线；原有颜色、粗糙度、遮罩、细纹及湿润逻辑保留。
- 没有修改共享材质母图，9 把枪的运行材质槽名和材质资产路径均保持原样，因此现有 `current_surface_bindings.json` 不需要改变。网格重导入来源均指向本轮配对源 FBX。
- 各枪原运行网格路径保持原样，枪匠、持枪和展示继续读取同一资源。未改数值、动画、手部、其它后托或均衡后握把。

## 保存与检查结果

通过当前已运行 UE 编辑器的互斥桥完成导入、网格构建与保存，`install_receipt.json` 的 `complete=true`。为修改正在使用的资产结束了当时的 PIE；没有关闭、重启或主动新开编辑器，也没有重新启动游戏。

| 枪型 | 保存后主体 UV0 塌缩 | 导出异常角点法线 | 异常 R2 法线 |
|---|---:|---:|---|
| M4A1 | 0 | 0 | 已移除 |
| AKM | 0 | 0 | 已移除 |
| QBZ-191 | 0 | 0 | 已移除 |
| M16A2 | 0 | 0 | 保持已认可版 |
| HK416 | 0 | 0 | 已移除 |
| A762 | 0 | 0 | 原未接 R2，本轮接回正确结构法线 |
| PKM | 0 | 0 | 已移除 |
| SVD | 0 | 0 | 已移除 |
| LMG201 | 0 | 0 | 已移除 |
| M4 Super90 | 0 | 0 | 已移除 |

HK416、LMG201 另从 UE **SOURCE_MODEL** 直接读取确认：原各 5,625 个 UV0 塌缩面均归零，记录在 `ue_uv_confirmation.json`。

各枪非主体接口三角形数在保存前后均一致（M4 1536、AKM 2752、QBZ191 1912、HK416 2684、A762 2940、PKM 2940、SVD 7008、LMG201 2940、Super90 4073）。双向顶点匹配的最大位置差约 **0.000066 mm**，属于导出浮点误差，见 `interface_preservation.json`。

`capture.json` 的 9 个保存后网格散列与本轮安装回执全部一致；M16 散列与用户认可版本一致。有效结构法线输入均已指向正确源。

10 张 `Preview/` 图片来自**保存后 UE 网格导出**，使用有效主体法线与统一金属材质进行 Blender 诊断；菱形异常均不再出现。总览为 `Preview/all_stocks_repaired.png`。图片不是实际 UE 配色或枪体装配画面，未运行全枪游戏、多人、天气、动画或性能测试，实机效果仍由用户确认。

## 复现与恢复

- `Before/`：9 个原运行网格、原 R2 法线和 A762 三个原材质的精确备份。
- `Final/`：每枪可编辑 Blender、FBX 及正确法线源。
- `Working/`、`matches.json`：原低模逐面匹配、实测宿主变换、插值和原属性数据。
- `production.json`：作者网格、接口面数、UV 与局部法线记录。
- `install_receipt.json`、`install_bridge.json`：实际保存回执。
- `Exports/`、`capture.json`、`surface_audit.json`：保存后资产与逐枪检查结果。

制作入口：`extract.py` → `match_original.py` → `author_models.py` → `install.py`。

检查入口：`capture_after.py` → `render_after.py`、`check_interfaces.py`、`confirm_uv_after.py`。这些检查是本次用户明确授权范围，不作为其它任务的默认验收。

## 2026-10-16 整理记录

本目录已确认退役的备份、候选或一次性操作已移至本机 `trash/weapon-attachments-retired-20261016/SourceAssets/TelescopicAllGunsRepair20261015`。原文的 Before/旧候选路径属于历史记录；当前恢复依赖已保留。准确清单、替代物及本轮发布边界见 [整理发布说明](../../Docs/Publication/WeaponAttachments20261016/README.md)。
