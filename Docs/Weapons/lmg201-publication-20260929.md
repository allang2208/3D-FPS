# 201 废案整理、制作源码与经验发布

2026-09-29，按用户授权整理本条 201 制作线并向 `allang2208/3D-FPS` 的 main 发布。原模型正式否定，当前重新生成模型保留。入口：[原模型废案](../Rejected/lmg201-original-model-20260929.md)、[当前制作说明](../../SourceAssets/LMG20120260927/README.md)。

## 本次归档

962 个文件、22,020,397,535 字节移入本机 `trash/lmg201-rejected-20260929`，包括首轮原始模型、被取代的模型/动作尝试、失败的 D35 盖体输出，以及 116 个无外部包引用的 UE 退役资源。逐项 SHA-256 移动后读回一致。50 个仍有外部引用的候选资源保留；其它武器和并行任务没有清理。

- [完整移动记录](lmg201-publication-20260929/archive-manifest.json)
- [包引用与保留理由](lmg201-publication-20260929/archive-references.json)
- [实际执行摘要](lmg201-publication-20260929/archive-summary.json)

引用读取通过后台 commandlet 完成。随后用户关闭重新打开的 UE，归档在互斥批次内执行。没有启动 GUI、运行游戏或对模型做新一轮视觉验收。

## 当前运行与恢复依赖

| 内容 | 保留入口 |
| --- | --- |
| 新主体与盖内壁 | Cover10 主体包；Repair36 完整 FBX、盖体 Blend；Detail35 加厚前代码/Work/贴图 |
| 机瞄 | Production20260927 的 FrontSight/RearSight，使用新几何和 Repair36 材质 |
| 布料弹箱 | ClothFeed33 分件与五类两条换弹；Repair36 骨骼用途布料材质 |
| 原装弹匣、常规动作 | Magazine24 两条换弹，BeltFeed08 基础动作 |
| 配件、天气 | Accessories22 及其 wet-material 目录；Material21 当前绑定表 |
| 手臂、服装 | 项目原生 Manny/Infima/V7，ADS34 的 LMG201 专属链甲绑定 |
| 声音 | FireAudio01；当前项目 PKM 声音资源直接引用。此前尾音争议不在本轮重新试听或判定解决 |

旧文件夹名不能作为清理依据。原金属弹箱已退役，后来用户重新要求的新布袋方案保留。Skin07、ArmSprint06、PKMFK19、Video26 的部分制作快照是输入依赖，含旧枪壳不表示允许整体恢复。当前作者链从这些已捕获的输入继续；若要重建更早的废案，按散列清单另行恢复前驱，不将 trash 作为现用自动加载目录。

## Git 边界

本次发布归档工具和记录、当前新模型的选定作者脚本/说明，以及两个枪械 SKILL 章节。脚本中的米制坐标是游戏美术适配数据，不是实物加工图纸。公开仓库仍是源码子集，不能仅靠克隆重建完整 201 资产。

模型、纹理、动画、SoundWave/uasset、密集顶点/骨骼 JSON、NPZ、视频、音频、Meshy 下载回执、日志和 trash 均不上传。原参考是用户提供的照片、游戏截图/视频；动作与配件复用项目现有 Manny/Infima/Fab 来源。允许 Git 推送不等于获得这些原素材的公开再分发许可。

共享运行时中还有角色换弹拆文件、其它武器和枪匠等并行未提交修改。本次不把这些整文件夹带发布，也不将本次整理称为所有在制功能的源码发布或公共仓库独立构建通过。当前本机模型、运行逻辑与配置不因归档而改写。

## 经验沉淀

- [生成枪械近景精修](../../skills/ue5-weapon-workflow/references/generated-rifle-refinement.md)：薄壳等厚补偿尖刺、原皮有限厚度修复、废案与现用依赖边界。
- [枪械材质](../../skills/ue5-weapon-workflow/references/weapon-finish.md)：静态布料转骨骼用途、局部涂层采样、法线单次绿通道转换。

个人技能和项目镜像仅同步这些新段落，保留其它主题的并行差异。Repair36 的历史定向几何/绑定读回不等于用户认可外观；本轮只执行用户要求的整理与推送检查，未做游戏、声音或性能测试。
