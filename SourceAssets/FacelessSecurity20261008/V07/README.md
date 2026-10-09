# 无面安保 V07：移除裤子内部的悬空碎片

2026-10-09 整理补注：本文记录对应版本历史；当前组合、保留依赖及已移入 trash 的旧导出/备份路径见 [无面职员发布与恢复](../../../Docs/Publication/FacelessStaff20261009/README.md)。不要批量运行旧导入脚本覆盖当前入口。

2026-10-08。用户指出 V06 腰侧仍有黑色小物体。前两轮把问题归到腰带附件，未找准这两块几何的实际归属。

当前已由 [V08](../V08/README.md) 接续处理用户报告的上臂／腋下尖刺；V08 保留本版裤子残片的清理结果，继续使用 V06 动作。

## 直接来源

制作源的 `Security_Trousers_Continuous` 含三个互不连接的网格部分：裤子主体 28362 顶点，以及左右两块分别为 96／86 顶点、188／168 三角面的独立残片。两块都使用黑色 `Security_Trousers` 材质，100% 绑定骨盆，尺寸约 1.4 × 2.6 × 2.5 cm。

在用户报告所涉及的待机／攻击源姿势中，两块碎片与衣物主体间距约 9–11 cm，所以会始终跟随腰部；删除腰包、袢带或袖扣无法移除它们。定位数据见 `fragment_source.json`，当前 UE 引用读取记录见 `active_before.json`。

## 本次修改

直接从裤子网格中删除这两个已定位的独立部分，共 182 顶点、356 三角面。保留其余裤子顶点坐标、UV、分裂法线和蒙皮权重；肩袖、其他衣物、身体与 V06 三段动作不变。

- `Authoring/FacelessSecurity_V07.blend`：清理后的独立作者对象。
- `Delivery/`：清理后的穿衣、独立衣物 FBX／GLB，以及完整身体副本。
- 穿衣组合由 192586 降为 192230 三角面，仍为 161 骨、7 材质槽、59 个衣物对象。
- UE 目标为 `SK_FacelessSecurity_V07` 与 `SK_FacelessSecurity_Clothing_V07`，接入原 `/Game/Monsters/FacelessSecurity/BP_FacelessSecurity`。完整身体和动画继续引用 V06。
- 删除记录：`fragment_removal.json`；导出记录：`export_receipt.json`；导入记录：`ue_delivery.json`。

两个 V07 网格与原蓝图已在现有编辑器内通过互斥桥实际导入、保存，`ue_delivery.json` 为 `stage: saved`，桥返回 `success=True`。导入前读取到正式蓝图使用 V06 网格，只有一个身体网格组件；导入时没有正在运行的 PIE。实际保存记录见 `Logs/import_bridge_01.txt`。

仅做本次缺陷定位所需的数据读取与网格修正，没有新增游戏测试、预览渲染或 C++ 修改。实际游戏表现交由用户测试。
