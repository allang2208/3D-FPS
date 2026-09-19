# 冷钢仪式箱 — V8

2026-09-09 开始，2026-09-10 完成。用户选择“冷钢仪式箱”方案后，已直接接入 UE 项目。

## 设计和实现

- 移除圆管卷草、44 片花瓣式放射装饰、4 颗正面小宝石及盖箍上的 48 片金色叶饰。
- 保留正面主宝石及左右侧面宝石，共 3 颗；尺寸为原来的 72%，降低突出厚度。
- 三块薄钢徽章各有 24 道实际几何凹刻的放射线，共 72 道。刻槽深度约 2.66 mm；底盘与大理石有约 0.7 mm 嵌入，镶圈底部接入徽章表面。
- 宝石使用薄香槟金镶圈和窄外沿，正面两侧换为贴面的细阶梯纹，留出大面积大理石。
- 保留箱体结构、盖体、锁扣、铰链及原有动画层级。新 GLB 刚性骨骼转换仍有 5 个关节。

## 材质

全部新材质位于 `/Game/ColdSteelUI/Warehouse20260909/RitualV8/Surfaces/`，旧材质未覆盖。

- Frame：枪灰钢，线性基色 (0.11, 0.13, 0.16)，粗糙度基准 0.38。
- Strap：稍浅钢色，粗糙度基准 0.34。
- Hardware：较亮的接触五金，粗糙度基准 0.27。
- Champagne：少量旧香槟金，线性基色 (0.34, 0.29, 0.20)，粗糙度基准 0.31。
- Engraving：深色凹槽，粗糙度基准 0.55。
- Sapphire：线性基色 (0.004, 0.015, 0.055)，粗糙度 0.14，保留真实几何切面；未宣称具有真实体积折射。
- 所有金属继续使用用户已下载的 Dirty Metal：R 污痕遮罩局部影响反射与颜色，G 粗糙度用于小幅变化；细方向纹仅微调粗糙度。
- 大理石仍为此前接入的 Ziarat White Marble 4K，内衬材质引用不变。
- 所有新材质支持骨骼网格，实例显式开启双面覆盖。

## 验证

- `validate_apply.py` 检查新旧 GLB 的动画目标、时间数组和通道值逐字节一致，Open 0.9 s / Close 0.7 s。
- 11 个实际材质槽均有配置引用，相关 uasset 全部存在；`inspect_assets.py` 在新 UE 进程中读回真实槽名、材质父级和实例颜色/粗糙度参数。
- 两次 1920×1080 独立游戏预览均退出 0 并输出 `WarehousePreview: COMPLETE`。第二次以 FOV 55、禁用纹理流送、独立预览进程时间倍率 0.15 延长预热，获得最终近景。
- 首次关闭截图在新材质完整显示前拍摄，颜色暂未就绪；随后开启截图和最终预热后的闭合/开启截图均确认颜色与材质显示正确。没有为此更改游戏材质参数或玩家持久设置。
- 最终近景：`After/detail-closed.png`、`After/detail-open.png`。普通视角开启图为 `After/chest-open.png`；`After/chest-closed.png` 保留了首次提前拍摄的证据，不应作为最终效果图。
- UE commandlet 导入和检查输出 PASS，但总退出码为 1，来自项目已有 GameFeatureData 资产管理规则错误。Blender 有缩略图写入路径警告；可编辑源和 GLB 实际保存成功并通过 UE 导入与运行渲染。
- 没有更改 C++、冷钢 UI、库存逻辑、存档或玩家交互距离。未进行打包构建或性能基准测试。

## 可编辑源与回退

- `warehouse_chest_ritual_v8.blend`：独立可编辑源，内嵌源贴图，Blender 颜色供形状编辑参考；最终反光以 UE 为准。
- `warehouse_chest_ritual_v8.glb`：保留源节点动画的导出文件。
- `warehouse_chest_rigid.glb`：UE 导入中间资源，75,601 个导出顶点。
- 新 UE 目录位于原有 always-cook 范围 `Warehouse20260909/RitualV8` 内。
- 正式入口：`D:/FPS3D/FPSGAME/Content/ColdSteelData/warehouse_assets.json`。
- `Before/warehouse_assets.json` 保留 V7 外观引用。回退时只恢复本次修改的 mesh/open/close 与相关材质项，避免覆盖后续并行修改。
- Godot 源工程、V7 模型和此前的 Fab 材质资产均保留。
- 重新开始当前游戏运行后，新宝箱实例会读取 V8 配置。
