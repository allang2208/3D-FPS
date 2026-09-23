# 突变体-3：材质槽与追击返程修复

当前版本与恢复顺序见 [突变体发布入口](Mutant3FeralPublication20260923.md)。本文保留阶段记录；其中 before/baseline 快照及已退役独立手臂求解已按归档清单移至 trash。

日期：2026-09-23。对应用户反馈“贴图还是没有加载；追踪一段后跑回生成位置，然后重新追击”。

## 材质根因与落盘

当前原生类、默认 Mesh 组件及正式资产均引用 `KhaimeraV2/SK_Mutant3_Claw`。组件无材质覆盖，网格仅有一个材质槽。`M_Mutant3_Meshy` 的骨骼网格用法有效，并可解析 BaseColor、Normal、Roughness、Metallic 四张纹理。之前的材质输出修复已经保存，但没有覆盖网格自己的渲染分区映射。

本次后台修复日志给出了直接证据：

```text
MUTANT3_SURFACE_BEFORE lod=0 section=0 render_material=1 slots=1
MUTANT3_SURFACE_REBUILT lod=0 section=0 render_material=0 slots=1
MUTANT3_SURFACE_SAVED ... SK_Mutant3_Claw ...
```

旧 FBX 重导入脚本在导入后恢复一元素 Materials 数组，留下引用第二槽的源分区／渲染缓存。引擎加载时虽修正了导入模型索引，渲染缓存依然为 1。只修材质图不能解决这个缺口。

新增 `Mutant3Surface.cpp::RepairSurfaceBinding`，仅处理这一个单材质正式网格：统一槽名称与 polygon group 的 imported material slot name，修正 imported section 的 MaterialIndex、清理 LOD 覆盖映射，提交 MeshDescription 并强制失效旧派生缓存，重建后保存。没有修改位置、UV、蒙皮、骨架、动画或物理资产。后续 `claw_reference_20260923/import_open_claw.py` 在恢复材质数组后也调用同一修复，防止再次导入留下错误分区。

正式保存资产：`Content/Monsters/Mutant3Meshy/KhaimeraV2/SK_Mutant3_Claw.uasset`。

## 追击返程的判定错误

共享控制器原先无条件执行“离出生点 > LeashRange 就返回”，突变体走默认 2400 cm。返回标记优先于攻击／追击，而且只在回到出生点后解除。随后视觉缓存又重新获取同一玩家，所以出现“追出 24 米 → 强制返程 → 重新追击”的循环。

另一个边界是当前已知目标仍被最初的 AggroRadius 1200 cm 限制，越过该距离即停止刷新可见证据；本轮改为在持续追踪时采用感知配置中的 LoseSightRadius（当前默认 1900 cm），仍须真实视线无遮挡。初次查找目标的 AggroRadius 保留。

仅突变体采用以下规则，其他怪物的出生点活动范围保持原样：

- 有效、可见或仍在记忆中的目标维持追击，不因离出生点 24 米强制返程。
- 丢失视野后仍保留现有记忆时限，默认 12 秒；死亡、失效或记忆超时后解除目标并返程。
- 返程途中允许从感知缓存重新发现玩家，并解除返回标记，不必先跑回出生点。
- 受控、死亡、攻击时序、攻击范围和导航避障保持原有合同。

## 构建与交付状态

- 常规 Editor 基础 DLL 构建成功：`Saved/BuildEditor/build-20260923-213115.log`。
- 后台命令行资产修复已执行并保存：`SourceAssets/Mutant3Khaimera20260923/material_return_fix/repair_surface.log`、`surface_saved.json`。
- 当前编辑器在处理期间自行退出；没有启动交互编辑器。一次结束 PIE 的桥请求未连接到编辑器，未执行；后续全部通过后台构建／commandlet 完成。
- 未启动游戏、运行回归、截图或进行画面验收，由用户测试。构建／资产保存成功不替代实机表现确认。
- 本次修改前备份位于 `SourceAssets/Mutant3Khaimera20260923/material_return_fix/before/`。
