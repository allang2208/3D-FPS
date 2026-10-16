# M16 直接复用用户认可的 M4 伸缩后托 — 2026-10-15

用户反馈 R2 版本的 M16 后托仍有明显坑洼，并明确选择 **M4** 作为合格母版。本轮直接移植 M4 现用的完整伸缩后托，不再对 M16 的旧主体做平滑、局部 UV 修补或额外重烘。

**后续状态**：用户随后也否决了这次 M4 移植在 M16 上的实际表现，并要求重新建模。本页为失败方案历史；新硬表面建模入口为 `../TelescopicHardSurface20261015/README.md`。

## 复用内容

- 来源：`/Game/Weapons/TacticalTelescopicStock20260914/M4/SM_TacticalTelescopicStock`。
- 完整保留来源的 81,536 个三角形、所有 UV 层、角点法线、切线、颜色及实际材质。
- 包括来源的金属、聚合物、橡胶和前套筒材质；M16 主体不再使用自己的旧材质加工分支。
- 从原 M16 网格保留 `M16_InterfaceMetal` 的 1,268 个闭合安装接口三角形及原材质。
- 只按既有装配合同做刚体变换：厘米空间 `yaw=-90°`、平移 `(-0.0038, -4.1045, 9.17)`，缩放保持 1。没有重算、减弱或重烘 M4 的表面信息。
- 目标仍为原运行路径 `/Game/Weapons/M16A2/UniversalAttachments20260920/Meshes/SM_M16_tactical_telescopic`，由现有枪匠、展示和角色装配入口读取。
- `current_surface_bindings.json` 只更新此后托的材质映射，保留 M4 的完整配方；网格重导入源指向本轮导出的 FBX。

## 交付

- `Before/`：替换前 M16 网格及该枪材质映射备份。
- `Final/SM_M16_tactical_telescopic.fbx`、`Final/M16_M4Stock_Editable.blend`：移植后的可编辑几何源。
- `install_m4.py`：通过当前 UE 资产数据直接复制与装配，不经 Blender 重建网格。
- `install_receipt.json`：实际保存结果、来源与目标散列、精确材质路径；`complete=true` 表示落盘及引用更新完成。

本轮仅制作、必要资产构建和保存。没有主动启动 UE 编辑器、游戏、截图、渲染或测试。M4 的合格判断来自用户本轮确认；移植后的 M16 实际观感由用户查看。

实际落盘：后台 commandlet 退出码 0，目标网格、重导入来源与材质映射已保存，回执 `complete=true`；最终 FBX 和 Blender 几何源已生成。

## 2026-10-16 整理记录

本目录已确认退役的备份、候选或一次性操作已移至本机 `trash/weapon-attachments-retired-20261016/SourceAssets/M16StockDonor20261015`。原文的 Before/旧候选路径属于历史记录；当前恢复依赖已保留。准确清单、替代物及本轮发布边界见 [整理发布说明](../../Docs/Publication/WeaponAttachments20261016/README.md)。
