# 绿色皮肤巨手：模型、动作与 UE 接入

2026-09-27 发布整理：当前制作源与输入保留；下文 `Before*` 和修复前备份的历史路径已按 [归档清单](../../Docs/Monsters/monster-hands-retired-20260927.json) 移入本机 `trash/monster-hands-20260927/`，不再从旧位置恢复。公开源码、未发布共享接口与合法素材边界见 [发布说明](../../Docs/Monsters/monster-hands-publication-20260927.md)。

2026-09-26。用户在绿色 V02 三视图之后要求“开始出模型”；沿用已指定的 Meshy 生成与拓扑、本地专用骨架与蒙皮路线。

## 已保存产物

| 内容 | 本地路径 |
| --- | --- |
| 可编辑四边面网格、骨架与蒙皮 | `LocalRig/FleshHand_Green_LocalRigV1.blend` |
| 同骨架的近、中、远距离网格制作源 | `LocalRig/FleshHand_Green_WithLODs.blend` |
| 绑定 FBX | `LocalRig/SK_FleshHand_Green_LocalRigV1.fbx` |
| 绑定 GLB，包含材质与纹理 | `LocalRig/SK_FleshHand_Green_LocalRigV1.glb` |
| LOD1、LOD2 的 FBX / GLB | `LocalRig/LODs/` |
| 本地贴图 | `LocalRig/Textures/` |
| Meshy 原始高模、四边面 FBX、GLB/OBJ 与 PBR | `Meshy/candidate01/downloads/` |
| 制作参数、骨骼定义与制作回执 | `meshy_settings.json`、`LocalRig/rig_definition.json`、`LocalRig/authoring.json` |

2026-09-27：用户要求完成剩余工作后，已补齐原五套动作的三维重制、Hit / Dizzy / Death、掌心副拳、三种攻击与小手召唤、共用战斗和 F6 接入；后台构建与实际导入保存记录见 `ue_installation.json`。详细合同和新加入的性能边界见 `../../Docs/Monsters/FleshHandIntegration20260927.md`。未渲染或测试。

2026-09-27 掌心正面修正：实际生成模型掌纹朝 Blender `+Y`，指甲/手背朝 `-Y`。当前骨骼定义元数据、8 个动画 FBX、掌心副拳和完整导入脚本已统一为掌面 `+Y`；主怪/小手蓝图组件为 `Pitch 0 / Yaw +90 / Roll 0`，将掌心对齐角色前方 `+X`，保持直立并沿导航方向转身移动。`install_palm_forward.py` 已通过后台 commandlet 完成相关 UE 资产导入和保存，回执见 `palm_forward_installation.json`。`BeforePalmForward/` 保留调整前源文件与资产。没有启动 GUI、游戏、渲染或测试。

## 模型与性能预算

- Meshy 四边面母版：13,637 顶点、13,635 个四边面。保留生成表面、UV、自定义角点法线和原始模型；未声称已手工重排全部关节环线。
- LOD0：27,270 三角面；LOD1：13,634 三角面；LOD2：5,454 三角面。三个等级共享骨架与 1 个材质槽；UE 已导入这两个 LOD，屏幕比例切换为 .42 / .16。
- 专用手部骨架：22 根骨骼，其中 21 根参与变形。包含非变形 root、wrist、palm、四条掌骨与三段手指链，以及三段拇指链。
- 初始骨热权重结合实际网格的手指连通区域隔离、拇指区域、表面邻接平滑和接缝权重统一；最后限制为每顶点最多 4 个骨骼影响。
- 制作使用一米高的标准绑定坐标；UE 主怪缩放 2、小手缩放 .65；不使用服务自动估测尺寸。
- 生成请求为 4K PBR；本地保留颜色、法线与材质通道。UE 已配置 2K 颜色/法线、1K ORM/组织掩码和纹理流送；面数记录不代表同屏帧率。

## 生成与来源

- 输入：`References/FleshHand_ThreeViews_v02_Green.png`。用户指定绿色皮肤，参考当前突变体 SurfacePolish 的源 BaseColor；来源明细见 `References/README.md`。
- `prepare_inputs.py` 按原图空白分隔裁出掌面、侧面、手背，等高白色补边，仅拆图，不重新生成外形或改变比例。三个输入与散列位于 `References/MeshyInputs/`。
- Meshy 端点：`/v1/multi-image-to-3d`；模型档：`meshy-7.1`；几何档：`2k`；PBR、4K 纹理、quad 目标 15,000 面；保留 `pre_remeshed_model.glb`。
- 任务：`01a0de58-cdd3-7578-8df0-ffe77fb792e2`，服务回执 `SUCCEEDED`，已下载 11 个输出文件。任务实际扣除 35 积分，提交前后余额为 1998 → 1963；回执和去签名下载清单保存在 `Meshy/`。
- [官方多图生成接口](https://docs.meshy.ai/en/api/multi-image-to-3d)、[官方计费](https://docs.meshy.ai/en/api/pricing)。本次没有提交额外收费的自动绑骨或动作任务。
- 三视图为本任务生成的原创参考，3D/PBR 通过用户提供的 Meshy 账户生成；未核实账户许可等级，不将服务模型声明为 CC0 或公开再分发素材。
- 密钥仅进入当前生产进程的 `MESHY_API_KEY`，进程已结束。作者文件、配置、回执与日志不保存密钥；下载清单剥除签名查询串。

## 制作入口

1. `prepare_inputs.py`：按 V02 冻结输入。
2. `meshy_pipeline.py`：仅从环境变量读取认证；已有 `task.json` 时复用任务，禁止因下载或绑定失败重复收费生成。
3. `prepare_rig_geometry.py`：读取生成四边面网格，提供关节定位所需坐标与分段数据，无渲染。
4. `LocalRig/surface_landmarks.json`：本次生成网格的关节中心；模型改变后应重新放置，不能把旧坐标直接复用到其他手型。
5. `define_rig.py`、`author_local_rig.py`：定义手部骨链、创建权重并导出。游戏导出沿用服务 GLB 的三角面次序，按对应空间位置转移四边面权重。
6. `author_lods.py`：从绑定母版制作两个距离网格，保留近景源并再次限制权重影响数；另存带 LOD 的 Blender 文件。

7. `author_animations.py`：按原图集姿态和时序烘焙 8 个三维动作，另存 `Animations/FleshHand_Animated.blend` 与动画/副拳 FBX。
8. `prepare_ue_inputs.py`：打包本怪 ORM / TissueMasks，转码原攻击音效。
9. `install_ue.py`：后台实际导入网格/LOD、动画、查询 PhysicsAsset、材质、AI 和主怪/小手蓝图，保存到 `/Game/Monsters/FleshHand/`；写出保存回执。

10. `author_charge.py`：按本怪掌面和各指骨轴制作蓄力闭拳、握拳冲锋、松拳收势三条动画；实际指腹拟合与拇指外扣参数保存在 `Charge/authoring.json`，可编辑源为 `Charge/FleshHand_Charge.blend`。不重写原八条动作。
11. `install_charge.py`：基础 DLL 构建后导入三条冲锋动画，绑定主怪蓝图并保存可调参数；完整 `install_ue.py` 也会接上此步骤。战斗合同见 `../../Docs/Monsters/FleshHandCharge20260927.md`，实际接入回执为 `Charge/ue_installation.json`。
12. `save_charge_prediction.py`：仅保存冲锋预测强度及最大提前距离，不重导动画。按突变体的起跳重采样方式，在巨手蓄力结束时根据目标水平速度和实际接触时间计算提前量，带目标穿墙截断、完整/半量/零提前量路线回退；冲出后保持直线。
13. `save_mobility_and_inspect_reactions.py`：保存大手 259.2 / 小手 324 cm/s 普通移速，保留原动画参考速度 216 / 270，使满速播放率达到 1.2；普通 Slam 新增 150 cm 击退。按本轮用户要求读取硬直/眩晕等实际绑定，回执为 `Mobility20260927/installation_and_reactions.json`。缺失的手怪击飞、倒地、正反面起身仅完成设计，见 `../../Docs/Monsters/FleshHandMobilityReactions20260927.md`。
14. `author_knockdown.py` / `install_knockdown.py`：用户继续授权后，已制作并实际导入 10 段正反腾空、落地、倒地与指腹撑起/侧翻起身动画，绑定大小手 `HandKnockdown` 组件并保存两份蓝图；原生构建完成。源与成功回执位于 `Knockdown/`。当前合同见 `../../Docs/Monsters/FleshHandKnockdown20260927.md`，替代第 13 项首轮「仅设计」状态；未进行试玩、渲染或性能测试。

蓄力握拳冲锋的基础模块构建与三动画/主怪蓝图导入保存均已完成；本轮未进行游戏、画面或性能测试。

15. `retire_palm_attack.py`：按用户最新要求清除大小手蓝图的掌心副拳、Hammer 和召唤类引用，原生选择逻辑取消 Hammer，重拍不再调用召唤。`install_ue.py` 同步此规则，避免重建恢复旧绑定；源模型与旧动作不删除。保存回执位于 `AttackSimplification/installation.json`。

16. 冲锋表现优化：`author_charge.py` 已重新烘焙后压、绷紧颤动和收势卸力；`author_charge_audio.py` 生成原创蓄力/破风音。`install_charge_visual_all.py` 依次导入三段动画、五份专用材质、两段音频并保存大手蓝图引用。`ChargeVisual/` 保存源音频、制作回执和构建/导入日志；完整流程同步接入 `install_ue.py`。特效使用最多 8 组共享槽及现有流体装饰预算，具体合同见 `../../Docs/Monsters/FleshHandChargeVisual20260927.md`。未进行试玩或性能测试。

17. 移动僵硬修订：`author_locomotion.py` 制作大手 `WalkWeighted`、小手 `WalkScurry`，用腕缘交替承重、掌部回弹、错相手指替代同步摆动和腕部缩放；`install_locomotion.py` 保存大小手独立 `MoveClip`，完整导入入口最后执行此步骤。`Locomotion/` 保存源文件、FBX、回执和接入日志。原生仅调整本怪起停混合、追击/返回相位连续及低速播放率，普通移速不变。见 `../../Docs/Monsters/FleshHandLocomotion20260927.md`，未运行游戏测试。

18. 基础动作接地修复：`repair_basic_grounding.py` 修正已有 Idle、Slam、GrandSlam、Hit、Dizzy、Death 的根位置轨道，将世界竖直补偿转换到正确的骨骼局部轴；`author_animations.py` 同步修正。`install_basic_grounding.py` 已在后台重导并保存六个同名动画包，保留大小手的现有引用；制作／接入回执和旧文件备份在 `GroundingRepair/`。详见 `../../Docs/Monsters/FleshHandGroundingRepair20260927.md`，未追加测试。

F6 入口为“异变巨手”和“小皮肤手”。大手当前只保留普通拍击、重拍和蓄力握拳冲锋，两种拍击均不产生小手；小皮肤手保留独立入口。主怪死亡使用专用动画，不使用布娃娃。未运行游戏、渲染或测试，由用户测试。
