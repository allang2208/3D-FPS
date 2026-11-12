# 螳螂 ArmChainV15：地面普攻与飞扑臂链候选

**后续状态：普通攻击已按用户要求退回。** 用户反馈普攻仍别扭，要求恢复本轮修改前版本。正式角色、Beast06 对比角色及本 ArmChainV15 对比角色的三个普攻引用均已恢复 ClawV16 并保存。本对比角色的三段飞扑仍保留 ArmChainV15，正式飞扑仍为 PounceV11。后续微调直接从 ClawV16 制作，见 [回退与 ClawV17](D:/FPS3D/FPSGAME/Docs/Monsters/MantisM27ClawRollbackAndV17_20261109.md)。以下五段制作与初次接入说明保留为历史记录，不能视为当前普通攻击引用或用户认可。

2026-11-09。用户明确反馈地面左右普攻和飞扑双镰下劈都存在挥法僵硬、奇怪的问题。本轮将这两类动作一起重做为独立候选，正式角色保留现有引用。此次处理动作结构，不再沿用 V13／V14 仅重排旧刀弧播放时间的方式。

## 制作变化

现有脚本先采样源动作，再用预设镰刀方向反求肩部旋转；这会改变肩部与身体的关系，即使肘部局部轨道保留，也不能据此认定整体发力协调。本版移除这层固定刀弧和左右无限分隔平面，动作主体改由已保存的原生重定向输入驱动。

| 动作 | 本版来源与处理 | 时长 |
|---|---|---:|
| 左普攻 | Beast06 Attack1 原生重定向输入；以螳螂准备姿势作一次局部中立姿势校准，发力段保留完整源旋转变化 | 0.65 秒 |
| 右普攻 | 独立使用 Beast06 Attack6，保留自身身体、肩肘与回收关系 | 0.65 秒 |
| 飞扑蓄力 | PounceV5 保存的 Mutant3 原生重定向输入，恢复躯干、肩带和整臂变化；起手逐渐进入源动作 | 0.60 秒 |
| 飞扑腾空 | 同一来源的完整上身动作，共用源时刻；移除 V6／V11 的分道和固定朝向修正 | 0.65 秒 |
| 飞扑落地 | 沿同一来源继续上身收回，再过渡到原待机姿势 | 0.80 秒 |

飞扑下半身、骨盆轨迹沿用 V11。地面普攻保留非线性秒制时间映射及 0.25–0.30 秒接触窗；源旋转变化在发力段取完整幅度，进入和恢复阶段以整身统一包络衔接准备姿势。地面骨盆位移取源变化的 65%，配合既有脚掌支点、抬跟和原骨长腿部求解。

这些输入是**原生重定向后、螳螂固定刀弧修正前**的保存数据；飞扑的上游仍是 Khaimera／Mutant3 派生动作，不宣称已经换成新的原生螳螂素材。完整来源路径保存在制作清单。

## 刀体与避让

实际骨架中镰刀根是前臂 `lowerarm` 的分支。本版保留该刚性连接、骨长、蒙皮及模型；手部轨道不被当成独立刀腕使用。

避让采用实际刀体顶点和分段包围球，只针对地面、躯干近似胶囊及另一把镰刀的接近情况旋转完整臂链。它允许刀体在身体前方跨过中线，不再强制全刀始终留在各自左右半空间。每侧肩部修正上限 24°，修正连续平滑并在准备姿势端点释放；无目标刀尖位置、无预设逐帧刀刃俯仰曲线、无独立肘腕朝向覆盖。

真实刃面、曲刃鼓出侧和切削侧的带符号坐标，以及避让参数均写入制作清单。该坐标记录不等于已完成切削朝向或穿模验收。此次按用户规则仅制作和接入，不追加离线量化检查、渲染或游戏测试。

## 对比入口与资产

独立候选蓝图：`/Game/Monsters/MantisM27/ArmChainV15/BP_MantisM27_ArmChainReviewV15`。

候选复制正式角色的其他配置，连接全部五段新动作：

| 字段 | 新动画名 |
|---|---|
| `attack_clip`、`left_slash_clip` | `A_M27_LeftSlash_ArmChainV15` |
| `right_slash_clip` | `A_M27_RightSlash_ArmChainV15` |
| `pounce_windup_clip` | `A_M27_PounceWindup_ArmChainV15` |
| `pounce_flight_clip` | `A_M27_PounceFlight_ArmChainV15` |
| `pounce_land_clip` | `A_M27_PounceLand_ArmChainV15` |

动画目录为 `/Game/Monsters/MantisM27/ArmChainV15/Animations`。可将候选蓝图放入自己的测试关卡，比较地面近身攻击与远距飞扑。正式 F6 `MantisM27` 的资产引用不由本轮改写；实际保留引用记录在导入回执中。伤害、命中事件、飞行弹道、恢复门控与 C++ 代码保持原有实现。

源文件和五个 FBX 已导出，五段 UE 动画与独立候选蓝图均已后台导入／保存，commandlet 退出码为 0；保存记录见 [ue_receipt.json](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/ArmChainV15/ue_receipt.json)。本批读取的正式引用仍为左右普攻 Beast06V2、飞扑 PounceV11，未被改写。未进行测试，用户表现确认仍待完成。

## 制作资料

- [可编辑源与导出](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/ArmChainV15/Delivery)
- [制作清单](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/ArmChainV15/Delivery/motion_manifest.json)
- [作者脚本](D:/FPS3D/FPSGAME/Tools/MantisM27/ArmChainV15/author.py)
- [候选导入脚本](D:/FPS3D/FPSGAME/Tools/MantisM27/ArmChainV15/import_candidate.py)

保留 Beast06 和 Epic Paragon Khaimera／Mutant3 的原有来源与许可；派生动作不是 CC0，不发布原始模型或动画二进制。
