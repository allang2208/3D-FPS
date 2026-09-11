# 手脑案例：2026-09-11

以下为本轮工作记录，继续任务前检查磁盘与当前代码；不代表未来重新验收。

**当前基线（2026-09-11 15:52）**：用户接受 SurfaceV07；行为已改为共用 Behavior Tree + NavMesh，详见 [行为流程](monster-ai.md)。最终独立 AI 16/16、护士村庄 15/15、手脑村庄 30/30 通过；布娃娃接地已通过。下文的局部避障和早期布娃娃失败属于历史阶段，不能作为当前实现说明。

## 真源及版本

- 原画/动作/音效：`Y:/开发/游戏/素材库/怪物/手脑/`。Idle 单图；Move 12 帧/1 秒；Slam 26 帧/2 秒，1 基第 14 帧接触，即 `(14-1)/26*2 = 1` 秒；Howl 28 帧/3 秒。缺死亡参考，死亡为本地设计。
- 工作根：`D:/FPS3D/FPSGAME/SourceAssets/HandBrain20260910/`。
- `hunyuan_v01/` 为主体、专用骨架、Idle/Move/Slam 基线；已有独立攻击手臂与冠部手扇。不能宣称作者文件只有一个网格。
- `howl_v01/` 通过凹入旧脸、叠入生成张嘴脸实现嚎叫，用户因两套模型拼接拒绝。已归档至工程 `trash/monster-workflow-20260911/SourceAssets/HandBrain20260910/howl_v01/`，不作正式输入。
- `howl_rebuild_v02/` 在原脸局部重拓扑，连接口腔、重投影 UV、局部加牙与口部骨骼；未复现源图所有头顶手掌完全张开的程度，需保留此视觉限制。
- `death_v01/delivery/HandBrain_FiveActions.blend`、`SK_HandBrain_FiveActions.fbx` 和 GLB 是当前五动作源。4 个作者网格、38 骨；UE 导出合并为一个 Skeletal Mesh 的多个材质区段。

## API 与可重建工具

- `Tools/AssetPipeline/hunyuan3d.ps1` / `.py` 使用 TokenHub `hy-3d-3.1`；接口为 `https://tokenhub.tencentmaas.com/v1/api/3d/{submit,query}`。以当前客户端实现为准。
- 凭据由客户端读取本机 DPAPI 文件；不要展示、复制明文密钥，来源清单也不写临时签名下载地址。
- 历史 402/401008 来自免费额度耗尽且后付费未启用，不是余额为零。检查对应生成模块启用状态后续查原任务，避免重复扣费。
- 作者阶段各目录的 `rebuild_local.ps1` 与 Python 脚本保留在 SourceAssets，技能仅索引，不复制成另一套维护真源。
- `howl_rebuild_v02/build_single_face.py`：保留口部外边界、局部环形拓扑、BVH/重心 UV 重投影；`animate_export.py`、`validate.py`、`verify_fbx.py`、`validate_glb.py` 负责动作和导出检查。
- `death_v01/build_death.py`：中性 `death_pivot` 承接 root 子骨与 root 权重，保持原有动作；死亡 2.8 秒，约 1.12 秒接地，2.05 秒后静止，root 不位移。作者平地接触验证不代表 UE 物理地形通过。
- `Tools/HandBrain/prepare_export.py`、`prepare_audio.py`、`import_handbrain.py`、`place_village.py`：合并 SK、分别导出五个动画、单声道音效、PBR 与蓝图导入、关卡刷怪点保存。复用前读参数，缓存存在时导入可能跳过旧资产。
- `Tools/HandBrain/Open-HandBrainVillage.ps1 -Audit`：隔离存档运行验收；结果 `Saved/HandBrain/acceptance.json`，画面同目录。无 Audit 参数用于正常游戏。

## 导出与实现经验

- Blender 5 动作切换同步 action 和 action_slot；世界空间旋转/位移需转换到骨骼局部空间。
- GLB 的 UV 分裂顶点不等于几何碎片。先确认焊接语义再减面，不盲目填全部洞。几何修改后检查自定义法线。
- UE 用厘米；本例 Blender +X 前向、Z 向上，约 2 米高。测量实际导入骨架前向，不凭通用 -90 度模板旋转。
- 本例 PBR 导出将法线绿色通道翻转为 DirectX，粗糙度取 MR 绿色通道；避免导入设置再次翻转。6 材质槽应按语义映射核对。
- Unreal Python 非蓝图暴露属性使用 `set_editor_property`。本例 PhysicsAssetFactory 未暴露目标网格入口，改用 `HandBrainMonster::CreatePhysicsAsset` 编辑器辅助函数。
- Blender 批处理带 `--python-exit-code 1`，UE commandlet 检查明确完成标记。
- 共享编辑器构建遇到载入 DLL 时，核对项目已有构建方法；本轮使用带唯一后缀的 Editor 构建并启动新进程验证。PowerShell 中 `-ModuleWithSuffix=FPSGAME,编号` 整体引用。不关闭其他任务进程；旧编辑器不等于已加载最新模块。

## 数值与游戏合同

- `Source/FPSGAME/Monsters/HandBrainMonster.*`、`HandBrainFearComponent.*`、`HandBrainVillageSpawner.*`、`HandBrainAudit.*`；魔法伤害接入 `FPSCombatHealthComponent.cpp` 的 mdef 分支。
- 等级 12、HP 1500、物攻 50、魔攻 55、魔防 65；经验 2892 和移速 100 cm/s 是本轮 UE 调整数值，不冒充二维原始值。
- Slam：2 秒，1 秒结算一次，100 点防御前物理伤害，范围 300 cm、冷却 6 秒；前摇锁定判定方向，支持躲避/遮挡/打断。
- Howl：3 秒，`[0,3)` 在 0/.5/1/1.5/2/2.5 秒共 6 跳，每跳 27.5 点防御前魔法伤害；半径 600 cm、冷却 30 秒。恐惧 3 秒最多 3 层，减速 33/66/99%，强制远离并到期释放输入。
- Death：播放死亡后约 1.15 秒交给布娃娃，20 秒尸体回收；生成器在尸体销毁后计时 300 秒再次生成，总计约死亡后 320 秒。
- `/Game/Monsters/HandBrain/`：SK_HandBrain、PA_HandBrain、BP_HandBrain 和五个 A_HandBrain 动画。
- `/Game/GameMaps/L_Normandy_FPS_Test`：`HandBrain_Village_01` 单实例刷怪点。移动目前为地面探测+局部扫掠避障，不是全局 NavMesh 寻路；未完成联机或打包验收。

## 验收边界和待办

- 五动作导出时长为 Idle 2、Move 1、Slam 2、Howl 3、Death 2.8 秒；重新导入渲染及原动作保持检查已执行，具体数字读对应 delivery 验证 JSON。
- UE 导入、村庄保存回读、真实枪击、追击、攻击时机/去重/冷却、躲避/遮挡/打断、恐惧释放、奖励一次、尸体回收与再次刷新在本轮自动验收通过。
- **布娃娃尚未通过：`ragdoll_stays_above_terrain` 失败。** 最新记录 cranium 约低于地面 81 cm，尸体近景不见模型。现有 base/neck/cranium 三刚体配置仅为待修实现，不能当已验证配方。
- 后续先读 `Saved/HandBrain/acceptance.json`、`play.log`、`inspect-physics.log`，核对参考姿态下刚体变换、动画转物理时的世界变换与地形碰撞，再复测尸体可见/接地。`inspect_physics.py` 上次执行失败，需先查看异常，不能称其已可用。
- 生成任务和模型数值验证不能替代角色身份目检；开启物理不能替代尸体接地验收。本次技能整理没有重跑或修复上述游戏失败。

## 后续修复：2026-09-11 09:01

上述布娃娃未通过项已在后续本地修复：累计骨骼缩放 100 倍，而胶囊半径和长度未逆缩放。BuildPhysicsAsset 已统一换算，PA_HandBrain 已重建，物理半范围恢复为 46/46/114.5 cm。接地验收改用实际胶囊支撑距离，不用偏离胶囊中心的 cranium 关节高度。村庄最终 30/30 通过，证据在 Saved/HandBrain/ragdoll-fixed，详见 Docs/HandBrainRagdollFix.md。此结果只覆盖该次场景；继续工作仍须核对当前资产和日志。


### 2026-09-11 Fab material V04 runtime correction

User-added `/Game/ZombiSkinMaterial` maps are exported and blended in `SourceAssets/HandBrain20260910/material_v04`. Use `Tools/HandBrain/refine_fab_materials.py`, `bake_fab_materials.py`, `verify_fab_bake.py`, and `import_fab_materials.py`. Preserve the original wound mask and bake rest-space organic height/color/roughness into existing UVs. Oral interior has degenerate UVs and uses constant mucosa, not an empty bake.

A fresh game revealed that material appearance cannot be accepted from in-memory slot assertions: `save_loaded_asset(mesh)` skipped the change unless forced with `False`. The original materials also lacked `used_with_skeletal_mesh`, causing runtime default-material substitution. Set skeletal usage before compilation, force-save the mesh, then restart the independent game and check both its actual image and missing-usage warnings. `finalize_fab_materials.py` and `finalize_report.json` record this correction. Never rerun the original full mesh/physics import merely to replace materials.


### 2026-09-11 Realism V05 mouth and contact refinement

Active candidate `/Game/Monsters/HandBrain/RealismV05/SK_HandBrain_Realism` and its howl clip are assigned in `BP_HandBrain`; refer to `SourceAssets/HandBrain20260910/realism_v05/STATUS.md` and `activation.json`. Lower-lip shape/chin weights and 29-degree jaw hinge replace the earlier large downward translation. Oral lining now has usable UVs and 18 baked maps pass reload checks. Old constant-only mouth workaround applies to V03/V04, not V05. Existing skeleton and other four animation clips are retained.

Contact diagnostics now sweep the actual oriented capsule against the finite scene geometry. A plane extrapolated from one triangle can falsely intersect a capsule on irregular terrain; do not treat that plane's support distance as definitive penetration. Preserve the same tolerance, keep old/new readings in logs, inspect the actual corpse and retain failed evidence. Three bodies use CCD and 16/8 solver iterations. First V05 village run passed 30/30 with -0.009 cm sweep gap; later runs are documented with the delivery, not assumed universally stable.


### 2026-09-11 Sculpt V06 hand anatomy pass

`SourceAssets/HandBrain20260910/sculpt_v06/STATUS.md` records the active `/Game/Monsters/HandBrain/SculptV06` mesh and Howl clip. Landmark-guided geometry edits cover 26 visible hands / 92 finger segments: 6,137 of 60,926 body vertices moved, maximum 5.731 mm. A 1,456,656-vertex high sculpt supplies creases and nail detail; runtime combined vertex count remains 84,546. This is local refinement, not full anatomical retopology of every hand.

Use `sculpt_hands.py`, `bake_sculpt.py`, `merge_sculpt_maps.py`, `verify_sculpt.py`, `preview_sculpt_compare.py`, `validate_sculpt_contracts.py`, `export_sculpt.py`, `preview_sculpt_export.py`, and the V06 import/activation scripts under `Tools/HandBrain`. Clear stale custom normals after geometry edits. Bake high color to its own UVs, selected-high-to-low tangent normals, and composite only the sculpt-area mask; preserve mouth maps and outside-mask pixels. Resolve appended Blender materials using actual export names, including numeric suffixes. Identical-lighting clay and textured close-ups are separate evidence.

V06 exact skin-weight hashes and sampled bone poses match V05; the five action contracts remain unchanged. Fresh village run at 13:06 passed 30/30 with -0.004 cm capsule sweep gap and a visible corpse, recorded under `sculpt_v06/runtime`. Fine close-up anatomy remains limited in planar, occluded and separate attack/crown areas. Preserve this quality boundary when reusing the workflow.


### 2026-09-11 Surface V07 local refinement

`SourceAssets/HandBrain20260910/surface_v07/STATUS.md` records the next active mesh/Howl under `/Game/Monsters/HandBrain/SurfaceV07`. Connected local tessellation increases body vertices from 60,926 to 91,112, followed by bounded surface relaxation and knuckle/tendon support. Combined export has 114,732 vertices. This is local surface refinement, not complete per-hand quad retopology. New vertices interpolate UV/deform layers; validate normalized weights and unchanged bone poses rather than requiring unchanged body topology hashes.

Tools use the `surface_v07` suffix under `Tools/HandBrain`. Bake a new normal only within the SurfaceRegion mask and retain color/roughness/oral maps. Keep sculpt attributes in the source; remove bake-only attributes from the export copy before joining. Compare clay and textured renders under identical lighting. Broad original planar forms and occluded/thumb/attack/crown anatomy remain a stated quality limit.

Fresh V07 village run at 13:19 passed 30/30, with -0.057 cm capsule sweep gap and a visible grounded corpse; evidence is in `surface_v07/runtime`. This is one regression run, not a new LOD or packaging-performance acceptance.


### 2026-09-11 玩家反馈修正验收边界

旧 V07 的胶囊接地通过遗漏了实际渲染表面穿地。后续复现最低表面低于地面 88.367 cm，约 72% 采样点穿地；根因包括物理根缺失和轴向胶囊未覆盖手掌。当前采用不碰撞 root 与主体拟合凸包，具体修复、真实蒙皮读法、当前回归和失败证据见 [反馈回归](monster-feedback-20260911.md)。上面的历史 30/30 不能用作当前尸体表面合格的依据。
