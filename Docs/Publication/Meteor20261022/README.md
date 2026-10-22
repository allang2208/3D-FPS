# 陨星整理与发布 — 2026-10-22

本批覆盖陨星范围/封闭岩体、V4 低矮火场、V5 撞击、准备门控、逐帧地面预览，以及本轮公式/联机复查。只整理本任务的文件与差分，未提交共享工作区的其他战斗、服装、场景等改动。

## 发布范围

- 陨星实体、燃点采样、撞击焦痕、统一资产清单、地面验证和接触点工具直接发布在 `Source/FPSGAME/Skills`。
- `skills.json` 只更新 `meteor` 条目；火系模型只提取等级起点/火场成长，Cook 配置只增加本技能当前目录。共享文件的其他修改留在工作区。
- 当前作者脚本、必要的 V2/V3 制作供体配方、音频加工脚本、说明和对应 SKILL 发布在原路径；`.uasset`、原始音源及 Fab/Epic 来源素材留本地。
- `runtime-integration.patch` 保存 12 个共享接入/检查源码的精确差分或新增文件，基线见 `integration-baseline.json`。包括准备清单、按地形逐帧预览、服务器锁点及原生/真实网络检查入口。

公开主线尚缺完整后台技能准备、已带 CastId 的预约/退款框架和综合检查宿主。这些涉及其他未发布共享功能，原有边界见 [2026-10-15 技能发布](../SkillMagic20261015/README.md) 与 [联机框架发布](../Multiplayer20261014/README.md)。本批没有为发布覆盖这些共享文件，也没有复制它们的全部未提交内容。

**接入补丁不是可以对公共 HEAD 直接执行的一键安装包。** 每个 named-local-prerequisite 要先恢复对应准备/档案/检查框架，并对齐所列 LF SHA-256；补丁中新增的检查文件也依赖该框架。当前完整本机工程已接入，不要再次应用。公开源码和配方不等于完整资源备份或干净检出的完整游戏构建。

## 当前资源和恢复顺序

1. 保留已许可的 `RealisticV3` 岩体/材质、`RealisticV5` 包覆火与尾焰、原爆炸图集与音频、DragonBreathAuthor 宿主及对应插件；其来源与许可沿原工程记录，本批不重新分发。
2. `build_meteor_closed_rock.py` 保存 `MeteorClosedVolumeV1` 封闭岩体。原岩体来自授权扫描资源，模型作者代码可以公开，资源包不随代码推送。
3. `install_advanced_magic_range.py` 中的陨星路径及 `meteor_ground_sources.py` 仍是 V2 供体恢复步骤；它同时涉及其他高级魔法，**不要为重建陨星盲目执行整个安装器**。先恢复原供体资产，再依次使用 `build_meteor_ground_fire_v3.py`、`build_meteor_ground_fire_v4.py`。当前 `build_meteor_ground_volume.py` 转发到 V4。
4. `build_meteor_impact_v5.py` 保存当前爆燃/烟尘，`meteor_scorch_v5.hlsl` 与 `author_meteor_scorch_audio_v5.py` 保存焦痕和音频接入。`prepare_meteor_impact_audio_v5.py` 使用本机原 `SourceAssets/FireMagic20260921/S_MeteorLand.wav` 加工；缺原音源时不能仅凭脚本恢复声音。
5. `build_meteor_surface_preview.py` 保存当前斜坡预览；旧名 `build_meteor_aim_preview.py` 仅转发到当前作者，避免重新生成旧水平投影。运行清单与当前 Cook 目录保持一致。

资源清单见 `asset-dependencies.json`。当前 V4 火场、V5 撞击和新预览均已实际保存在本机；本次整理没有启动 UE 或重复制作、编译、试听、游戏测试。

## 归档

确认退役的阶段备份、旧水平预览作者、被 V5 替代的 V4 爆炸作者、重复构建包装器移入 `trash/meteor-retired-20261022`。`archive-manifest.json` 逐文件记录原路径、目标、大小、SHA-256、原因与替代物，并在移动后读回核对；没有永久删除。

仍被作者依赖的 V2/V3 配方和资产不是废案，保留原处。历史成功/失败日志和回执也保留，便于区分失败尝试、实际保存、构建与运行结果。归档内 Before 快照不应覆盖当前源码。

## 证据与边界

前一轮完整本机整合版：Game/Editor 构建成功、新预览资产保存、80 项原生检查通过；双进程 UDP 主机/客机在每端 60 ms 延迟、3% 丢包下通过。客机陨星获得 14 点命中修炼，主机为 0；重复请求没有重复扣费/实体，迟到实体未重播瞬时爆炸。摘要见 `verification-summary.json` 和 [公式与联机记录](../../Skills/meteor-formula-network-audit-20261022.md)。

启动身体动画加载异常及执行器过早读取修炼的失败尝试保留在本机日志。最终网络运行使用已有身体外观隔离开关、固定隔离档案；不涵盖身体外观加载、完整档案上传/重连、多客机同时在线或画面音效。上述结果不是本次发布后对公共提交重新构建/测试的结果。

本次只进行用户要求的归档读回、暂存范围、文本差异、许可/敏感信息及远端分支核对。推送完成后的 SHA 和远端回读记录写在本机发布回执与交付消息中，避免提交内自引用。
