---
name: ue5-audio-workflow
description: UE5 游戏音频全流程工作流。通过用户 Google Colab Ultra GPU 生成游戏 SFX、视频同步 Foley、环境循环、BGM 与中英文 NPC 语音，落盘候选与溯源记录，并在用户选定后完成 48kHz/24-bit 本地母带化与 UE5 后台 SoundWave/Attenuation/Concurrency 导入。
---

# UE5 音频生成、母带与后台导入工作流

**第一条（FPSGAME）　文件落盘与引用路径。** 在包含 `FPSGAME.uproject` 的当前工作副本，先查[制作目录与功能索引](../../Docs/Production/README.md)与[存储规则第 4.1 节](../../WORKFLOW.md#41-存储分配与文件操作边界)确定制作源、正式资产、批次输出和工作目录。工程 `Content/` 音频使用 `/Game/...` 包名引用；制作脚本相对工程根或已配置的制作源根寻址；候选与母带 WAV 落入 `SourceAssets/<功能>/<批次>/`，导入回执落入 `F:/FPSGAMEData/ArtProduction/<功能>/<批次>/`，交付时在同一功能条目登记来源、正式包与恢复状态。

## 边界与原则

- **遵守全局默认规则**：默认后台生成、母带化、UE5 后台导入与保存；不主动启动 UE 编辑器窗口，不主动试听、跑 PIE 或声称听感已通过，也不跨对话协调。
- **选型权归用户**：AI 生成阶段只产出多候选 WAV 与客观体检指标（时长、峰值、RMS、静音预卷、起音时间、高频占比），**客观指标不代替主观听感验收**；正式母带化与引擎替换以用户选定的候选编号为准（除非用户明确授权直接生成并接入）。
- **凭证绝不入库**：`AUDIO_WORKER_TOKEN`、`HF_TOKEN` 和临时隧道 URL 仅存 Colab Secrets / Google Drive `FPSGAME_AudioBridge/config/token.txt` / 本机 `%LOCALAPPDATA%/FPSGAME/colab_audio.json` 或环境变量，严禁写入仓库、脚本、日志或 Git 提交。
- **许可分离记录**：每批 `provenance.json` 必须记录底层模型 ID、许可协议与种子；开源权重许可与公开再分发权按 `WORKFLOW.md` 第 5 节分别核对，用户参考音/视频素材按原许可继承。

## 引擎路由表（Colab Ultra GPU）

| 音频需求 | 首选 `--engine` | 备用引擎 | 采样率 / 声道 | 适用要点 |
|---|---|---|---|---|
| 武器、近战、技能、交互、怪物、环境 SFX | `mmaudio` | `tangoflux`（需 `diffusers==0.30.3`） / `stable_audio` | 44.1 kHz | 1–30s，MIT；在 Colab Python 3.13 + L4/A100 `bf16` 实测最稳，支持 `--negative-prompt` 与可选 `--ref-video` 动作同步 |
| **动作视频/GIF 同步 Foley** | `mmaudio` | `tangoflux` | 44.1 kHz | 1–30s，MIT；传 `--ref-video` 对齐动画接触时刻，支持 `--negative-prompt` |
| 长环境底噪 / 氛围铺底 | `tangoflux` 或 `stable_audio` | `audioldm2` | 44.1 kHz Stereo | `stable_audio` 最长 47s（需 Colab Secrets `HF_TOKEN`），母带阶段做无缝循环折回 |
| 游戏 BGM / 战斗与城镇配乐 | `acestep` | `musicgen` | 48 kHz Stereo | 5–240s，Apache-2.0；纯器乐留空 `--lyrics`，写明流派、乐器、情绪与 BPM |
| 中 / 英文 NPC 语音对白 | `kokoro` | `f5tts` | 24 kHz Mono | Apache-2.0，自动识别中英文；中文可用 `zf_xiaobei` / `zm_yunxi` 等音色 |
| 指定角色零样本音色克隆 | `f5tts` | `kokoro` | 24 kHz Mono | MIT；传 `--ref-audio`（3–15s 干净人声）与 `--ref-text` 精确转写 |

详细连接架构、参数调优与排障见 [Colab 音频管线参考](references/colab-audio-pipeline.md)。

## 四步标准执行流程

### 1. 检查 Colab 连接状态
- 优先直连 HTTPS 隧道（自动走本机代理 `127.0.0.1:7897`），未命中时通过 `gdrive` 读取 `FPSGAME_AudioBridge/session.json`；隧道不可用自动回退 Google Drive `inbox/outbox` 队列：
  ```powershell
  python Tools/AudioPipeline/colab_audio_client.py health
  ```
- 若返回离线，提示用户在 Colab 打开 `FPSGAME_AudioBridge/colab_audio_worker.ipynb`（或用 `deploy-notebook` 推送最新版本）并点「全部运行」。

### 2. 生成多候选并落盘溯源
- 默认每条需求生成 **4 个候选**（`--num-variants 4`），直接落入 `SourceAssets/<Feature>/<Batch>/Candidates/` 并写入 `provenance.json`：
  ```powershell
  python Tools/AudioPipeline/colab_audio_client.py generate `
    --engine tangoflux `
    --prompt "sharp cold steel blade slash through air with crisp metallic whoosh, dry studio foley, no music" `
    --duration 1.5 --num-variants 4 --seed 101 --prefix slash_whoosh `
    --out-dir SourceAssets/<Feature>/<Batch>
  ```
- 将候选路径和客观指标表汇报给用户试听拍板。

### 3. 本地母带化（48 kHz / 24-bit PCM WAV）
- 用户选定候选后，使用 `Tools/AudioPipeline/master_audio.py` 生成确定性母带到 `SourceAssets/<Feature>/<Batch>/Masters/` 与 `master_manifest.json`：
  - 3D 空间音效：`--preset sfx_spatial`（单声道、45 Hz 高通、裁首尾静音、`-1.5 dBFS` 余量）。
  - 1P 枪声/UI：`--preset sfx_oneshot`（保留立体声、35 Hz 高通、`-1.3 dBFS` 余量）。
  - 无缝环境循环：`--preset ambience_loop`（默认 0.6s 恒功率首尾折回交叠，RMS 控在约 `-18 dBFS`，杜绝硬切接缝爆点）。
  - BGM / 语音：分别用 `--preset bgm` / `--preset voice`。
- 裁切前导静音时保留 `master_manifest.json` 里的 `trimmed_lead_ms`；涉及机械接触点或动画通知时同步核对触发提前量。详细 DSP 与重导规则见 [UE5 母带与后台导入参考](references/ue5-audio-mastering-and-import.md)。

### 4. UE5 后台导入与功能登记
- 编写导入清单 JSON（指定 `sounds`、`attenuations`、`concurrencies`、`force_reimport`），经安全互斥包装脚本在后台运行 `UnrealEditor-Cmd.exe -nullrhi`：
  ```powershell
  powershell -File Tools/AudioPipeline/run_ue_import.ps1 `
    -SpecPath SourceAssets/<Feature>/<Batch>/import_spec.json `
    -ReceiptPath F:/FPSGAMEData/ArtProduction/<Feature>/<Batch>/audio_import_receipt.json
  ```
- 导入完成并核对回执后，在 `Docs/Production/README.md` 对应功能条目登记制作源、正式 `/Game/...` 包路径、回执与备份状态，并如实注明未试听 / 未实机测试。

## 标准实战工作流：从真实参考/选源到联机与性能闭环（2026-11-27 沉淀）

本节沉淀自 SVCh 全套音效、穿心箭发射音、召唤马匹随机口哨与全界面 UI 音效四类实战，作为后续同类音频开发的默认工程标准：

### 1. 先查动画时钟与源码分支，再选音源路线
- **先核对现行代码入口**：开工前查清运行时实际解析路径（如 `LoadAKMSound`、`RifleSuppressedAudioAssets::Bank`、`BowWeaponPrivate::PiercingReleaseSoundPath`）、资产路径大小写（防打包 Pak 大小写敏感）与动作源时钟（如 120 fps 的 `EquipPull`/`EquipRelease`/`MagOut/Insert/Seat`）。
- **按品类选源，不迷信单一生成路线**：
  - **写实枪械 / 机械 / 真人口哨**：优先真实 CC0 1.0 棚录多源分层合成（如 SVCh 组合多款 7.62/步枪 CC0 录音频段，召唤马匹口哨选用 Freesound CC0 1.0 真人口哨）；若 AI 生成候选听感发闷或失真，直接判废并归入 `trash`。
  - **奇幻 / 超音速 / 冲击波技能**：走 **Colab Ultra GPU 分层生成（裂音、空气撕裂、次低频冲击、金属张力）+ 真实基干录音混合**，严格把控 0 ms 瞬态起音（`< 2 ms`）与 `-1.3 ~ -1.5 dBFS` 峰值余量。

### 2. 分层合成、A/B 试听与多变体防疲劳
- 编写确定性合成脚本（`compose_*.py`），同时产出分段 WAV、连续对照试听条 `PREVIEW_*.wav` 及 `manifest.json`（时长、峰值、RMS、来源/许可），交用户试听拍板后再把选定项固化到 `FinalMasters/`。
- 高频或标志性触发声（开火、消音、马蹄、召唤口哨）保留 **3–4 条轻度差异变体**，运行时使用**无相邻重复随机 + 微幅音高偏移（如 `±1.5%`）**。

### 3. 联机音频同步合同（四态全覆盖）
所有可被他人听见的玩法音效必须在 **Standalone / Listen Server / Client / Dedicated Server** 四态核对：
- **Dedicated Server 零加载零播音**：除 `GetNetMode() == NM_DedicatedServer` 与 `IsRunningDedicatedServer()` 外，编辑器内「Dedicated Server PIE」需额外过滤 `UGameInstance::IsDedicatedServerInstance()`。
- **本地 2D + 远端 3D 空间衰减**：
  - 发声者本机用 `2D` 保证零延迟清晰度；远端观察者与 **Listen Server 房主** 用 `3D` 空间衰减。
  - **移动发声源**（如召唤马匹口哨）：服务端校验通过后发 `NetMulticast, Unreliable`（自动受 Actor 网络相关性裁剪），远端使用 `SpawnSoundAttached` 附着在发声角色根组件眼高处，避免奔跑中声音留在原地。
  - **投射物/技能发射声**（如穿心箭 `ABowArrow`）：复用初始复制快照字段（`bHeartPiercingArrow` + `FlightStartServerTime`），在 Listen Server `Configure()` 与远端 `OnRep_Presentation()` 双端触发 3D 衰减音，同时跳过 `Shooter->IsLocallyControlled()`、过滤 `bStuck` 与迟到 `Age > 0.75 s`（防晚入视距或插墙箭重播）。
- **并发与防自叠**：资产级 `USoundConcurrency` 管全局多人并发（如口哨 `MaxCount=3, StopOldest`），单角色记录最近 `UAudioComponent` 并做 40 ms `FadeOut` 防止同玩家连按自叠。

### 4. 打包与性能铁律
- **常驻打包必登记**：凡经 C++ 字符串或 `FSoftObjectPath` 加载的音频目录，**必须**写入 `Config/DefaultGame.ini` 的 `+DirectoriesToAlwaysCook=(Path="/Game/...")`，否则独立打包静音。
- **热路径零同步 `LoadObject`**：UI 音效由 `UGameInstanceSubsystem` 启动预载；角色与技能音频走 `UAssetManager::GetStreamableManager().RequestAsyncLoad`（配合 `PlayerSkillAssets::Gather` 预热），仅在冷启动极早期保留同步兜底。
- **高帧率输入零冗余遍历**：全局 UI 音效拦截器在局内无光标战斗态必须 O(1) 快返，绝不在开火/瞄准点击时遍历 HUD Slate 树（详见 [UI 音效反馈规范](../../ue5-ui-umg-slate/references/ui-audio-feedback.md)）。

### 5. 收尾清理与 Git 边界
- 用户确认并完成导入后，将未选候选、`PREVIEW_*.wav`、废弃 AI 草案、检测截图/GIF、只读回读 dump 与 `__pycache__` 移入 `trash/<task>/`，并在隔离目录外（`F:/FPSGAMEData/ArtProduction/<功能>/<批次>/cleanup-manifest.json`）记录逐文件原路径、目标、大小、SHA-256 与保留替代物。
- 原位保留：`compose_*.py` 配方、`FinalMasters/`、重建所需的最小原始音源、`LICENSE_CC0.txt` / `provenance.json` 与导入回执。
- Git 公开推送严格遵守 `WORKFLOW.md` 第 5、8 节：按精确路径暂存源码、配置、工具、文档与 SKILL，不夹带未核准再分发二进制或并行会话脏索引。

## 领域专项衔接

具体游戏玩法挂载、网络复制与动画时序继续遵守各领域参考，不另建冲突规范：
- UI 全界面按钮与栏位音效：[ui-audio-feedback.md](../../ue5-ui-umg-slate/references/ui-audio-feedback.md)
- 枪械开火/消音/换弹预卷与去噪：[weapon-audio.md](../ue5-weapon-workflow/references/weapon-audio.md)
- 怪物状态边沿、声部预算与循环：[monster-audio.md](../ue5-monster-workflow/references/monster-audio.md)
- 天气雷声起音与压低混音：[cloud-lightning-audio.md](../ue5-weather-workflow/references/cloud-lightning-audio.md)
- 喷泉与连续水声：[fountain-water-audio.md](../ue5-pcg-building/references/fountain-water-audio.md)
