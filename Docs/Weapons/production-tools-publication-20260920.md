# 伐木斧与矿镐：发布、恢复及归档

2026-09-20 按用户要求整理本任务、更新技能并发布源码。目录根为 `D:/FPS3D/FPSGAME`，目标为 `https://github.com/allang2208/3D-FPS.git` 的 `main`。共享工作区其他武器、UI、树木生长等修改不属于本次提交。

## 当前功能

- 伐木斧：朝外刃向、左低右高双手持握；H4 装备/待机、整组步态、拇指与腕肘修正；向右后蓄势、快速左下劈砍、命中停住后撬动抽回，镜头单次沉重下顿。
- 矿镐：用户提供的 Rustic Mountaineering GLB，双手待机/装备/奔跑，Sightline4 举顶下砸；命中停住 0.24 秒后撬动拔出；镜头单次下顿，空挥不触发强命中反馈。
- 两者均需在主手槽装备，占用双手，支持右键与拖放装备、G/滚轮切换；不再使用 6/7 从背包直接调出。竖直图标，斧头 1×3、矿镐保持 2×3。
- 低伤害自卫沿用现有公式与防御链，采集与敌人共用接触确认/动作反馈；敌人不会结算材料。斧头查询增加树干表面宽容度，矿镐采矿仍为中心射线。

## 当前资产与作者依赖

| 项目 | 正式路径或作者源 |
| --- | --- |
| 斧头世界网格 | `/Game/Items/ProductionTools/BattleAxe20260919/SM_BattleAxe` |
| 斧头视模、骨架及动画 | `/Game/Items/ProductionTools/GripMotion20260913/` |
| 斧头 Idle / Equip 最终源 | `SourceAssets/AxeThumb20260919/Fixed/Axe_ThumbFix_Idle_Equip_Editable.blend` |
| 斧头 Swing / HitRecover 最终源 | `SourceAssets/AxeRightArm20260919/Axe_RightArm_Editable.blend` |
| 矿镐世界/视模/骨架/动画 | `/Game/Items/ProductionTools/RusticPickaxe20260919/` |
| 矿镐网格及 Idle / Equip 源 | `SourceAssets/RusticPickaxe20260919/RusticPickaxe_Fitted_Master.blend`、`RusticPickaxe_TwoHand_Editable.blend` |
| 矿镐 Swing / HitRecover 最终源 | `SourceAssets/PickaxeSightline20260919/Pickaxe_Sightline_Editable.blend` |
| 竖直图标 | `Content/ColdSteelData/ProductionTools/axe.png`、`pickaxe_upright.png` 及其同名 Texture2D |

斧头制作链保留 BattleAxe 单手网格源、Kimodo H2/H3 接触参数与握姿、H4、攻击 V1–V5 的参考/作者源、ThumbFix、HitPause、RightArm。当前 RightArm 读取 HitPause，后者读取修正拇指的动作，不能把较早目录按名字判为废案。

矿镐链为 `RusticPickaxe → PickaxeOverhead → PickaxeNaturalArms → PickaxeElbowArc → PickaxeSightline`，另依赖斧头 V5 的 `authoring.json` 骨段站点及原单手矿镐/Manny 来源。重建需恢复这些合法本机输入，包括被忽略的完整骨架、抓握和网格采样 JSON。历史文档记录对应阶段；当前入口以本页和最终导入脚本为准。

## 恢复顺序

1. 从合法本机素材恢复上述网格、手臂材质、骨架、贴图及作者输入。用户提供的 Meshy 模型、Manny/Fab 手臂和既有音频不因本次推送获得公开再分发许可。
2. 保留斧头已有视模/骨架，使用 `Tools/Production/import_axe_h4_pose_family.py` 导入最终四条动作；只更新攻击时用 `import_axe_two_hand_attack.py`，两者当前均指向 RightArm 攻击源。旧 `import_axe_hit_pause.py` 是历史局部重定时入口，不覆盖最终 RightArm。
3. 用 `Tools/Production/import_rustic_pickaxe.py` 恢复矿镐网格/基础动作，再用 `import_pickaxe_overhead.py` 覆盖 Sightline4 的 Swing / HitRecover。
4. 图标分别使用 `SourceAssets/AxeImpactInventory20260919/import_upright_icon.py` 和 `SourceAssets/PickaxeEquipment20260919/import_icon.py`，保留公开目录中的占格数据。
5. 构建当前 C++，恢复 `production_tools.json`、`combat-weapon-formulas.json` 和 `axe_impact_motion.json`。矿镐命中重映射在 `ProductionPickaxeImpactMotion.h`，不能仅导动画而遗漏运行时代码。

公开的是源码、作者/导入脚本、动作调参、说明与归档元数据。GLB、Blend、FBX、uasset、图标/贴图、音频和完整骨架采样留在本机；公共仓库不是完整可运行资产备份。

## 归档

70 个替换前备份，约 43.22 MiB，移至 `trash/production-tools-publication-20260920/SourceAssets/` 下的原相对目录。旧 `Before` / `BeforeH2` / `BeforeH3` 文档链接由 [归档清单](production-tools-archive-20260920.json) 定位；清单记录原位置、新位置、大小、SHA-256、理由和保留替代物。全部文件在移动前后核对散列；未删除有效制作链，trash 不公开上传。

## 构建与测试边界

矿镐反馈最初只做 Live Coding，用户重启后加载的旧正式 DLL 不含该补丁。2026-09-20 07:41 已完成正式 Editor 构建（`Saved/BuildEditor/build-20260920-074120.log`，`Result: Succeeded`，16.31 秒）。这证明当时宿主完成编译和链接，不代表公共源码快照已独立恢复资产或通过实机测试。

本次整理仅进行用户授权的归档、Git 差异/发布范围、脚本语法和技能链接检查，未启动 PIE 或追加游戏验收。最终手感交由用户测试。
