# 人形控制与皮肤巨手：仓库整理和发布

2026-09-27，发布宿主 `D:/FPS3D/FPSGAME`，授权目标 `https://github.com/allang2208/3D-FPS.git` 的 `main`。当前分支名为 `cursor/highland-blade-seat`，开始整理时其 HEAD 与 `origin/main` 相同；不为发布切换或重置共享分支。

## 本机当前成果

- 人形击飞/起身、世界级布娃娃预算、死亡交接修正、眩晕和动态硬直：见 [击飞](humanoid-knockdown-20260926.md)、[死亡交接](humanoid-ragdoll-handoff-fix-20260926.md)、[眩晕](humanoid-stun-20260926.md)、[控制区分](stagger-stun-separation-20260926.md)。已有资产保存及正式构建记录，视觉、玩法和多怪帧率未验收。
- 绿色皮肤巨手/小手：沿用 Meshy 模型、本地手骨架和掌面 +Y 的作者约定；UE 掌心朝 Actor +X。基础动作、LOD、移动、冲锋、提前量、专用击飞和起身、状态/奖励/刷怪入口均在本机接入。最终入口见 [集成](FleshHandIntegration20260927.md) 和 [作者链](../../SourceAssets/FleshHand20260926/README.md)。
- 当前大手已取消掌心副拳攻击和拍击召唤小手。移动速度为大手 259.2、小手 324 cm/s，动作参考速度单独保留。马赛克材质与根骨接地修正分别见 [冲锋表现](FleshHandChargeVisual20260927.md)、[接地修复](FleshHandGroundingRepair20260927.md)。
- 小手低位近战：120 cm、60° 前方范围，突刺 30°，按当前瞄准、不锁定目标；移动阻挡与近战受击查询分开，保留遮挡和每刀去重。[具体参数与构建记录](../Weapons/small-hand-melee-range-20260927.md)。正式 Editor 构建记录为 `Saved/BuildEditor/build-20260927-144839.log`，未游戏测试。

## 归档

90 个文件、269.13 MiB 已移动到本机 `trash/monster-hands-20260927/`。逐文件原路径、目标、大小、SHA-256、理由和替代入口见 [归档清单](monster-hands-retired-20260927.json)；移动后散列全部一致，trash 内也保留清单。

范围是本对话的旧朝向、冲锋/接地修复前快照、自动 Blender 备份、已完成的一次性编辑器操作脚本，以及被绿色连续皮肤路线替代的虫群迁移草案。存活制作器的备份出口同步指向 trash，避免重跑时再把回退副本堆入制作入口。

保留当前 Blend/FBX/LOD、原 Meshy 输入与回执、重定向中间源、关键失败测量、许可、作者脚本和实际保存的 UE 内容。Hammer / PalmFist 历史导出仍被完整作者/导入链读取，保留为重建输入；当前蓝图已解除攻击引用，不能仅因玩法取消就删除制作依赖。清理未触碰其他任务或正在运行的编辑器。

## 公开范围与待发布运行接口

本批公开作者/导入脚本、HLSL、来源和恢复说明、归档清单、SKILL，以及独立的 `MonsterReactionTiming.h`。个人技能与工程技能中本次新增内容同步；原有不同的后台规则文本和其他任务路由保留。

**当前工作区的完整运行行为尚不能从这次公开提交单独重建。** 共享 `MonsterCombatComponent` 混有其他任务的韧性形式/抗性接口；护士、胖子和武器组件混有未发布的移动、战斗公式及武器状态改动。按精确提交规则，这些共享文件保持本机未提交，不把它们整文件夹带发布，也没有将索引内容写回工作区。

本对话新增的 13 份运行源码另存为 [新增文件交接补丁](Publication20260927/new-runtime-sources.patch)，逐文件散列和接口缺口见 [交接清单](Publication20260927/runtime-handoff.json)。它位于 Docs，**不参与公开树的 UBT 编译，也不是完整接入补丁**；现有本机源码不移动。补丁保留大/小手、冲锋表现、手型/人形击飞、布娃娃预算、眩晕和小手近战查询的本机实现，供依赖接口完成各自审查发布后接续。

后续还需精确接入共享战斗、护士/胖子动画生命周期、剑/快速近战、F6、图鉴/数值以及具体技能击飞入口；不在当前完整宿主直接应用新增文件补丁，不用公共 main 覆盖本机工程。此次保留缺口不改变本机已保存资产和已构建 DLL。

## 资源与重建顺序

- 本地恢复 `SourceAssets/FleshHand20260926/References`、`Meshy`、`LocalRig`、`Animations`、`Charge`、`Knockdown`、`Locomotion`、`UEInputs` 和已保存的 `Content/Monsters/FleshHand`。基础动画应含 `RootLocalSupport20260927V1` 接地修正；最终移动为 `WalkWeighted/WalkScurry`。
- 恢复本机已合法取得的共享感染皮肤母材质、原攻击音源、Mesh2Motion 源动作、目标人形网格/绑定与 IK 重定向输入。人形制作脚本在 `Tools/HumanoidKnockdown`、`Tools/HumanoidStun`，拟合输入和导入收据在对应 `SourceAssets`。
- FleshHand 按 README 的制作链恢复，再运行完整 `install_ue.py`；现有资产的定向接地/材质修复分别使用 `install_basic_grounding.py`、`repair_charge_air_material.py`。这些调用需要上述本机完整运行类及合法素材，脚本不等于资产已恢复。
- Mesh2Motion 源动作的 CC0 不覆盖目标蒙皮、其他素材或 Meshy 账户产物；Meshy 账户许可等级未核定，不公开模型、PBR、Blend/FBX、UE 包和密集几何/权重/动作数据。密钥仅通过环境变量读取；服务回执、下载链接和生产日志不提交。

本轮只做获授权的发布检查：差异、引用/依赖范围、文本与脚本语法、敏感信息与大文件、归档散列和远端 SHA 回读。没有重新构建、导入、启动 UE、运行游戏或做视觉/性能验收。上述构建和资产记录来自制作阶段。

暂存范围为 71 个精确路径；36 份 Python、3 份 JSON 语法检查通过，两项 SKILL 元数据检查通过。没有提交二进制、超过 1 MiB 的文件或检测到的凭据/签名下载链接；本轮新增的 Markdown 导航均可在公开索引解析。`AssetSetup.md` 原有三条暗纹弓外观链接指向尚未发布的文档，属于原基线缺口，本次保持不变。完整检查记录保存在本机 `Saved/monster-hands-publish/review.json`。
