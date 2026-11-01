# 已保存静态网格的切线与回退模型

适用近景复杂硬表面附件导入后法线贴图失真、切线轴为零，或 Nanite 与回退网格细节不一致。2026-11-01 两款锤座案例，不作为所有模型强制启用完整回退的标准。

- 源 FBX 有法线/UV、导入成功和编辑器保存成功分别是不同证据。用户要求检查时，读取实际保存并构建后的网格缓冲，核对切线 X/Y/Z 非零、方向正交和材质槽；不要只看源文件。
- 先定位 UV 退化面；保留已认可几何、顶点法线与接口，局部修复 UV。不要把所有顶点平滑、细分或加面当成法线问题的修复。
- 修复切线以原始 MeshDescription 为源。不要从已被 Nanite 简化的 Render LOD 重建源几何，否则会把批准的细节永久换成低精度形体。本例先计算 Mikk 切线，再将切线投影到原法线的正交平面，仅对退化角点回退；保留原角点法线、UV 和分组。
- UE 5.8 本例仅设置 fallback_percent_triangles=1、fallback_relative_error=0，仍处于 Auto 目标，实际产生低精度回退。改为明确的 PERCENT_TRIANGLES 目标后才得到预期完整回退；重新读取已保存资产确认设置，而不是仅修改 Python 局部对象。
- 完整回退、高精度切线和 UV 会增加资源成本。它们在本例用于保真修复，不代表已完成游戏低模优化或性能验收。之后减面另保留可编辑高模，按用途和近景剪影制定 LOD。
- 导入器同步修复参数与原生修复入口，确保再次制作不会重新引入问题；保留回退前包及逐文件散列。当前实例使用 GuanLei V12_UV2 和 JiLei V14，不能把失败导出重新接回目录。

工程实现：`UWarhammerModificationAuditCommandlet::RepairSeatTangentBasis`；恢复脚本：`SourceAssets/ThunderGodHammer20261028/FullNetworkReview20261101/repair_seat_tangents.py`。该入口只处理具名锤座，不能无范围限制地应用到所有资产。
