# 从原树截取树桩

后续实现已由 [树桩断面与切口倾倒修复](TreeCutHingeFix-20260913.md) 更新：使用匹配的上下段、显式断面 UV 和真实切口前缘支点。本页保留上一版制作记录。

按用户要求，采集后的树桩改为当前四种 `SK_BlackPoplarPCG_A/B/C/D` 各自的原树下段。保留原始根部形状、树皮 UV、材质、局部原点，以及生成时的位置、朝向和缩放；在原树局部 Z=42 cm 处截断并封上年轮断面。

倒下树干底部使用同一次切割得到的对应断面，因此不再统一套用直径 36 cm 的圆片。三款可拾取粗原木继续沿用上一版，不受此次树桩调整影响。

截取在制作阶段完成，运行时显示静态网格实例。四种树桩合计最多显示附近 64 米内最近 64 个，继续从已采集资源记录重建，无需新增存档字段。树桩仍是无碰撞装饰。

## 源资产处理

这些原树使用 Nanite 组合数据。普通骨骼 FBX 导出的 imported fallback 在根部不完整，因此作者脚本通过 Geometry Script 的 `SOURCE_MODEL` 读取编辑器源几何，再导出给 Blender 截断、沿真实边界封面并保留 UV。中间静态资产只用于导出，不保存或加入运行时引用。

| 原树 | 树桩三角形 | 对应断面三角形 |
|---|---:|---:|
| A | 6112 | 388 |
| B | 7294 | 388 |
| C | 11691 | 560 |
| D | 10318 | 378 |

引擎资源：`/Game/Items/HarvestTimber/SM_OriginalStump_A` 至 `_D`、`SM_OriginalCut_A` 至 `_D`。

作者脚本位于 `SourceAssets/HarvestTimber20260913/original_stumps_export.py`、`original_stumps_cut.py`、`original_stumps_import.py`。可编辑文件为 `SourceAssets/HarvestTimber20260913/OriginalStumps/OriginalTreeStumps.blend`；FBX、源引用及导入记录保留在同目录。原树及其衍生二进制资源继续遵守现有资产许可和本地保留规则，不公开再分发。

Editor 原生代码构建完成，八个树桩/断面网格已导入保存。按用户规则没有运行 PIE、视觉验收或性能测试；需要重启 UE 后由用户试玩。构建记录 `Saved/Logs/OriginalStumps-Build.log`，导入记录 `Saved/Logs/OriginalStumps-Import.log`。导入脚本成功与整个 commandlet 的退出码分别记录；项目已有 GameFeatureData 配置和 MCP 端口占用日志不作为本功能验收结果。
