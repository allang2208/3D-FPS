# Colab Ultra 音频生成管线参考

## 双通道架构（HTTP 隧道优先 + Google Drive 兜底）

```text
用户下达音频需求
  └─> 本地 Tools/AudioPipeline/colab_audio_client.py
        ├─[主通道] 经代理 127.0.0.1:7897 直连 Cloudflare Quick Tunnel -> Colab FastAPI (端口 8765)
        │          (URL 与 Bearer Token 自动从 Drive FPSGAME_AudioBridge/session.json & config/token.txt 同步)
        └─[兜底通道] 若隧道掉线/不可达 -> 经 gdrive CLI 写 inbox/<job_id>.json -> Colab 后台线程执行 -> outbox/<job_id>/ 拉回本地
```

- **本机私有缓存**：`%LOCALAPPDATA%/FPSGAME/colab_audio.json` 保存最近同步的隧道地址、Drive 根目录 ID 和 Token，位于工程之外，永不入库。
- **Colab Ultra 显存策略**：服务端按显存自动设置常驻模型上限（A100 80GB 留 4 个、A100 40GB 留 3 个、L4 24GB 留 2 个、T4 16GB 留 1 个），超额时按 LRU 自动卸载并清理显存；Ampere/Hopper 架构默认启用 TF32 与 `bfloat16`。

## 首次部署与日常启动

1. **推送 Notebook 到 Google Drive**（只需首次或更新服务端代码后执行）：
   ```powershell
   python Tools/AudioPipeline/build_notebook.py
   python Tools/AudioPipeline/colab_audio_client.py deploy-notebook
   ```
   输出 JSON 中的 `colab_url` 可直接在浏览器打开。
2. **Colab 端一键运行**：
   - 运行时选择 **GPU（A100 / H100 / L4）**，Ultra 会员可开启「后台执行」。
   - 点 **全部运行 (Run all)**。约 1–2 分钟内完成依赖安装、模型预热并写入 `MyDrive/FPSGAME_AudioBridge/session.json`。
   - 如需使用门控模型 `stable_audio`（`stabilityai/stable-audio-open-1.0`），在 Colab 左侧钥匙图标 **Secrets** 新增 `HF_TOKEN`。
3. **本机确认连通**：
   ```powershell
   python Tools/AudioPipeline/colab_audio_client.py sync-session
   python Tools/AudioPipeline/colab_audio_client.py health
   ```

## 各场景提示词与参数建议

### 1. 游戏 SFX（`tangoflux`）
- 用**英文物理材质 + 触发方式 + 声学环境 + 干湿约束**描述，避免抽象情绪词。
- 示例：
  - 近战挥砍：`"heavy curved steel blade slicing rapidly through air, crisp metallic whoosh, dry close-mic foley, single hit, no music"`（`--duration 1.5 --steps 50`）
  - 枪械机械：`"--duration 1.0"` + `"tight crisp metallic rifle bolt carrier snap click, close dry mechanical foley, studio recording, no reverb, no background noise"`
  - 技能释放：`"--duration 3.0"` + `"dark arcane shadow dash burst with low sub-bass thump and sharp crystalline wind tail, game combat sfx, no music"`
- 建议每次 `--num-variants 4`（seed 自动递增），优先挑 `lead_silence_ms` 短、瞬态清晰、无多余底噪的候选。

### 2. 动画视频同步配音（`mmaudio`）
- 直接复用 `F:/FPSGAMEData/ArtReviews/.../*.mp4` 或录屏片段：
  ```powershell
  python Tools/AudioPipeline/colab_audio_client.py generate `
    --engine mmaudio `
    --ref-video F:/FPSGAMEData/ArtReviews/<Feature>/<Batch>/preview.mp4 `
    --prompt "heavy warhorse galloping on packed dirt road, crisp hooves impact" `
    --negative-prompt "music, speech, singing, wind noise, distortion" `
    --duration 6.0 --num-variants 3 --steps 25 `
    --out-dir SourceAssets/<Feature>/<Batch>
  ```

### 3. 背景音乐 BGM（`acestep` / `musicgen`）
- 游戏配乐优先纯器乐（`--lyrics ""`），明确**流派、主奏乐器、情绪、速度 BPM、无演唱**：
  ```powershell
  python Tools/AudioPipeline/colab_audio_client.py generate `
    --engine acestep `
    --prompt "dark medieval fantasy village exploration soundtrack, solo acoustic lute, soft cello drone, subtle distant wind, melancholic calm, 76 bpm, instrumental, no vocals" `
    --duration 45 --num-variants 2 --steps 32 `
    --out-dir SourceAssets/<Feature>/<Batch>
  ```

### 4. NPC 语音（`kokoro` / `f5tts`）
- 快速中文/英文对白（`kokoro`）：
  - 中文女声：`zf_xiaobei`、`zf_xiaoni`、`zf_xiaoxiao`、`zf_xiaoyi`
  - 中文男声：`zm_yunjian`、`zm_yunxi`、`zm_yunxia`、`zm_yunyang`
  - 英文：`af_heart`、`am_adam`、`bf_emma`、`bm_george`
  ```powershell
  python Tools/AudioPipeline/colab_audio_client.py generate `
    --engine kokoro --voice zm_yunxi --lang-code z --speed 0.95 `
    --prompt "东门外的林道最近不太平，牵好你的马，天黑前务必回城。" `
    --num-variants 2 --out-dir SourceAssets/<Feature>/<Batch>
  ```
- 指定音色克隆（`f5tts`，需先在 Colab Cell 2 勾选 `INSTALL_F5TTS`）：
  ```powershell
  python Tools/AudioPipeline/colab_audio_client.py generate `
    --engine f5tts `
    --ref-audio SourceAssets/<Feature>/VoiceRef/speaker_clean.wav `
    --ref-text "参考录音的逐字原句文本" `
    --prompt "目标台词文本" `
    --num-variants 3 --out-dir SourceAssets/<Feature>/<Batch>
  ```

## 常见故障处理

- **隧道 502 / 连接超时**：运行 `colab_audio_client.py sync-session` 拉取自动重连后的新隧道地址；若仍失败，直接加 `--transport drive` 走 Drive 队列。
- **本机代理未生效**：检查 `127.0.0.1:7897` 是否开启，或显式传 `--proxy http://127.0.0.1:7897`。
- **Colab 显存不足**：先调 `colab_audio_client.py preload unload` 释放已驻留引擎，再提交新任务。
- **未安装某引擎**：先跑 `colab_audio_client.py engines` 查看 `installed: true` 列表；或改用零额外依赖的兜底引擎（SFX 用 `audioldm2`，BGM 用 `musicgen`）。
