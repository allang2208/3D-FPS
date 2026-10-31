# 公寓细部与城市街区整理发布

本批承接 2026-10-24 的公寓/海湾发布，保存后续卧室与床复用、厨房接触与电线、圆润车辆和夜间车灯、景观布置、近岸原生 PCG、道路修复及性能策略的原创制作链。正式关卡仍为 `/Game/GameMaps/L_CyberpunkApartment`。本次为文件归档、技能沉淀与 Git 发布，没有重新制作地图或运行游戏。

## 公开内容与本机依赖

- 公开精确清单中的 Python/PowerShell/HLSL、两个原创 C++ 作者工具、作者宿主描述与源码、制作说明和 SKILL。`publication-files.json` 记录工作文件 SHA-256；Git 提交按 `.gitattributes` 规范化换行。
- 地图、uasset、Blend/FBX、贴图/法线、图标、声音、第三方包、从第三方模型提取的几何、密集装配清单、完整回执和本机 Python 库继续留在本地。发布源码不构成这些资源的再分发许可，也不是可直接运行的完整游戏。
- 恢复需要合法取得 Soul: City、City Sample Buildings、City Sample/CitySamplePCG、BlackAlder 等现有内容，以及原公寓、家具、天气、水体、角色与设备基础。不能用公开配方替代供体资产。
- Content 仍通过 `D:/FPS3D/FPSGAME/Content` 联接到 `F:/FPSGAMEData/Content`。本次没有移动正式 Content、打开/关闭 UE、生成额外场景或改变全局光追/Lumen。
- 本机旧版本输入仍有真实依赖；`Revisions/BeforeRiverfront20261026/layout.json` 和 `make_layout.py`、原生 PCG `native_manifest.json`、`Audit/saved_scene.json` 与 WKB、`Repair/source_*`、`Performance/source_*` 均保留。局部 `.gitignore` 排除生成数据与宿主缓存，不修改共享根忽略规则的他人暂存内容。

## 当前制作和恢复顺序

| 部分 | 作者入口 | 正式接入/注意事项 |
| --- | --- | --- |
| 卧室细部与床 | `CyberpunkApartmentRebuild20261022/BedroomPilot20261024/RefinementV3` | `Integration20261024/install_level.py` 接回正式公寓，再调用 `BedReuse20261025`。旧 Pilot 目录是源依赖，独立试点地图已在前轮退役。 |
| 厨房 | `KitchenPilot20261024`，随后 `CyberpunkKitchenRepair20261026` | 使用现有容器/铰链；`cable_route.py` 为台面边缘 V2 走线合同。保留其源场景/geometry/资产回执。 |
| 全屋电线 | `CyberpunkApartmentCables20261027/layout.py`、`author.py` | `install_level.py` 保留设备身份、局部端点与静态圆角导向；仅自由段模拟。 |
| 车流与夜灯 | `CyberpunkTrafficUpgrade20261026` | 替换原三类车流批次，材质驱动夜灯和地面光斑，未新增逐车灯或 Tick。 |
| 外围楼体与景观 | `CyberpunkExteriorUpgrade20261025`、`CyberpunkUrbanLandscape20261025` | 保留已放在临江楼后方的景观；本轮近岸修复不重做对岸。临江景观使用 `layout_riverfront.py` 及其原始修订输入。 |
| 近岸河堤与绿化 | `CyberpunkNearBank20261028` | 当前 `layout.json` 已含道路修复后的旧树位置；不要用初始粗布局覆盖。 |
| 原生 PCG 街区 | `NearBankPCGRepair20261028/AuthoringHost`、`generate_native.py` | 离线真实执行图，输出为 26 个静态分区 BP；作者宿主不是第二套游戏场景。 |
| 道路/碰撞与性能 | `Repair/compose_repairs.py`、`Performance/manifest_policy.py`、`component_policy.py` | 当前 `publish_manifest.json` 是已优化输出；`build_publish_assets.py` 后 `install_level.py` 接入正式图。 |

上述路径均位于 `SourceAssets/`，表中厨房初始目录在 `CyberpunkApartmentRebuild20261022/` 下。常规全公寓恢复链 `RefinementV21/publish.py` 已串接后续升级，按本机安装回执选择执行；恢复回执必须与资产和布局同版本，不能伪造文件绕过依赖。

近岸重建注意：`Repair/repaired_manifest.json`、`Repair/mesh_jobs.json` 是性能优化前保存的生成结果，**不能直接重放**。需要道路修复再生成时，先恢复原生输入和 Audit 几何、保留 `Performance/published.json`，再运行 `compose_repairs.py`，使其输出包含连续道路与简化碰撞。`Performance/prepare.py` 是一次性脚本，`simplify_colliders.py` 会追加任务，不当作幂等入口。当前优化包的 `Performance/publish_background.py` 可按保留的 `manifest.json`/`mesh_jobs.json` 重新制作与安装，但它会回放这一保存版本，不能覆盖之后的布局修改。

作者宿主需要本机 City Sample 插件与内容接入；描述中的路径按合法安装位置调整。Python 几何配方使用 NumPy、SciPy、Shapely，本机库留在各任务的 `Audit/pythonlib`、`PythonDeps`、`BlenderDeps`。C++ 反射烘焙工具需要现有 Editor 构建和真实 RHI，普通资产制作可用 NullRHI。沿用工程共享互斥，不自动启动图形编辑器。

## 已有结果与本次检查边界

2026-10-28 的 `Performance/published.json` 记录正式地图保存；`result.json` 的模板与关卡配置统计一致：实例 156,483 → 122,558，启用碰撞实例 104,682 → 10,374，overlap 实例 156,483 → 0；9 类车辆代理均为 276 面，约 3.4 万道路小片改为 21 个连续分区。完整计数摘要见 [历史性能结构记录](historical-performance.json)。这些不是当前 FPS 实测，本轮也没有重新加载地图核实现场状态。

之前道路任务的离线几何检查记录了路面连通与局部净距；不证明游戏物理、导航或全场视觉通过。用户确认的是场景基本成功、性能仍需优化；后续结构优化尚无同机位帧率对照。本次只作归档散列、发布内容/大小/敏感信息/许可、索引差异和 Git 远端检查，不编译、不运行玩法、截图或性能测试。

## 退役与保留

225 个旧回滚快照、重复控制台日志及缓存/自动备份，共 701,943,989 字节，已移入 `trash/CyberpunkDistrict20261031/`。原路径、目标、SHA-256、原因及替代项见 [归档清单](archive-manifest.json)，移动后散列读回见 [归档回执](archive-receipt.json)。这是可恢复移动，没有永久删除；trash 不上传。

保留当前模型与制作源、详细引擎日志、实际生成输入、所有仍被引用的旧版本、每个备份系列的最新快照，以及优化前完整快照和原车碰撞备份。需要历史回滚时按清单逐文件恢复，不将旧地图/配置整批覆盖当前工作区。
