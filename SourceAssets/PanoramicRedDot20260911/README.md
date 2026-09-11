# 薄边框全景红点

**当前游戏版本：** [GameIntegration](GameIntegration/README.md)。基于 Reroll03 修整，15,894 三角面、2K 材质图集、独立镜片与红点；底座按用户要求收窄至 25 mm，保留宽镜框。以下为生成阶段的历史记录。

Reroll02 的已否定试验已移入本机 trash/optic-workflow-20260911，清单见 Docs/Weapons/optic-archive-20260911.json。Reroll03 为当前作者脚本的真实输入，保留原位。

**最新复抽（用户否定首次形变后）：** [Reroll03](Reroll03/README.md) 为当前较好的生成候选，采用修正的单视角实心浅灰参考与去背景输入。大凹洞及整体形变明显减少，但按钮/旋钮位置仍有推断偏差，尚未接入。下文为首轮历史记录。

## 首轮历史结果

2026-09-11 服务重启后，原回执恢复执行成功，耗时 420.509 秒。原始 GLB 6199534 三角面，2K 带贴图母版 93387 三角面；下载散列已与远端核对。`panoramic_red_dot_clean.glb` / `.fbx` 与 `panoramic_red_dot_clean_editable.blend` 是后处理候选，74493 三角面。原始输出均保留。

实际渲染确认薄框开窗完整；`clean_candidate.py` 切除生成背景底板，去除包括假红点在内的游离碎片，用本地石墨常量材质检查形体。没有以其他建模方法替换 5080 主体。底座仍有明显孔洞、融化表面和软化边缘，未达到游戏资产精修要求。未制作功能镜片/准星，未校准真实安装尺寸，未接入游戏。

清理预览 `panoramic_red_dot_clean_beauty.png`，正/背/侧视图为同前缀对应图片；生成原貌 `panoramic_red_dot_high_beauty.png`。最终状态、限制和散列见 `job_status.json`，几何统计见 `cleanup_report.json`。下一步是按已定三视图修整底座硬表面，而不是将此候选直接登记为合格游戏资源。

授权阶段：参考三角洲行动全景红点设计三视图，再通过 RTX 5080 生成模型。尚未接入游戏。

参考外形：https://sjz.jbskins.com/Item/detail/id/1204.html 。`reference_delta.png` 是该页游戏道具参考图，版权属于原权利人，仅作本地参考，不作为生成模型贴图。概念图由内置 image_gen 生成，`panoramic_red_dot_three_views.png` 为前/右/后视图；并非模型投影或测绘。

设计：宽圆角视窗、薄上沿和两侧立柱、较厚下缘、低矮开放式底座，深石墨色阳极氧化金属。保持大体轮廓，简化为原创薄框设计，无品牌文字。微透镜和红点在模型阶段另行检查，不把生成贴图红点直接当作游戏瞄准功能。

5080 入口 `pipeline.py`，本机节点信息 `nodes.json`，硬件 `hardware.json`；三个视图由 ImageCrop 分别送入 front/right/back，多视角 TRELLIS.2-4B，1024_cascade，16/32/24 步，seed 91143，2K 贴图、10 万面目标母版，并保存原始几何。实际面数和视窗质量以输出读回为准。

回执 `panoramic_red_dot_high_submitted.json`；重复执行 submit 时返回既有回执。不得重复提交或中断其他任务。生成完成后保存 history、GLB、SHA-256、实际模型渲染及可编辑 Blend。薄壁、视窗封堵和玻璃需要检查；未完成部分明确记录。

`finish_job.py` 是本次回执的单次后处理进程：等待最多两小时，成功后下载并渲染，不重复提交、不取消任务。状态见 `job_status.json`，错误见 `finish_stderr.log`。`generated_pending_visual_review` 表示模型与预览落盘，尚需人工检查，并非游戏接入成功。超时或退出后先读既有 history 再续处理。
