# RSH-12 暂停、归档与源码发布

2026-10-03 用户要求暂停制作、记录待办、将废案移入 trash，并授权向 `https://github.com/allang2208/3D-FPS.git` 普通推送。本轮仅整理和发布，不继续动画制作或资产接入，不新增游戏测试。

## 当前状态

RSH-12 已有五发容量、12.7 毫米弹药、单持／双持／法杖副手、715 动作共享及专用单动开火的接入源码。弹巢部件与子弹入座、开火 REST → POSE 修复已有各自实际资产保存记录。

最新握持和 ADS 拨锤仍是未完成修订：静态候选已导出，最新动作源码尚未完整烘焙；Grip 回执只记录初版十个资产，没有最新 `registered-mechanical-axes-v3-full-skin` revision。当前 UE 资产与最新制作源不一致。详细边界见 [握持与拨锤现场](rsh12-grip-cock-fix-20261003.md)，恢复顺序见 [待办](../Backlog.md)。

## 本机保留与废案归档

131 个废案文件（88,010,065 字节）已移入 `trash/rsh12-pause-20261003/`：过时开火导出／profile、被后续拟合取代的日志与接触结果、旧候选截图和失败的桥接／导入尝试。每项记录原路径、归档路径、大小、SHA-256、退役原因和保留替代物，移动后按原散列读回。公共清单为 `SourceAssets/RSH12Publication20261003/archive-manifest.json`；实际内容与完整清单保留本机 trash。

保留原始 Sketchfab 包与官方元数据、完整 715 供体、`RSH12Grip20261003/native_*.json`、原始拟合基准 `BeforeAuthored/Integration`、当前静态源与接触合同，以及各次 `BeforeAssets`／`BeforeSource` 回滚资料。它们仍是重制／恢复输入，不能仅凭旧日期或 Before 名称清走。具体清单见 `retained-recovery-dependencies.json`。

过时单动动画已归档，当前 `RSH12SingleAction20261003/{single,r,l}` 中的导入文件需要先重制。不要直接运行最新导入脚本，也不要用旧的 `complete` 回执跳过重制。

## 公开源码与恢复边界

公开精确选择的 RSH 制作脚本、参数、武器定义、运行接入片段、目录数据、署名、待办和技能经验。共享文件按代码片段或 RSH 数据对象暂存，保留其他任务的工作区修改；不把仓库整体脏文件作为本任务提交。

模型来源：[Rsh-12 by Medji](https://sketchfab.com/3d-models/rsh-12-177cd570002d4e89bd378ec328a47f9c)，[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。完整署名在本机 `Content/ColdSteelData/Licenses/RSH12-Medji-CCBY4.txt`，并以公开说明保留。视频 [BV1pj411e7Jw](https://www.bilibili.com/video/BV1pj411e7Jw/) 的 1:42–1:44 仅作动作参考，原视频／截图不公开。

本轮不公开 UE 包、Blender／FBX、贴图、视频、密集几何／蒙皮／姿态、下载认证、临时签名地址、构建／桥接日志或 trash 内容。公开源码需要本机合法 715／V7 手臂与对应素材才能重制，不等于可直接运行的完整工程。发布清单与源散列见 `published-files.json`。

## 沉淀内容

武器技能记录真实膛孔入座、机构绑定帧和共享动作边界；手臂技能记录 POSE 烘焙、完整混合蒙皮接触、原始绝对拟合与 ADS 源时钟。具体候选偏移、未完成的拇指路线和离线残差不作为已通过的动作标准。个人技能与工程镜像同步本次新增内容。
