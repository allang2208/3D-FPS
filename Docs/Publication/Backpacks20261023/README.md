# 五款背包整理与源码发布（2026-10-23）

本批发布行军包／登山包修复、远征包、简易斜挎包、开拓者战术包的源码、制作配方、必要目录与穿戴配置。当前本机资产已保存并接入；本仓库按既定规则不再分发模型、贴图、图标、UE 包、玩家存档或测试宿主。

## 当前实现

| 背包 | 主背包新增 | 夹层（横 × 竖） | 当前穿戴制作入口 |
| --- | --- | --- | --- |
| 简易斜挎包 | 1 行 / 18 格 | 3 × 4 | `Tools/SimpleSlingBag/author_gravity.py`，GravityFitR3 |
| 行军背包 | 1 行 / 18 格 | 6 × 6 | `Tools/BackpackHarness/refine_alice_sides.py` + `Tools/BackpackMotion/author_alice.py` |
| 登山包 | 1 行 / 18 格 | 5 × 6 | `Tools/BackpackHarness/`，UEFrontFaceR6；针织件使用 MountainR2 |
| 重装远征背包 | 2 行 / 36 格 | 8 × 6 | `Tools/ExpeditionBackpack/` + BackpackResponseR2 |
| 开拓者战术背包 | 3 行 / 54 格 | 12 × 6 | `Tools/PathfinderBackpack/`，PathfinderMeshyHarnessR1 |

主背包原始 18 × 4，开拓者装备后为 18 × 7。容量从当前目录解析；夹层改列数先按旧行跨度迁移，换小包或卸下空间不足时完整拒绝事务。双肩包使用有界惯性，斜挎包使用重力、带长约束与躯干代理；包体和背带共享动态变换。肩胸固定区不随包体整体漂移。网络纠偏复位判断读取可见身体的位置，避开胶囊先纠正而身体仍平滑的跳变。

## 发布范围与共享前置

- 直接发布：背包动态与检查源码，`ApplyOutfit` 背包分支、刚性包体预加载、容量／迁移规则、读档迁移标记、主背包行数提示；五个 `items.json` 条目、五个 `player_body.json/outfits` 条目、显式 Cook 目录；本批制作工具和技能引用。
- `Integration/guest-backpack-layout.patch` 仅包含现有 `SanitizeGuestProfile` 末尾“先迁移再校验”的修复。完整服务器身份、重连与上传净化框架来自其他开发批次，当前公开基线未包含该函数定义。前置符号和本机文件散列见 `Integration/prerequisites.json`。不要用本机完整共享文件覆盖仓库，也不要把该补丁当成整个联机框架。
- `integration-manifest.json` 记录应发布的目录项／穿戴配置散列、容量、源码和 Cook 路径；`published-files.json` 记录精确发布路径。并行武器、服装、法术及其他 UI 改动保留在本机工作区。
- 本机整合构建和联机记录不代表公开仓库干净检出可直接构建；共享框架和授权资产仍需恢复。材质颜色、摆动渲染及极端姿态由实际游戏体验确认。

## 恢复与继续制作

1. 保留各 `SourceAssets` 当前有效 Inputs／BodyInputs、模型、纹理、作者数据、实际 UE 包和保存回执。Fab/Epic 原资产按各自许可获取；用户 Meshy GLB 原件及权利留本机，本次没有授予公开模型再分发许可。
2. 行军包最初母版位于 `SourceAssets/PortableBackpackAlice20261019`；`AliceBackpack_uv_bevel_prebuckle.blend` 仍被正式搭扣制作器使用，不能当旧版删除。侧袋开口源位于 `BackpacksReview20261021`，当前穿戴源位于 `BackpackMotion20261022/AliceFit`。
3. 登山包使用 `BackpackHarnessRebuild20261020`。保留 `winding.py` 的作者／UE 面序转换、UV 与法线面角顺序、连续封壳与 LOD 接缝。不要重跑已被否定的模板拟合器。毛衣专用修正由 `fit_mountain_sweater_r2.py` → `register_response_refit.py` → `save_refit_r2.py` → `publish_response_r2.py` 接入。
4. 远征包的完整作者链为 `prepare_source.py` → `read_body_inputs.py` / 有 provenance 的输入准备 → `author.py` → `save_assets.py` → 当前动态配置；共享双肩运动源在 `Tools/BackpackMotion/`。
5. 斜挎包保留 `prepare_source.py`、`split_pouch.py`、`author.py`、`save_assets.py` 的基础能力；当前贴身路线为 `read_gravity_body.py` → `author_gravity.py` → `save_gravity_assets.py` → `publish_gravity.py`。旧 R1/R2 发布器已归档，目录项以本次 `items.json` 为准。
6. 开拓者依次使用 `prepare_source.py` → `read_body_inputs.py` → `author.py` → `prepare_buffers.py` → `save_assets.py` → `publish.py`。`author.py` 默认读取本款 `BodyInputs`；现有导入回执记录的是读取资产一致、时间未过期的 GravityFitR3 输入复用。不能无条件拿旧身体／衣物数据套新角色。
7. 保存器复用 `Tools/ChainmailPants/save_assets.py` 的 GeometryScript IO；配置写入走 `Tools/PlayerBody/config_transaction.py`，按具体字段保留并行工作。制作所需 NumPy/SciPy/Blender 与 UE 5.8.2 按本机环境配置。只写脚本不等于资产已保存。

## 已有检查证据

本批整理前，按用户要求完成：Editor/Game 构建；81 项合成容量与旧布局迁移断言；五款 × 六套衣物共 30 项实际资产组件生命周期检查；同机 UDP 主机／客机共 14 个阶段，覆盖不同装备、卸包、快速换装、Pawn 重建、同档案重连，各端设置 60 ms 延迟和 3% 丢包。摘要见 `review-summary.json`，原始日志与隔离测试存档保留本机。

真实网络夹具只覆盖开拓者与重装远征两款。NullRHI 测试角色固定位置，未验证奔跑渲染；Pawn 重建不等于完整伤害／死亡／布娃娃流程；未执行第二客机、专用服或跨机器打包运行。本次仓库整理仅做用户要求的发布内容检查，不重跑游戏测试。

## 归档与技能

本次新增归档 `trash/backpack-retired-20261023`，逐文件原路径、目标、字节数、SHA-256、原因和替代物见 `retirement.json`。之前已清退的旧背带链仍在 `trash/backpack-rejected-20261020-full-audit`，本次同步其 21 个已跟踪文件的删除。归档可恢复，未物理删除。

沉淀到 [背包工作流](../../../skills/ue5-item-asset-workflow/references/backpack-equipment.md)：导入面序和法线、源壳保真、贴身与动态约束、容量迁移、联机检查边界、制作依赖识别和精确源码发布。个人维护源与本项目引用同步；不把历史用户认可扩大为所有动作或网络场景通过。
