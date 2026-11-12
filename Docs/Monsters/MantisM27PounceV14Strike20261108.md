# 螳螂飞扑 V14：双镰下劈力度候选

2026-11-09 后续反馈：用户进一步指出地面普攻与飞扑的挥镰方式本身都僵硬。V14 只调整旧刀弧的速度，不能视为解决招式结构。后续 [ArmChainV15](D:/FPS3D/FPSGAME/Docs/Monsters/MantisM27ArmChainV15_20261109.md) 从固定刀弧修正前的原生重定向输入重建五段动作，独立候选交由用户比较，正式版本仍保留。

2026-11-08。用户补充指出，PounceV12 相比旧版的主要退步是「双镰挥击的速度和力度变差」。本次据此将优化范围集中到空中下劈；正式 F6 螳螂继续使用已恢复的 V11，V14 作为独立候选。

## 制作内容

直接读取 PounceV11 的完整密集姿态，保留旧刀弧、完整臂链及真实刃面方向，对 Flight 使用全身共用的非线性时间映射。身体、肩肘腕和腿部沿旧姿态轨迹共同推进，保留原身体与双镰的发力关系。

| Flight 局部时间 | 制作变化 |
|---|---|
| 0.00–0.25 秒 | 沿用 V11 原始进度，保留起跳与最初举镰 |
| 0.25–0.42 秒 | 展开原 0.25–0.34 秒的连续举镰蓄势轨迹，形成更明确的释放准备 |
| 0.42–0.59 秒 | 集中完成原 0.34–0.60 秒的主要下劈；该段源轨迹的播放时间从 0.26 秒压缩到 0.17 秒 |
| 0.59–0.65 秒 | 播放原最后 0.05 秒的切出、制动轨迹，落在 V11 原末帧姿态 |

以上数字是作者时间映射，不是测试得到的刀尖速度或力度提升结果。制作目标是扩大蓄势与快速切入之间的速度对比，并保留原有落地压缩。只导出新的 Flight 动画；Windup 和 Land 直接引用 V11 原 UE 资产。此前 V13 的起势与收势修改仍是另一份候选，没有合并进本版，也没有被用户反馈认定为失败。

Flight 保持 **0.65 秒、60 fps、40 个采样点**，整个动作仍为 0.60 / 0.65 / 0.80 秒。原首尾姿态、骨架、网格和蒙皮保留。角色实际位移与命中仍由既有弹道和服务端 `Landed` 负责，没有提高伤害、修改命中时机或统一播放倍率。

## 对比入口与保存记录

- 正式旧版：F6 螳螂 `MantisM27`，三个飞扑片段均为 V11。
- V14 候选：`/Game/Monsters/MantisM27/PounceV14/BP_MantisM27_PounceReviewV14`。
- 新动画：`/Game/Monsters/MantisM27/PounceV14/Animations/A_M27_PounceFlight_PounceV14`。

候选复制回退后的正式角色配置，仅替换 Flight，左右普攻仍为 Beast06V2。可在内容浏览器找到候选蓝图并放入自己的测试关卡，与正式旧版比较双镰释放的速度和力度。

作者源与 FBX 已后台导出，新的 UE Flight 动画和独立候选蓝图均已导入／保存，commandlet 退出码为 0。保存记录见 [ue_receipt.json](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/PounceV14/ue_receipt.json)。本轮未运行测试、离线验收、渲染、PIE 或游戏，由用户确认表现。

## 制作资料

- [可编辑源与导出](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/PounceV14/Delivery)
- [时间映射与来源记录](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/PounceV14/Delivery/motion_manifest.json)
- [作者脚本](D:/FPS3D/FPSGAME/Tools/MantisM27/PounceV14/author.py)
- [候选导入脚本](D:/FPS3D/FPSGAME/Tools/MantisM27/PounceV14/import_candidate.py)

制作来源仍为本地 V11 的 Epic Paragon Khaimera / Mutant3 派生链，UE-only，不是 CC0。PounceV12 继续作为用户否定的历史方案保留；V14 尚未获得用户认可。
