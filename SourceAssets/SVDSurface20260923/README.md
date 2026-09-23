# SVD 分区表面材质（2026-09-23）

## 2026-09-23 整理后的当前入口

旧换弹导出已由 `SVDThumbUp20260923` 替代；当前模型与材质入口为 `SVDRefinedFinish20260923`。本目录的旧制作记录保留其历史日期与验收边界。已经移走的旧导出、自动备份及恢复快照位于 `trash/svd-superseded-20260923/SourceAssets/` 下的同名目录，原路径、散列及保留替代物见 [归档清单](../../Docs/AssetArchives/svd-superseded-20260923.json)。当前所需 Blend、脚本、参数与原素材仍保留；不要直接重跑旧导入覆盖用户已认可的抓握。新 checkout 的恢复方式见 [SVD 发布说明](../../Docs/Weapons/svd-publication-20260923.md)。

后续修订：当前运行表面已更新为 [SVDMatteDetail20260923](../SVDMatteDetail20260923/README.md) 的独立哑光干湿材质，弹匣使用专用 4K 图集。本目录是其保留结构法线与分区贴图的来源，下面为本轮历史制作记录；后续不要仅重跑旧导入器覆盖当前绑定。

按用户要求参考 QBZ191 Hero 与武器 Skill 的结构／表面分离方法，制作并接入 SVD 专用材质。完成四张 4096² 贴图、两个母材质与七个既有材质实例的后台导入保存。没有启动交互编辑器、游戏或视觉验收。

## 表面制作

旧材质将源 AO 直接乘进 BaseColor，并直接沿用整张源粗糙度。新材质把 AO 独立接到环境遮蔽输入，按真实零件区分颜色、粗糙度和金属度，保留原结构法线的完整强度及当前修正后的 UV0。

| 区域 | 本轮制作 |
| --- | --- |
| 机匣、枪管、保险杆 | 深色处理钢材；减少旧色图的大面积斑驳贡献，保留局部标记 |
| 弹匣 | 与枪钢同一色系，独立反射参数；保留筋槽结构法线 |
| 拉机柄、扳机 | 稍亮的加工钢材，粗糙度低于机匣 |
| 枪托、护木 | 深色聚合物、金属度 0；按实际几何分区，未套用源 metallic 的错误家具金属区域 |
| 托底、贴腮垫 | 消光橡胶和棕色软垫独立制作 |
| PSO-1 镜筒、镜座 | 深灰涂层与较暗安装座分别制作，保留白色刻字、黑色橡胶／内壁区域 |

微纹只做小幅粗糙度变化，没有叠加强烈颗粒凹凸。正常钢件粗糙度中心约 0.235–0.31，聚合物 0.50、橡胶 0.72；这些是本次制作参数，不是所有枪械的通用标准。详细参数与面分区见 `authoring.json`。

本轮没有重新制作几何倒角或结构法线；区别于 QBZ191 Hero 的高低模重烘焙。原法线仍可能保留源文件自身的细节和压缩局限，转换为 PNG 不等于恢复丢失信息。

## 已保存资产

- `Textures/`：枪体与 PSO 各一张 BaseColor、一张 ORM，共四张 4096² PNG。ORM 为 R=AO、G=Roughness、B=Metallic。
- `SVD_Surface_Editable.blend`：完整模型、手臂、现有动作、新工作材质，以及默认隐藏的 `SVD_SURFACE_AUTHOR` 制作对象和程序材质。
- `../SVDCompletion20260923/SVD_Complete_Editable.blend`：同步新工作材质的正式可编辑源，保留原部件／材质名与动作。
- UE 新资源：`/Game/Weapons/SVDDragunov20260922/Surface20260923/{Textures,Materials}`。BaseColor 为 sRGB BC7，ORM 为线性 BC7；原 Normal 保留专用压缩及既有单次绿色通道转换。
- 七个既有 `MI_SVD_{Body,Magazine,Trigger,ChargingHandle,SafetyLever,ScopeBody,ScopeMount}` 已保存新母材质与纹理参数；网格继续使用原实例路径，无需改变模型槽或原生代码。
- 正式骨骼网格 `/Game/Weapons/SVDDragunov20260922/Complete20260923/SK_SVD_Manny` 的实际槽引用记录在 `import_receipt.json`。镜片、独立枪机载体和手臂沿用各自材质。
- `Before/` 保留制作前 Blend 与七个原材质实例包；只能按目标文件恢复，不整目录覆盖其他会话的改动。

导入使用项目现有批次互斥的无界面 commandlet，退出码 0，日志包含 `SVD_SURFACE_IMPORT_COMPLETE`。材质图编译与资产保存已完成；没有 C++ 改动，不需要原生重编译。这些是制作和接入记录，不是效果验收。

## 再制作入口

1. `prepare_regions.py` 从当前源模型的实际连通壳体生成 `body_regions.json`。只改材质参数时无需重新生成分区；若改变拓扑，需要重新制作分区。
2. Blender 后台运行 `build_finish.py`，按原 UV0 烘焙 BaseColor／ORM，并保存上述两个 Blend。
3. UE 关闭时运行 `import_background.ps1`；若编辑器已打开，使用项目现有互斥桥执行 `import_finish.py`。

若从头运行旧 SVD 模型／材质导入入口，应最后再运行本目录材质导入，避免旧 `import_svd.py` 或 `fix_material_parents.py` 将七个实例接回初版母材质。普通完整网格导入仍使用这些稳定 MI 路径，无需另导网格或动作。

## 来源与交付范围

源模型、原始结构图及部分标记／纹样继续来自 LeroyCake 的 CC BY 4.0 SVD，见 [来源记录](../SVDDragunov20260922/PROVENANCE.md)。本轮没有引入新第三方素材。

没有运行游戏、效果渲染或操作回归；最终观感由用户测试。已有烘焙目录图标仍是此前 UV 修复版，这轮未另行渲染图标。枪械实际展示采用本次已保存的材质实例。
