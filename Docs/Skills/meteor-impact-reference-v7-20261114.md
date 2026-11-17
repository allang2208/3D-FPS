# 陨星撞击 Reference V7

**后续反馈：用户认为几乎没有改善，V7 未获认可。** 2026-11-14 后续排查发现火焰有效帧只有前约 10 帧，旧火冠却按火焰与烟共用的 64 帧序列播放，导致实际火焰约 74 ms 后消失。当前同路径资产修复说明见 `meteor-impact-visibility-repair-20261114.md`，下文时间为最初制作配置，不能作为修复后的实际观感依据。

用户已否定 V6 的撞地效果；V6 的后台保存与构建成功不代表观感合格。本轮范围仅为撞击爆炸与冲击，目标按用户给出的参考重新制作，保留岩体及已有碎块、V6 包覆焰/尾迹、V4 低矮残火、焦痕、声音、镜头和玩法数值。

## 直接观察的参考

[用户提供的视频](https://www.bilibili.com/video/BV1ZEWj6qE8S/)及其[原作者版本](https://www.youtube.com/watch?v=peHi4w1SKEA)。本轮实际取得公开播放副本，提取 231.0–232.6 秒的 METEOR 分层片段及 444.7–445.5 秒的 AI VIDEO 陨星片段；没有把火球片段或右侧 GPT PICTURES 当作目标。

参考可见的结构：撞地白热亮芯、明显的白金色径向放射、连贯火冠向外撑开、岩块/小火星抛出、余火与烟。V6 原实现缺少独立的径向冲击表现，几团同类火焰也没有构成整体爆燃。本次以这些差异为制作依据。视频展示包含慢放及多枚陨星，不能把视频播放秒数直接当作单次技能物理时长。

本地 `SourceAssets/MeteorImpactReferenceV7_20261114/Reference` 只供参考分析，不导入游戏、不加入 Cook。游戏贴图来自原创 Mantaflow 烘焙，不从视频抠取场景像素。

## 重制内容

- 85 ms 集中接触亮芯，叠加约 200 ms 的白金色径向放射扇面；放射与离体火星分别控制。
- 一个初始连通的燃烧体，加九个短促向外/向上的燃料脉冲；50 ms 后停止供燃。使用 128 格最长轴、60 fps、96 帧的原始场，导出 64 帧图集。整段统一裁切和归一化，避免旧图集大幅留白缩小有效火焰。
- 白热核心持续约 220 ms，完整火冠约 820 ms。0.34 秒的不规则贴地压力前缘随后散开，不形成持久发光圆环。
- 24 条高温径向碎屑、16 颗冷却余烬使用弹道与独立衰减；已有岩体碎块照常呈现。
- 十团低矮尘浪与六团冷却余烟，共享现有 16 粒烟尘预算；湿命中关闭尘浪。装饰粒子随现有 DetailReduction 缩减。
- 单次最多 61 粒，不新增灯、Actor Tick、碰撞查询或实时流体网格。粒子数是制作配置，不是性能实测。

运行目录为 `/Game/Skills/FireMagic20260921/MeteorImpactReferenceV7`，唯一系统 `NS_MeteorPressureV7`。仅切换 `MeteorAssets.h` 的 Impact 路径和新增 Cook 目录；准备与播放继续使用同一清单。其余运行字段不变。

## 生产与恢复

1. Blender 后台运行 `Tools/Fluids/bake_meteor_pressure_v7.py`；`--export-only` 可复用缓存。
2. `Tools/Skills/run_meteor_reference_v7.ps1` 等待生产图集完成，通过既有 DragonBreathAuthor commandlet 导入、编译并保存。
3. `install_meteor_reference_v7.py` 在完整资产回执后按字段接入，原文件留在本次生产目录的 `Before`。
4. `build_meteor_reference_v7.ps1` 等待已有原生构建/输出占用结束，执行 Game 与 Editor 常规构建。不会停止其他进程或启动交互编辑器。

重建旧版本后最后执行 V7 接入，避免旧工具把 Impact 引用切回 V6。保留旧资产和源文件。

资产实际保存看生产目录 `asset-receipt.json`，引用切换看 `integration-receipt.json`，构建与最终落盘状态看 `delivery.json`。未运行 UE 界面、游戏、预览或验收测试，不能称“100% 视觉一致”；还原效果由用户自行查看。
