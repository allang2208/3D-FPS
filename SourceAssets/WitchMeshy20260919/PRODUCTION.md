# Meshy 制作入口

2026-09-21 已暂停：以下保留原始生成入口与请求说明，不是重新生成授权。复用已下载源，当前状态与废案位置以 `STATUS.md`、`Docs/Monsters/witch-paused-publication-20260921.md` 为准。

继续阶段已准备：本体、木杖和毒瓶各三张独立 PNG 输入，路径见 `Inputs/input_manifest.json`；生成参数见 `meshy_settings.json`，动作意图与原始事件时序见 `motion_plan.json`。

凭据来自进程或 Windows User/Machine 环境变量 `MESHY_API_KEY`；脚本不保存密钥。用户随后提供凭据，本轮通过 `meshy_session.py` 的隐藏输入载入单个生产进程，进程退出即清除，不写入用户或系统环境。

本体、木杖与毒瓶的 Meshy 7.1 三视图生成、自动绑骨、五个定制原始动作及五次角色动作套用均已完成。各 `Meshy/<任务>/task.json` 和 `response.json` 保存任务与成功回执。本地下载和导出状态见 `STATUS.md`。

三件模型和五段原始动作均已生成成功、下载落盘。本体自动绑骨也已完成，返回 24 根骨骼，没有独立手指骨。`Authoring/Witch_Rigged_Candidate_v01.blend` 和 `Delivery/SK_Witch_Meshy_Candidate_v01.fbx` 保留该骨架、UV、蒙皮和材质；抓杖、握瓶、脱手的精细手部变形仍需本地补充，不把身体动作套用成功视为持械接触已完成。

## 运行命令

从本目录运行，使用本机 Python 3.11（已有 requests）：

```powershell
py -3.11 meshy_pipeline.py balance
py -3.11 meshy_pipeline.py submit body staff bottle
py -3.11 meshy_pipeline.py poll body staff bottle
py -3.11 meshy_pipeline.py rig
py -3.11 meshy_pipeline.py poll body_rig
py -3.11 meshy_pipeline.py library
py -3.11 meshy_pipeline.py motion Idle Walk CastPoison ThrowPoisonBottle DeathBackward
py -3.11 meshy_pipeline.py poll motion_Idle motion_Walk motion_CastPoison motion_ThrowPoisonBottle motion_DeathBackward
py -3.11 meshy_pipeline.py animate Idle Walk CastPoison ThrowPoisonBottle DeathBackward
py -3.11 meshy_pipeline.py poll animation_Idle animation_Walk animation_CastPoison animation_ThrowPoisonBottle animation_DeathBackward
```

临时凭据可运行 `py -3.11 meshy_session.py`，隐藏输入后在同一进程输入上述命令的子命令部分，结束时输入 `exit`。不要把密钥写入命令文件。

`poll` 每次读取一次状态，间隔至少 5 秒；成功后立即下载模型、贴图和服务已有的默认缩略图。保存默认产物不代表制作了验收渲染，也不表示已进行视觉检查。`task.json` 存在则复用任务，`request.json` 存在但任务 ID 丢失时停下恢复任务，避免重复付费提交。

图像预处理使用 bundled Python / Pillow 执行 `prepare_inputs.py`，仅裁切、移除边缘连通白底、等比例留白，不重绘造型。拼图尺寸与裁切范围保存在输入清单。

本轮因 CDN 连接中断，使用已落盘的 Meshy Prime 动作和原本体蒙皮完成五段本地重定向。源动作的身体链映射到本体的 24 骨，手指通道保留在干净源文件中。制作脚本读取关节头坐标校正 A/T 参考姿态差，按腿链长度换算骨盆位移，保留后倒轨迹；Idle/Walk 处理末端循环。原网格、UV、骨架父链、权重和 PBR 不变。身体避让与抓握仍未精修。

本轮实际运行的生产命令：

```powershell
& 'E:\Program Files\Blender Foundation\Blender 5.1\blender.exe' --background --python local_retarget.py -- Idle Walk CastPoison ThrowPoisonBottle DeathBackward
```

输出分为 `Authoring/LocalRetarget/` 与 `Delivery/LocalRetarget/`，制作参数见 `local_retarget_manifest.json`。云端带角色动作下载恢复后，可以另存原生套用版本，按 `motion_plan.json` 重定时，不覆盖本地重定向成品：

```powershell
& 'E:\Program Files\Blender Foundation\Blender 5.1\blender.exe' --background --python author_exports.py -- Walk CastPoison ThrowPoisonBottle DeathBackward
```

## 参数来源和阶段边界

- [Meshy 多图生成接口](https://docs.meshy.ai/en/api/multi-image-to-3d)：第一张输入作为正面；本体启用 PBR、4K 基础色、80,000 面目标，保留减面前 GLB，关闭图像增强以减少风格变化。
- [Meshy 绑骨接口](https://docs.meshy.ai/en/api/rigging)：本体完成后以任务 ID 继续；1.9 m 是含尖帽的工作高度。宽袖与长裙的局部权重仍需制作，不能把自动绑骨视为已经完成持械动画适配。
- [Meshy 动画库](https://docs.meshy.ai/en/api/animation-library)：先按原动作意图挑选参考，不根据名称声称动作已匹配。
- [Meshy 文生动作](https://docs.meshy.ai/en/api/text-to-motion)：已生成 2 s 原始候选，并在本地重定向时设置源攻击 1.5 s；发射、脱手事件秒数已保留，手部接触适配仍未制作。

本轮不运行测试、PIE、截图或验收渲染。正式模型、蒙皮、动作和游戏接入的完成状态，以后续实际产物分别记录。
