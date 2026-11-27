---
name: ue5-audio-workflow
description: FPSGAME 音频制作与 Colab Ultra 自动生成入口。用于游戏 SFX、视频同步 Foley、环境循环、BGM 与中英文 NPC 语音的远端生成、48kHz/24-bit 母带化及 UE5 后台导入。
---

# FPSGAME 音频工作流

**第一条（FPSGAME）　文件位置与引用路径。** 从当前工程的[制作目录与功能索引](../../Docs/Production/README.md)和[存储规则第 4.1 节](../../WORKFLOW.md#41-存储分配与文件操作边界)查找对应功能。先确定制作源、正式资产和输出目录，再创建或引入文件。工程 Content 资产用 `/Game/...` 包名引用，制作脚本从工程根或已配置的制作源根解析相对路径。交付时在同一功能条目登记实际位置、引用及备份状态。

共用流程读取仓库发布快照：[ue5-audio-workflow](../_shared/ue5-audio-workflow/SKILL.md)，不要叠加重复镜像。 为什么：共用流程只维护单一来源，避免工程入口与个人维护源漂移。

## 本工程工具与默认边界

- **Colab 服务端与 Notebook**：[colab_audio_worker.ipynb](../../Tools/AudioPipeline/colab_audio_worker.ipynb)（源码 [colab_audio_server.py](../../Tools/AudioPipeline/colab_audio_server.py)，构建器 [build_notebook.py](../../Tools/AudioPipeline/build_notebook.py)）。
- **本地调用与母带/导入链**：[colab_audio_client.py](../../Tools/AudioPipeline/colab_audio_client.py)（默认走代理 `127.0.0.1:7897` + Google Drive `FPSGAME_AudioBridge` 自动发现/队列兜底）、[master_audio.py](../../Tools/AudioPipeline/master_audio.py)、[import_audio_ue.py](../../Tools/AudioPipeline/import_audio_ue.py)、[run_ue_import.ps1](../../Tools/AudioPipeline/run_ue_import.ps1)。
- **领域专项音频规则**：
  - 全界面按钮与栏位交互音效：[ui-audio-feedback.md](../ue5-ui-umg-slate/references/ui-audio-feedback.md)
  - 枪械开火/消音/换弹：[weapon-audio.md](../ue5-weapon-workflow/references/weapon-audio.md)
  - 怪物状态音与循环：[monster-audio.md](../ue5-monster-workflow/references/monster-audio.md)
  - 天气雷声起音与混音：[cloud-lightning-audio.md](../ue5-weather-workflow/references/cloud-lightning-audio.md)
  - 建筑水声与喷泉循环：[fountain-water-audio.md](../ue5-pcg-building/references/fountain-water-audio.md)
- 遵循工程默认规则：后台制作、母带与 `UnrealEditor-Cmd.exe` 无头导入，不主动启动 UE 编辑器、不自动试听或验收；凭证仅留本机用户缓存或环境变量，严禁入库。
