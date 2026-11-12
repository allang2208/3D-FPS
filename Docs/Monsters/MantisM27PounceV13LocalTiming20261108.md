# 螳螂飞扑：恢复 V11 与 V13 局部节奏候选

后续定位：用户补充反馈，V12 的主要问题是双镰挥击的速度和力度。本版仅涉及起势和末段收势，另行制作的 [V14 双镰下劈候选](D:/FPS3D/FPSGAME/Docs/Monsters/MantisM27PounceV14Strike20261108.md) 针对空中释放节奏。两者独立保留，正式角色继续使用 V11；该反馈不代表用户否定了 V13。

2026-11-08。用户检查后认为新的 PounceV12 不如旧版，要求先退回再重新优化。本轮先恢复正式飞扑，再从 PounceV11 的密集原始姿态制作独立候选。全程后台制作、导入与保存；没有运行测试、离线验收、渲染、PIE 或游戏。

## 正式回退

正式 `/Game/Monsters/MantisM27/BP_MantisM27` 和原 `/Game/Monsters/MantisM27/Beast06V1/BP_MantisM27_Beast06ReviewV1` 的三个飞扑字段都已恢复 PounceV11 并保存。仅按 V12 接入回执恢复这三个字段，左右普攻保持 Beast06V2，其他配置随现存蓝图保留。F6 稳定 ID 仍为 `MantisM27`。

回退保存记录：[rollback_to_v11_receipt.json](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/PounceV12/rollback_to_v11_receipt.json)。PounceV12 的源文件和资产保留为历史记录，文档已标记用户否定。

## 本次重新制作范围

V13 直接读取 `PounceV11/Delivery/MantisM27_PounceV11.blend`，保留完整的逐帧姿态轨迹、整条臂链和带符号的实际刃面方向。八阶段继续用于标记动作片段，运动轨迹以 V11 为基础。此次结合此前计划中的起势与收势速度调整，只做两个局部变化：

| 片段 | 修改范围 | 制作目标 |
|---|---|---|
| Windup | 0.00–0.26 秒 | 原前 0.06 秒的姿态展开到新前 0.12 秒，随后平缓追上原进度，0.26 秒以后沿用旧节奏；减缓开始时的突然抬镰 |
| Flight | 全段复用 V11 原 UE 资产 | 保留旧版腾空举镰、收腿与下劈动作，以及原速度 |
| Land | 0.48–0.80 秒 | 原触地和深蹲缓冲保持，后段较快开始回收、末尾减速收住，调整回防的缓急 |

每个片段内的全部骨骼共用同一条非线性时间映射。位置和缩放在原密集帧之间采样，旋转采用同半球四元数插值；没有重新构造稀疏姿势、重做腿部 IK 或混入供体整体骨盆升降。前后端点仍使用 V11 原始姿态。本次是局部节奏候选，不包含原诊断中两处切段脚位差的全面重建。

时长保持 **0.60 / 0.65 / 0.80 秒**、60 fps；运行时仍使用原弹道、实际落地事件及 0.25 秒恢复逻辑。模型、骨架、蒙皮和游戏代码保留。

## 用户对比入口

- 正式旧版：F6 螳螂 `MantisM27`，飞扑为 V11。
- 新候选蓝图：`/Game/Monsters/MantisM27/PounceV13/BP_MantisM27_PounceReviewV13`。

候选从回退后的正式蓝图复制，只替换 Windup 和 Land，Flight 直接引用 V11。因此候选继承正式角色的待机、移动、普攻和其他战斗配置，便于比较本次局部改动。可以在内容浏览器找到该蓝图并放入自己的测试关卡。已生成的旧实例可能继续持有此前引用，需要重新生成角色查看保存后的默认动作。

本轮不替换正式角色的 V11。V13 的可编辑源和两个 FBX 已导出，两个 UE 动画与独立候选蓝图均已后台导入／保存，commandlet 退出码为 0，保存记录见 [ue_receipt.json](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/PounceV13/ue_receipt.json)。导入保存不代表动作自然度已经通过检查，实际表现由用户确认。

## 制作资料

- [可编辑源与导出](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/PounceV13/Delivery)
- [制作参数](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/PounceV13/Delivery/motion_manifest.json)
- [作者脚本](D:/FPS3D/FPSGAME/Tools/MantisM27/PounceV13/author.py)
- [候选导入脚本](D:/FPS3D/FPSGAME/Tools/MantisM27/PounceV13/import_candidate.py)

来源沿用 V11 的本地 Epic Paragon Khaimera / Mutant3 派生链，许可仍为 UE-only，不是 CC0。此记录没有将候选标记为用户认可的成功模板。
