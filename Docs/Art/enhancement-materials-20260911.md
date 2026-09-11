# 强化石与魔法粉尘写实模型及 UE 接入

2026-09-11。两款三视图、模型修整、轻量模型和法线烘焙已经完成，并已接入 UE 同名物品的地面模型。强化石使用 5080 高档母版处理版本，粉尘使用按参考人工分件重建版本。粉尘 1024 恢复后已推进到 HR 采样；用户确认当前精度可用并要求暂停，已提交定向取消。此高档对比未完成，不再作为本轮待办。

保持既有 `enhancement` 强化材料分类、99999 最大堆叠与仓库一次性补足逻辑。测试使用单独 `ColdSteelProfile`，没有重置玩家材料或正常存档。

## 实测对比

相同物品使用相同seed和三视角参考。512为12/16/12步；1024_cascade为16/32/24步。两者都导出2K贴图、目标10万面。并非最高100步或4K测试。

| 项目 | 512 | 1024级联 |
| --- | ---: | ---: |
| 强化石执行时间 | 102.29秒 | 726.05秒 |
| 强化石原始三角面 | 2443554 | 9075790 |
| 强化石带贴图母版三角面 | 98804 | 99756 |
| 粉尘执行时间 | 324.13秒 | 未确认 |
| 粉尘原始三角面 | 11155582 | 未确认 |

强化石高档的断面起伏更细，耗时约7.1倍。原始面数不是最终验收标准：直接从908万面烘焙产生黑斑，已改用整理后的99756面表面烘焙低模，失败实验保留但不交付使用。

粉尘512原始模型将玻璃和粉末合为偏黑外壳，另按三视图人工重建厚壁玻璃、金属盖、粉末和晶粒。不能把这份人工重建宣称为5080直接生成。

## 推荐交付

目录：[Delivery](../../SourceAssets/EnhancementMaterials5080_20260911/Delivery/README.md)。

- 强化石：20000三角面，14cm，颜色/金属粗糙度/法线贴图。
- 魔法粉尘：12070三角面，16cm，透明玻璃与粉末分件，瓶盖/粉末颜色、粗糙度及法线均已烘焙。
- 两款GLB均内嵌贴图、底部中心原点；对应Blender源可编辑。
- 36帧旋转预览由交付GLB真实渲染，视频4.5秒，非生成图冒充模型。

![候选模型](../../SourceAssets/EnhancementMaterials5080_20260911/Delivery/preview.png)

[实测对比图](../../SourceAssets/EnhancementMaterials5080_20260911/Delivery/quality_comparison.png) · [旋转预览](../../SourceAssets/EnhancementMaterials5080_20260911/Delivery/turntable.mp4)

## UE 接入与验证

- 资源：`/Game/Items/EnhancementMaterials/enhancement_stone/SM_enhancement_stone` 与 `magic_dust/SM_magic_dust`；各 1/4 个材质槽。打包目录已加入 AlwaysCook。
- 运行映射：`Source/FPSGAME/UI/ColdSteelPickupConsumable.cpp`。使用导入包围盒作碰撞根，14/16 cm 高度，继承现有 CCD、重力、摩擦和拾取事务。
- `SourceAssets/EnhancementMaterials5080_20260911/export_ue.py` 导出 FBX 与全通道贴图，保留金属度乘数。`Tools/AssetPipeline/import_enhancement_materials.py` 连接颜色、粗糙度、金属度和法线；非颜色图关闭 sRGB，glTF 法线翻转绿色通道后按 UE 法线压缩。
- 材质重建先复制 `get_material_expressions()` 列表，再逐个删除并断言为空。本机 UE 5.8 的 `DeleteAllMaterialExpressions` 遍历期间修改原集合，会留下节点；重复 Thin Translucent 输出曾导致实际运行编译回退，导入成功标记不能替代运行检查。
- 玻璃使用 Thin Translucent 和 Surface Per Pixel Lighting。UE 5.8 Substrate 的 legacy 转换通过 `lerp(TransmittanceColor, 0, Opacity)` 计算透射；Opacity=1 会堵住透光，故透明瓶体设置为 0，并以透射色控制玻璃。实时薄层近似不等于 Blender 厚玻璃折射/焦散。
- 本轮原生编译成功，模块后缀 `2026091195`；导入脚本输出 `ENHANCEMENT_MATERIAL_IMPORT_PASS`。命令行还包含既有 GameFeatureData 配置和已占用 HTTP 端口告警，不能把其非零进程返回码混同资产脚本失败。
- 独立运行入口 `-EnhancementMaterialPickupAudit -ColdSteelProfile=EnhancementMaterialPickupAudit_20260911e`，地图 `/Game/GameMaps/DayNight_Lighting`。
- 首轮 23/0；增加目标存在性检查后为 27 项。中间一轮玻璃节点残留触发编译回退，固定两秒落地判定也受冷启动卡顿影响，出现 4 项失败；已修复表达式清理并等待实际落稳后再检验。最终 e 轮 **27 项通过、0 失败，未出现材质编译回退**；覆盖最大堆叠、丢弃、导入模型、重力下落、实体地面落稳、99999 数量、保存/重载位置与旋转、瞄准拾取及世界 Actor 消失。
- `Saved/EnhancementMaterialsRuntime.log`、`Saved/EnhancementMaterialsInGame.png` 保存实际丢弃证据；`Saved/EnhancementMaterialsUprightInGame.png` 是同一游戏场景内的正立材质对照摆放，不作为重力落地证据。

粉尘 1024 恢复状态与回执见[恢复记录](../../SourceAssets/EnhancementMaterials5080_20260911/RECOVERY.md)。未把重新提交计作完成，最终对比须下载校验并实际渲染。

![UE 内正立材质对照](../../Saved/EnhancementMaterialsUprightInGame.png)

回归：`ConsumablePickupAudit_20260911regression` 在同一新模块下 39 项通过、0 失败，保留原有两款药水和两种弹药盒的掉落/存档/拾取。日志 `Saved/ConsumablesRegression20260911.log`。


### 恢复任务的进度核对

恢复任务的阶段日志仍停在 decoder 加载时，使用外部只读 py-spy 采样发现已进入 `sample_shape_slat_cascade_multiview` 的 HR Euler 采样。连续采样从 `t=0.9454545` 进入 `0.9345794`，对应 32 步重映射时间表的第 7→8 步；不能以日志停留或 GPU 满载单独推断死锁/完成。诊断工具来源、校验和堆栈保留于 `Saved/EnhancementMaterialTools`，未注入运行进程或重启服务。

用户已接受当前精度并要求暂停。已向恢复任务发送带 prompt_id 的定向 interrupt，HTTP 200；检查时当前节点仍为 in_progress，未把请求接受记作任务已退出。共享队列其他任务保持不动，本地监测脚本已停止。此次粉尘高档对比不再继续，不记作成功或显存失败；最终采用已验收的分件模型。记录 `recovery_pause.json`。
