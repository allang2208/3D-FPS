# 巫婆 Meshy 制作状态

## 2026-09-21：暂停，用户反馈未达预期

V06 身体与 SpellSupportV07 攻击已接入，但用户试玩仍不满意；独立 WitchFoundation 人体动作粗模可用。后续优先处理原模型与衣物/腿脚蒙皮适配，不继续在原身体上叠加动作修补。保留当前运行对照、完整粗模候选、原始云端素材和分件；废案按 `Docs/Monsters/witch-paused-publication-20260921.md` 及 `Docs/AssetArchives/witch-retired-*-20260921.json` 移入本机 trash。待办为 `Docs/Backlog.md` W1–W3。以下均为制作历史。

## 2026-09-20 当前：原裙修复 CleanRobeV06

显示消失修正已保存：网格与动画的 FBX 场景单位转换统一开启，模型从 1.9 cm 恢复至 190 cm、骨架缩放恢复为 1；身体和原裙的显示区段均启用。错误尺寸的布料重建为厘米单位 `Witch_CleanRobe_ChaosV06Cm`。本次修正入口为 `Tools/Witch/repair_v06_visibility.py`，最新保存回执为 `ue_clean_robe_v06_visibility_fix.json`；未运行游戏测试，F6 清除旧实例后重新生成。

修正版已完成导出、布料提取、最终显示模型重导入和保存。已移除错误撑大的内部身体、误带 Quinn 双手及沿用的小腿内衬；只导出七个原 Meshy 显示部件。腰口和脚部切口使用相同蒙皮，新的 2368 顶点代理只用于布料，固定腰口与脚踝附近，中段最大允许位移为 6 cm，使用专用五胶囊碰撞体。

当前制作入口为 `clean_robe_v06.py`；组合源、独立 Blender/FBX 部件与更新后的动作源位于 `Authoring/CleanRobeV06`，导出位于 `Delivery/CleanRobeV06`。五段动作键未改、无需重新生成。F6 保持原 `Witch` 入口，模型继续使用兼容路径 `/Game/Monsters/WitchMeshy/OriginalRobeV05/SK_Witch_Meshy`，其内容已更新为 V06。

接入保存记录 `ue_clean_robe_v06.json`；详细范围见 [CLEAN-ROBE-V06.md](CLEAN-ROBE-V06.md)。常规构建及后续绑定逻辑 Live Coding 已完成。未运行游戏、截图或验收，效果交由用户重新生成巫婆后测试。下方 V01–V05 均为历史记录，不能视为当前制作入口或已认可版本。

## 2026-09-20 历史：保留原裙的分件调整 V05

双层裙反馈修正：原裙最终 FBX 已排除 `Witch_Robe_SimProxy` 并重导入，提取布料用的完整输入另存为 `SK_Witch_OriginalRobeV05_ClothBuildSource.fbx`。此前仅靠 UE 禁用区段，代理源几何仍在；本次从实际渲染模型中去掉，不删除原裙或原布料模拟数据。作者源和 F6 `Witch` 引用保持 V05，五段动作不变。

定向排查确认 UE 区段 5 → 4，代理槽/区段已消失，最终 FBX 只保留原裙显示网格。用户关闭占用后，布料数据已从两份减为一份，原裙区段 3 已通过 UE 标准工具重新绑定并保存；其余区段无布料绑定。制作记录 `Saved/WitchV05-cloth-binding-repair.json`；未进行游戏试玩。

用户否定 V04 可见重建裙后，采用 `OriginalRobeV05`：可见下袍保留原 Meshy 的网格、褶皱、破边、UV 和 PBR；原脚单独切出并重新分配脚/脚趾权重。隐藏人体与 1984 顶点布料代理独立保存；上身持杖与下身成熟步态保存为可编辑动作层，同周期重采样后混合烘焙。V04 裙和全部旧资产保留。

作者源和交付 FBX 已完成，UE 模型/五段动画/材质/骨架/物理资产已保存到 `/Game/Monsters/WitchMeshy/OriginalRobeV05`。原裙与隐藏布料代理已绑定并保存，代理渲染区段已移除。原生引用已更新并完成常规 Editor 构建（`Saved/BuildEditor/build-20260920-190749.log`），编辑器已正常重新打开；现有 F6 巫婆入口和当前编辑器默认值已切到 V05。说明见 `ORIGINAL-ROBE-V05.md`，实际接入阶段见 `ue_original_robe_v05.json`。未测试，不代表穿模、抓杖或步态已获认可。

## 2026-09-20 分层人体、长袍与成熟步态 V04

最新制作目录为 `Authoring/LayeredV04` / `Delivery/LayeredV04`。可保留外观、双手与两件道具已拆成独立源资产；原始未切分母版、PBR 和原面/顶点索引保留。人体采用本地现有蒙皮素材，独立下袍重拓扑并投影原色/粗糙度；新行走使用 UE 原生 IK 重定向的女性步态与持物层，按真实脚掌校正平地高度。原 Meshy 24 骨保留，不继续使用 V03 简化腿管和程序步态。

UE 候选目录 `/Game/Monsters/WitchMeshy/LayeredV04`，模型、五段动画、独立材质/骨架/物理资产均已保存，Chaos Cloth 已建立并绑定下袍。F6 沿用 `Witch` 入口和原导航规格，当前编辑器默认值与原生源码均已切至 V04。具体接入/保存阶段见 `ue_layered_v04.json`。常规 Editor 构建成功：`Saved/BuildEditor/build-20260920-150739.log`；已正常重新打开工程。制作边界与来源见 `LAYERED-V04.md`。未测试，未新增斜坡脚锁 IK；旧版本以下内容仅为历史记录。

## 2026-09-20 裙摆与步态 V03

当前版本为 `RobeGaitV03`。已分离裙摆、补内部腿部、追加 24 根裙摆骨，重做脚部权重与约 1.9667 s、32 cm/s 的小步行走；五段动画包含烘焙裙摆摆动，未安装实时布料插件。已保存至 `/Game/Monsters/WitchMeshy/RobeGaitV03`，原生 F6 巫婆引用已更新，普通 Editor 构建成功。说明与实际接入记录见 `ROBE-GAIT-V03.md`、`ue_robe_gait_v03.json`。未测试，旧版本记录不代表认可。

## 2026-09-20 用户反馈后的 V02 更新

此前缺失的四段 Meshy 云端带角色 GLB/FBX 已用原任务全部下载，未再次生成或扣费。行走与持杖 V01 已被用户否定，现已导入云端原生套用动作加局部左手权重、卷握手形和掌心握点的 V02。制作内容与接入记录见 `CLOUD-GRIP-V02.md`、`cloud_grip_v02_manifest.json`、`ue_cloud_grip_v02.json`。下文描述此前 V01 阶段，下载阻断已解除；新版不代表用户认可或测试通过。

2026-09-20。模型、绑骨与五段身体动作候选已接入 UE，并加入 F6 交互开发面板。入口为 **F6 → 怪物生成 → 怪物类型：巫婆 → 在玩家前方生成**。完成必要常规 Editor 构建并重新打开编辑器；没有运行游戏、截图、验收渲染或测试，由用户测试。

## UE / F6 接入

- 角色类 `/Script/FPSGAME.WitchMonster`，目录 ID `Witch`；沿用面板数量、距离、导航落点、生成计数与清除。
- `/Game/Monsters/WitchMeshy` 已导入本体、骨架、物理资产、三套 PBR 材质、法杖、毒瓶和五段动画；导入记录 `ue_import.json`，收尾保存记录 `ue_integration.json`。
- 已接共用怪物行为树、追击/返回、生命/伤害/奖励、三发扇形法术、掷瓶/毒区、中毒与死亡 60% 时刻交接布娃娃。角色销毁时清理本角色产生的投射物/毒区。
- 本轮完整 Editor 构建成功记录：`Saved/BuildEditor/build-20260920-005740.log`。未运行测试，不作为动作、材质或物理效果认可。
- 具体时序和剩余机制见工程 `Docs/Monsters/WitchMeshy.md`。个人与工程怪物技能均已加入“新怪物接入时同步登记 F6 生成目录”的要求。

## 已落盘

- 本体、木杖、毒瓶：Meshy 7.1 三视图生成模型，原始几何、减面版、GLB/FBX/OBJ 和 PBR 贴图保留在 `Meshy/{body,staff,bottle}/downloads/`。
- 本体自动绑骨：24 骨，原始结果在 `Meshy/body_rig/downloads/`，可编辑源在 `Authoring/Witch_Rigged_Candidate_v01.blend`，骨骼 FBX 在 `Delivery/SK_Witch_Meshy_Candidate_v01.fbx`。
- 两件道具：`Authoring/Witch_Staff_Candidate_v01.blend`、`Witch_PoisonBottle_Candidate_v01.blend` 及对应 `Delivery/SM_Witch_*.fbx`。
- 五段定制原始动作：Idle、Walk、CastPoison、ThrowPoisonBottle、DeathBackward，原始 FBX 在 `Meshy/motion_*/downloads/`；可编辑源在 `Authoring/OriginalMotionSources/`。
- 已套到巫婆的待机：`Authoring/Witch_Idle_Candidate_v01.blend` 与 `Delivery/A_Witch_Idle_Candidate_v01.fbx`。
- 五段本地重定向成品：`Authoring/LocalRetarget/Witch_*_LocalRetarget_v01.blend` 与 `Delivery/LocalRetarget/A_Witch_*_LocalRetarget_v01.fbx`。保留本体原网格、UV、蒙皮和 PBR；与云端套用版本分开保存。

| 本地动作 | 时长 | 制作内容 |
|---|---:|---|
| Idle | 2.0 s | 呼吸待机候选，循环末键处理 |
| Walk | 1.1 s | 对应原行走时长，移除水平根位移净漂移，循环末键处理 |
| CastPoison | 1.5 s | 单次左手持杖施法，保留 0.535714 s 发射/音效事件数据 |
| ThrowPoisonBottle | 1.5 s | 单次右手掷瓶，保留 0.666667 s 音效、0.75 s 脱手事件数据 |
| DeathBackward | 1.5 s | 单次后倒，保留骨盆后倒位移 |

120 FPS 烘焙；Blender 时间线标记取最近帧，精确事件秒数以 `motion_plan.json` 为准。事件标记属于制作数据，尚未转为 UE 业务事件，也不表示姿态接触已对齐。

## 云端已完成，剩余下载

五段角色动作的 Meshy 回执均为 `SUCCEEDED`。行走、施法、掷瓶、死亡四段云端原生套用文件的 CDN 下载遇到 TLS 握手中断；原始动作、本体、骨架、道具和待机已保存，不需要重新生成。本地成品已使用这些下载好的源动作重新完成五段重定向与导出。

用户切换代理后，Meshy API/CDN 的 TLS 连接仍被中断，直连超时。因此改用本地制作入口 `local_retarget.py` 继续完成身体动作，骨映射、平移尺度、源片段、输出和事件数据在 `local_retarget_manifest.json`。以后网络恢复时，使用同一个任务 ID 继续 `poll animation_Walk animation_CastPoison animation_ThrowPoisonBottle animation_DeathBackward` 可补存四段云端原生输出。

本轮生成扣费合计 160 积分：三个模型 90，五个原始动作 50，绑骨 5，五次角色动作套用 15。状态读取与下载重试没有重新提交付费任务。

## 后续制作边界

自动绑定的本体有 24 根骨骼，没有独立手指骨；原始动作源含手指通道，但不能直接驱动本体手指。已完成左手法杖、右手毒瓶的骨骼挂接与游戏脱手时序，抓杖、握瓶、松手的手指蒙皮仍需精修。长袍避让与接地尚未精修；瓶子玻璃/液体分材质、共用感染表面 UE 材质实例尚未接入，当前保留生成的独立 PBR。

尚未接入伴生煮锅、毒区致残减速、落点预警、原攻击/落地音效、专用受击动作或地图常驻刷新。F6 已能调用真实角色类；这不等于原项目全部机制迁移完成。造型、动作、命中和布娃娃效果仍由用户测试与判断。
