# 201 弹箱换弹、枪体与配件资料补充发布（2026-10-01）

本轮在 `D:/FPS3D/FPSGAME` 的 `main` 整理，目标远端为 `https://github.com/allang2208/3D-FPS.git`。读取 AGENTS、WORKFLOW 第 8 节及枪械发布规则后，仅处理 201；其他会话的源码、配置和暂存内容保留。

## 已在远端与本次补充

开始整理时，本地 HEAD 与 origin/main 同为 `655d45066af158778008bbe39849cc33ea4f6a90`，没有未推送提交。

- `790f71b3` 已包含 201 布箱换弹路径、普通/空仓时间映射、弹链进弹与阻尼等运行时接入。
- `655d4506` 已包含 ClothReload44 的制作说明、PKM/201 ArmHinge55 左臂修正和 GripLayer56 接触层，以及 SupportFingers59 失败回撤记录。
- 本次补充此前被忽略的 ClothReload44 作者配方、BeltFit53 弹链补丁、枪体/材质/大弹鼓/接头/图标/后握把修订配方及其保留依赖、细节制作记录和 SKILL。没有重新导入动作或修改游戏代码。

## 当前恢复顺序与边界

| 范围 | 当前入口 | 保留条件 |
| --- | --- | --- |
| 枪体及表面 | [总入口](../../SourceAssets/LMG20120260927/README.md)、SurfaceFinish50，H56 去提把，F57 修供弹入口 | 正式主体仍为 Cover10 包名；后续局部修改从当前保存网格重新采集 |
| 布箱换弹 | [ClothReload44](../../SourceAssets/LMG20120260927/ClothReload44/README.md)，五类握把 × 普通/空仓，共十条 | 44.4b 的时间映射、B53 弹链补丁及后续 ArmHinge55 都必须保留 |
| 左臂 | [ArmHinge55 修正](pkm-201-arm-hinge-20260930.md) | 只改左臂七根骨轨道；不能用旧整段 Tracks 覆盖当前包 |
| 运行时回握 | [GripLayer56](grip-layer56-20260930.md) | 保留操作接触段；不要重新应用已回撤的 SupportFingers59 |
| 弹药袋、弹链 | ClothTop45、BeltFit53、Motion55 弹链参数、FeedMouth57 | 子弹/链片/布料分区；袋内及机匣内端点、换弹显隐保持同一时钟 |
| 大弹鼓 | Drum46、DrumJoint47 | 路径仍在 Drum46；当前接口已替换复制的原厂弹匣上段 |
| 三款改装后握把 | [RearGripRestore58](../../SourceAssets/LMG20120260927/RearGripRestore58/README.md) | 从原始母版恢复；现用原 pivot、材质槽和 UV 通道合同不变 |

ClothReload44 的源 Tracks 早于 ArmHinge55。需要重制时，应先读取当前资产与骨骼，再制作 44.4b/合并 B53，按 ArmHinge55 的现用采集和局部写回流程叠加七根左臂轨道。导入器中的历史 SHA/Before 回执来自当时现场，不能跨版本直接作为当前目标。目录编号表示沿革，不是可以批量执行的安装顺序。保留的旧导入器与诊断脚本是追溯资料，不能覆盖已保存的完整装配。

R58 三款后握把已后台保存，仍有近零切线/副法线构建提示；本次未修改几何或重新处理这些提示。资产保存不代表用户已认可表面、抓握或换弹表现。

## 废案与保留依赖

本次 86 个文件、237,155,101 字节移到本机 `trash/lmg201-publication-20261001/`，移动前后逐文件 SHA-256 一致。含已否决 H54/M55 提把方案 61 个文件、ClothReload44 一次性文本补丁 20 个、具有正式可编辑源的 Blender 自动备份 4 个，以及无法读取的旧 R38 说明 1 个（原文件全为 NUL 字节，已重建恢复入口）。详情为 [归档计划](lmg201-publication-20261001/archive-plan.json) 与 [实际清单](lmg201-publication-20261001/archive-manifest.json)。原目录保留迁移说明，未删除任何正式 Content 资产。

- SupportFingers59 已由先前会话完整回撤并归档，本次不重复移动。参见 [失败记录](lmg201-support-fingers59-20260930.md)。
- G43/J44 旧握把不作为最终几何，但 J44 的接颈函数、F50 的材质及 R58 定位所需历史输入仍保留。FitFinish37 的盖体被否决，仍被引用的制作函数/涂层不能整目录移走。
- ClothReload44 `Before_v1/v2/v3` 是恢复与回执引用，ArmHinge55 与 B53 的采集输入是当前局部补丁依据，继续本机保留。
- 先前已清理的原枪体与旧动画不重复归档；旧说明中的 ClothFeed33 整包回退命令不再作为当前入口。

## 公开范围

仅发布作者 Python/PowerShell、Markdown、SKILL 与路径/散列清单。模型、PBR、图标、视频、音频、Blender/FBX/UE 二进制、Manny/Infima 动作及密集轨道/网格快照都留在本机。原始后握把模型、PKM/V7 供体、参考视频等必须从已有合法来源恢复；可用于游戏不等于允许把源资产公开。

脚本中的 `D:/FPS3D/FPSGAME`、UE/Blender 安装目录及个人视频位置是作者宿主路径，其他机器先替换。`.gitignore` 白名单只开放选定配方，不能用强制添加把整个 SourceAssets/Content 上传。完整公共源码与完整可运行内容不同，参见 [资产恢复说明](../AssetSetup.md)。

本轮只做用户要求的仓库整理、发布内容检查和归档散列读回；没有编译、启动 UE、运行游戏、渲染或进行动作验收，由用户实测。
