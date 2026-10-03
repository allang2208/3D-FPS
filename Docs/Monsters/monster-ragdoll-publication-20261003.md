# 怪物布娃娃与飞扑修订整理发布

2026-10-03 用户授权：本对话废案移入 trash，更新对应 SKILL，检查仓库整理和推送规则后发布到 `https://github.com/allang2208/3D-FPS.git`。从本机唯一开发仓库 `D:/FPS3D/FPSGAME` 精确发布，目标为 `origin/main`，普通非强制推送。

## 本次保留的成果

- 共用 `MonsterRagdollPhysics`：真实刚体读取、连续速度交接、交接初期八帧限速、根缩放链和停止物理前完整快照。标准仰卧／俯卧起身动画继续使用，快照转换到恢复后的网格坐标。
- 巫婆：死亡／击倒使用同骨架的连体 CorpseFollow，脚与裙身共同移动；行走恢复原活体模型与布料，末端长袍范围约束解决移动穿裙。尸体保留真实求解器姿势；法杖在交接时脱手、继承手部速度并使用覆盖完整杖身的简单碰撞自然落地。
- 推广：人形保留标准起身；毒蛆、手脑、犬类保留各自死亡资产；巨手另建连体死亡 Physics Asset。非人形活体击倒和物种起身没有新增。
- 性能：百目纳入现有共享预算；死亡定姿后退出角色、战斗、移动、网格与布料 Tick；已有多 LOD 尸体使用共享 0.5 秒调度，仅层级变化时刷新完整快照。独立法杖仍是独立物理道具。
- 枪械：不增加默认硬直，按真实命中位置叠加有界的局部骨骼回弹；不改变伤害／控制／攻击时钟。魔法局部反馈、冻结尸体再次受击与布娃娃网络复制不在已完成范围。
- 突变体：V3 起跳／空中翻掌、V4 落地腕轨、V5 蓄力六条臂腕轨分层保留，不重写其他身体轨道。

F6 显示名为“巫婆”，稳定 ID `WitchRebuilt`、原类和资源路径保留。用户已认可巫婆移动、倒地和死亡；其他怪物推广与性能改动只完成制作、构建和保存。突变体起跳和空中掌向获用户确认，V4 落地和 V5 蓄力没有后续认可，不能将它们当作已通过动作模板。

## 废案归档

归档位于 `trash/monster-ragdoll-retired-20261003/`，共 **115 个文件、103,356,541 字节（约 98.57 MiB）**。逐文件记录原路径、目标、大小、SHA-256、退役原因和替代物；移动前确认源／目标都在本工程授权目录内，移动后逐文件读回散列一致。清单在归档目录的 `archive-manifest.json`，本机发布记录副本在 `SourceAssets/MonsterRagdollPublication20261003/archive-manifest.json`。

归档包括本轮已经被当前实现替代的 Before 源码／资产快照、突变体首版 PalmDown 制作包、V2 旧安装与单次保存入口、覆盖前动画包、Blender 自动备份和一个空构建输出。历史文档中的 Before／before_content 保留其当时路径；追溯应使用归档清单。

没有按版本号清理所有旧源：V2 的制作源仍由 V3 读取，V3 的源仍由 V4 读取，V4 的源仍由 V5 读取。有效 Blend、FBX、作者配方、正式 Content、许可及成功构建回执保留原位置；当前重建不读取 trash。

## 本机恢复顺序

1. 恢复已有合法模型／骨架、原动画和 Physics Asset，以及 `/Game/Monsters/HumanoidKnockdown` 的标准动作。沿用 `Docs/AssetSetup.md` 的其他内容依赖。
2. 巫婆从 `SourceAssets/WitchRebuilt20260921/Authoring/WitchRebuilt_Master.blend` 保留活体；`SourceAssets/WitchCorpseFollow20261002/author_corpse_mesh.py` 与 `import_corpse_mesh.py` 制作／保存独立连体身体。按 `save_surface_sampling.py` 保存尸体 CPU 表面访问，供动画回退接地读取。
3. 使用已纠正的 `SourceAssets/WitchStaffDrop20261002/prepare_staff_physics.py`，由 `WitchPhysicalSettle20261003/prepare_staff_collision.py` 复用；旧骷髅限定碰撞不可恢复为现版。运行内容为 `/Game/Monsters/WitchRebuilt/Props/SM_WitchRebuilt_StaffPhysics`。
4. 百目恢复 `/Game/Monsters/HundredEyedSlag/RagdollGroundV17/PA_HundredEyedSlag_Ground_V17`；实际根来自网格参考骨架。保存关节限制需同步 PhysicsConstraintTemplate 的 DefaultProfile，不能只改 DefaultInstance。
5. 巨手通过 `SourceAssets/MonsterRagdollStandard20261003/prepare_hand_corpse.py` 保存 `/Game/Monsters/FleshHand/PA_FleshHand_Corpse`，保留原活体查询资产和专用起身片段。
6. 突变体从干净 `pounce_arm_refine` 源继续 V2 author → V3 author → V4 author → V5 author；安装 V3 后只覆盖 V4 落地、V5 蓄力。生产动画分别为 `A_Mutant3_PounceFlight`、`A_Mutant3_PounceLand`、`A_Mutant3_PounceWindup`。V2 仅是作者输入，旧方向安装入口已退役。

作者脚本需要本机保留的骨架、原模型／Blend、FBX 与密集动画采样。仅 Git checkout 不具备完整制作或游戏运行内容；导入脚本公开不代表克隆后资产已存在。

## 来源与公开边界

ALS-Refactored 参考固定为 `b754d6f0f2bb03741d301f8fb88077ebfe561e17`；保留 `SourceAssets/MonsterRagdollCore20261002/provenance.json`、原 `Reference/AlsCharacter_Actions.cpp` 与 `Docs/ThirdParty/ALS-Refactored-LICENSE.md` 的 MIT 许可。这里只适配物理读取和限速方法，没有安装整套 ALS 角色系统或其多人布娃娃复制。

公开本轮运行源码、原创脚本、专题说明与对应 SKILL。Meshy／Epic／第三方模型和动作、原材质、密集采样姿势、UE／FBX／Blend 包、构建二进制、日志、传输回执及 trash 均留本机，沿用已有来源记录，未新增二进制公开许可。

共享文件精确提取本轮内容：F6 只改巫婆显示名，枪弹结算只接局部回弹，怪物文件排除并行 State／受击网络复制、击杀技能通知与新 M-10 功能。为前次构建修复的 M-10 参数命名保留在本机，本次不发布整套新怪物。工作区与其他任务未提交／暂存修改保留。

## 构建与本次推送检查

沿用此前普通构建及真实保存记录：最新 Game 为 `Saved/BuildGame/monster-ragdoll-performance-20261003-104048.log`，Succeeded，82.72 秒；Editor 为 `Saved/BuildEditor/build-20261003-104952.log`，Succeeded，2.14 秒，当时标准模块已为最新状态。巨手死亡物理和巫婆法杖／身体已实际保存，详细收据见对应制作目录。

本次只执行授权的整理、发布差异／大小／敏感信息／许可检查、`git diff --cached --check` 与远端回读。没有重跑构建、启动 UE／游戏、截图、渲染、运行测试或性能采样；此前共享完整工程的构建结果不等于本次公开源码子集单独构建通过。

暂存文件清单、差异审查及推送 SHA／远端回读记录保存在本机 `SourceAssets/MonsterRagdollPublication20261003/`。遵守 `WORKFLOW.md` 第 4、5、7、8 节与 `skills/ue5-auto-assistant/references/parallel-repo-publish.md`，保留已有 Godot 归档标签。
