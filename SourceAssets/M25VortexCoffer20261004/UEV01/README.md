# M-25 涡电匣：UE 待机与蠕动接入

资产目录：/Game/Monsters/VortexCofferM25
F6 条目：涡电匣 M-25（VortexCofferM25）

## 本次制作

- 使用 RigV01 的完整原始高模、147 骨骼、已有四权重蒙皮，未减面。
- Idle：4 秒循环；蠕动：2.8 秒原地循环。
- 原生 UM25AnimInstance 混合两条动作，0.25 秒切换；按实际平面速度 / 16 cm/s 推进蠕动相位。
- 原生 AVortexCofferM25 复用共享 CharacterMovement 与 MonsterAIController/BT_Monster。
- 支持感知目标、追踪、停止和返回出生处。当前为移动阶段，关闭伤害，未制作攻击、受击、死亡及闪电特效。
- 复用已安装的大体型导航规格：半径 225 cm、高 450 cm、台阶 30 cm。F6 需要相应导航与足够开阔的地面。
- PBR 使用原始 BaseColor、MetallicRoughness（G 粗糙度/B 金属度）、OpenGL Normal（导入翻转绿通道）。

## 生产文件与状态

- import_m25.py：导入网格、骨架、材质、两条动画并保存 AI/怪物蓝图。
- ue_asset_receipt.json：每一步实际保存结果；只有 stage=assets_saved 才表示完整资产接入。
- build_editor_20261004.log / build_game_20261004.log：Editor 与 Game 两个目标均 Result: Succeeded；未运行游戏。
- BeforeIntegration：本任务修改共享文件之前的快照，仅供定向恢复本任务改动；不要整份回写覆盖其他任务修改。
- 未运行 PIE、自动测试、截图或渲染验收。由用户进行游戏内测试。

2026-10-04，用户关闭已有编辑器后，后台 commandlet 已完成并正常退出（exit 0）。ue_asset_receipt.json 的 stage=assets_saved，共保存 10 项资产。首次 PIE 占用导致的保存失败已经解除。

## 已保存资源

- /Game/Monsters/VortexCofferM25/BP_VortexCofferM25
- /Game/Monsters/VortexCofferM25/BP_M25AIController
- /Game/Monsters/VortexCofferM25/SK_M25_VortexCoffer
- /Game/Monsters/VortexCofferM25/SK_M25_VortexCoffer_Skeleton
- /Game/Monsters/VortexCofferM25/Animations/A_M25_Idle
- /Game/Monsters/VortexCofferM25/Animations/A_M25_Crawl_InPlace
- /Game/Monsters/VortexCofferM25/Materials/M_M25_MeshySurface
- /Game/Monsters/VortexCofferM25/Textures/T_M25_BaseColor
- /Game/Monsters/VortexCofferM25/Textures/T_M25_MetallicRoughness
- /Game/Monsters/VortexCofferM25/Textures/T_M25_Normal

FBX 导入保留全部 6,524,740 三角形；源 147 骨骼另加 FBX 容器节点，UE 导入为 148 节点。按导入后的身体前后骨方向将网格旋转 -90°，使口部朝角色 +X。两段动作的 root 局部缩放与绑定相同，无需根单位修正。

模型仍为完整高模，未制作 LOD 或执行性能测试。用户自行打开工程后，可在有大体型导航和足够空间的位置，通过 F6 的怪物生成列表选“涡电匣 M-25”。本次没有启动交互编辑器或游戏进行验收。

2026-10-05 整理：上文旧备份已移入仓库根 trash/m25-retired-20261005 的同阶段相对目录；逐文件映射见 Docs/AssetArchives/m25-retired-20261005.json。生产源与当前资源保留。
