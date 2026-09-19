# 宝箱蓝宝石装饰几何优化 — 2026-09-09

本次只修改 UE 宝箱的几何引用和对应动画资源引用。现有 Ziarat White Marble、Dirty Metal、蓝宝石及内衬材质映射保持一致。

## 已完成

- 重建正面 16 片、两侧各 14 片放射纹，共 44 片。原件是 8 顶点的独立硬棱块；现为圆滑、封闭的浅浮雕，根部进入镶圈底座。
- 重建 7 个镶圈，用 96 段周向采样和圆边剖面代替原来的 16 段直棱圈。保留 7 颗宝石原有切面形状，调整深度，使宝石亭部落在镶圈中。
- 正面卷草的 18 个连通部分先焊接对应端盖，再局部细分平滑。深度压缩到原来的 60%，移至箱面附近，避免原先粗硬管状花纹悬空。
- 保留箱体、盖体、铰链、锁扣、背面装饰的原有几何，以及三组网格的动画层级。

## 贴合与动画验证

- 正面大理石平面为源坐标 Y=-71；侧面为 X=±98。镶圈底部和放射纹背面进入板面约 0.1 源单位，即 0.7 mm，避免浮空和共面闪烁。
- 放射纹根部与镶圈最小径向重叠约 5.6 mm。没有把原有分离棱块简单放大来掩盖空隙。
- `check_and_apply.py` 对新旧 GLB 的动画目标、时间数组和通道值做逐字节对照，通过。保留 5 个刚性骨骼，Open 0.9 s / Close 0.7 s。
- UE 1920×1080 独立运行预览退出码 0，`WarehousePreview: COMPLETE`。检查关闭盖面、打开内衬、正面及侧面镶圈和装饰。最终截图位于 `After/`。
- 源箱身顶点从 9,628 增至 51,496；导出后的整箱渲染顶点从 42,893 增至 79,419。新增细分集中在装饰部件；没有据此宣称性能提升。
- 导入脚本输出 `CHEST_ORNAMENTS_IMPORT_PASS`，但 commandlet 总退出码为 1，来自项目已有的 GameFeatureData 资产管理规则错误。Blender 保存时存在缩略图路径错误，`.blend` 和 GLB 已正常保存；GLB 随后成功导入 UE 并完成运行渲染。

## 文件和回退

- 可编辑源：`warehouse_chest_v7.blend`，内嵌源模型贴图。UE 使用项目已有 Fab 材质覆盖。
- 中间资产：`warehouse_chest_v7.glb`、`warehouse_chest_rigid.glb`。
- UE 资产：`/Game/ColdSteelUI/Warehouse20260909/OrnamentsV7/`，位于现有 always-cook 目录。
- 实际引用：`D:/FPS3D/FPSGAME/Content/ColdSteelData/warehouse_assets.json` 的 mesh/open/close。
- `Before/warehouse_assets.json` 与 `Before/chest-*.png` 保留上版引用和外观。回退只恢复 mesh/open/close 三项，保留其他任务可能更新的材质映射。
- 来源为 `E:/3d/3-dfps/tools/chest-sapphire-20260908/warehouse_chest_v6.blend`；Godot 原工程源文件未覆盖。
- 重新开始当前游戏运行后，宝箱实例读取新模型。
