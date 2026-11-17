# 本轮特效、弓阴影与丘陵夜袭发布记录（2026-11-17）

目标：allang2208/3D-FPS 的 main；基线 34c08285d0675e1038e94800464c68c06c149178。本次按 WORKFLOW 第 4、6、7、8 节和当前个人发布参考执行。宿主有其他任务的暂存内容及共享文件差分，因此在 Saved/ConversationVFXHillsPublish20261117 的临时隔离索引发布；不修改宿主分支、共享索引或其他任务源文件。临时目录完成后移入 trash。

## 当前交付

- 陨石：V6 岩体包覆焰和连续尾迹；V7 路径保存火球供体爆燃与 revision 2 延长翻滚；保留径向冲击波、火星、岩体和 V4 低矮残火。恢复顺序和倍率见 Docs/Skills/meteor-fireball-impact-20261115.md。
- 暴风雪：用户选定 B / ChargedV3 区域云，近手云保持 RollingV1；室内寒气与去除规则霜面、冰锥触地碎裂保留。共享路径表资产数为 16。
- 高地长弓：各槽仅处理直接渲染子件，隐藏备用圆柱不能开启隐藏投影；不改变配件或数值。
- 丘陵：门址地形过滤、失败重选和刷怪等待分流；神像接近/接触表面、地面寻路进展恢复、不同体型导航、M08 表面节点绕障、M09 顶面连通；丘陵两条开发生成入口都排除悬钟，地牢保留。
- 联机：区域特效不依赖客户端施法者 Pawn 先进入相关范围，地面查询改用技能 Actor 上下文，冷加载尾迹从当前岩体续接；换敌导航继续匹配实际体型。服务器伤害、数值与刷怪权威不变。

## 发布边界

Source 下直接提交本轮可独立裁剪的陨石、暴风雪和弓改动，以及用户曾要求 GIF 时使用的可复用 commandlet 源码；制作配方、HLSL、烘焙和显式捕获工具在 Tools。不会自动执行捕获工具。

丘陵宿主及多人基础存在尚未公开的依赖，并且若干文件被其他任务共同编辑。本轮 24 个精确集成补丁在 Integration，记录改前副本 SHA-256 和本轮重放结果；不把其他任务的完整宿主文件作为新增源码发布。TemperateHillsStreaming 仅发布 HillsGround 标签这一块，排除了同期白崖/湖泊修改。PlayerSkillAssets 的独立补丁把预加载循环 15 改为共享 AssetCount，所需预加载宿主尚未在公开树中；补丁前置为对应 ZoneAssetPaths 循环，不代表完整预加载系统已公开。不要无条件把集成补丁叠加到已经修改完成的本机宿主。

这次提交是限定范围的源码/配方发布，完整本机工程与公开子集仍有差别；既有 HillsMultiplayer20261115、UnknownHumanoid20261116 等发布记录也保留各自依赖边界。未额外构建公开子集。

## 资产与制作源

asset-dependencies.json 记录 35 件当前本机使用资产的路径、大小和 SHA-256；资产文件仍在 Content 联接指向的 F:/FPSGAMEData/Content，未上传 UE 二进制或第三方授权素材。Mantaflow 缓存、blend、图集、参考素材、fireball-donor.json 和 rock-flame-surface.json 是有效制作源，仍保留原位置，不因版本目录旧而退役。工具恢复还需要这些本机输入及原火球/冰锥/云供体。

## 归档

本轮最初归档清单为 2847 个文件、1498801549 字节。实际结果以 cleanup-manifest.json 与 cleanup-summary.json 为准。每项记录原路径、trash 目标、字节数、SHA-256、退役原因及替代物；移动前核对范围，移动后逐文件读回。

trash/ConversationVFXHills20261117 保留诊断日志、截图、GIF、对比帧、隔离预览工程、旧资产/源码/DLL 副本和废案脚本。旧爆燃体积方案、已被 B 版取代的云恢复入口已退役，当前配方留在 Tools。当前资产、制作输入、游戏存档、主工程编译产物和其他任务目录未移动。HillsNightRaid20261115 与 HillsNightRepair20261114 作者资料属于原始夜袭依赖，继续保留。

历史文档中的 Saved 或 SourceAssets 证据路径可能已移到上述 trash 的同相对路径；小型有效保存/交付回执另保存在 Evidence，避免依赖临时目录。历史候选回执不等于当前方案，也不代表本轮重新运行测试。

## 构建与验收状态

本机 FPSGAME / FPSGAMEEditor Win64 Development 已在前一轮完成后台构建；最终 receipt 见 Evidence/Saved/ConversationNetworkAudit20261117/delivery.json，源码散列与构建时间依据保留在同目录。Editor 复用了同一宿主已完成的共享构建，Game 队列返回成功。原始完整日志可从 trash 对应目录取回。

本轮整理仅做用户授权的发布范围、差异、体积、敏感信息、许可、归档读回和远端读回核对。没有启动 UE、PIE、游戏、截图、渲染或新增玩法/联机测试。画面和联机实机效果由用户验收。

## SKILL

对应参考更新覆盖：meteor-ground-impact、blizzard-migration、m-series-locomotion、multiplayer-lifecycle-and-coverage，并发布本轮已有的 first-person-bow-parts 阴影经验；个人维护源与工程镜像均保留。没有更新跨会话记忆文件。
