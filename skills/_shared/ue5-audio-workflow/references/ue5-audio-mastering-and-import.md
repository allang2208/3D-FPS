# UE5 本地音频母带化与后台导入参考

## 1. 格式与母带预设规范

UE5 正式母带统一保存为 **48 kHz / 24-bit PCM WAV**，源文件与母带分别存放在 `SourceAssets/<Feature>/<Batch>/Candidates/` 和 `Masters/`，不覆盖原始生成候选。

| 预设名 | 声道 | 高通 | 裁首尾静音 | 无缝循环折回 | 目标 RMS / 峰值上限 | 典型用途 |
|---|---|---|---|---|---|---|
| `sfx_spatial` | Mono | 45 Hz | 是 | 否 | -16 dBFS / -1.5 dBFS | 3D 空间音效（脚步、马蹄、怪物、环境点声源、受击、门） |
| `sfx_oneshot` | Stereo | 35 Hz | 是 | 否 | -14 dBFS / -1.3 dBFS | 第一人称武器/技能主声、2D UI 提示音 |
| `ambience_loop` | Stereo | 35 Hz | 否 | 0.60 s 恒功率 | -18 dBFS / -3.0 dBFS | 风雨、林雾、火堆、怪物氛围底噪循环 |
| `bgm` | Stereo | 28 Hz | 否 | 按需开启 | -16 dBFS / -1.5 dBFS | 场景/战斗配乐 |
| `voice` | Mono | 80 Hz | 是 | 否 | -16 dBFS / -1.5 dBFS | NPC 3D 空间语音、系统旁白 |

### 批处理母带清单示例 (`master_spec.json`)

```json
{
  "manifest_out": "master_manifest.json",
  "items": [
    {
      "name": "SW_ShadowStep_Dash_01",
      "preset": "sfx_oneshot",
      "input": "Candidates/slash_whoosh_01_s101.wav",
      "output": "Masters/SW_ShadowStep_Dash_01.wav",
      "dsp": { "highpass_hz": 40.0, "max_duration_sec": 1.2 }
    },
    {
      "name": "SW_ForestWind_Loop",
      "preset": "ambience_loop",
      "input": "Candidates/wind_02_s202.wav",
      "output": "Masters/SW_ForestWind_Loop.wav",
      "dsp": { "loop_crossfade_sec": 0.8 }
    }
  ]
}
```

运行命令：
```powershell
python Tools/AudioPipeline/master_audio.py --spec SourceAssets/<Feature>/<Batch>/master_spec.json
```

### 关键音频工程纪律（汇总自项目历史案例）
- **3D 空间衰减必须单声道**：双声道源在 UE 空间化下容易丢失方位感；近身世界声源一律用 `sfx_spatial`（Mono）。
- **循环声严禁硬切**：`ambience_loop` 通过尾部折回头部 + 正弦/余弦恒功率交叉淡化（≥0.5s）消除接缝爆点，整体 RMS 压低到约 `-18 dBFS`（~0.125）避免盖住战斗提示。
- **接触声预卷对齐**：`master_audio.py` 输出 `trimmed_lead_ms`；若保留自然起音预卷用于枪械机械/脚步动作，触发端按真实秒数提前 `LeadSeconds`（参考 `weapon-audio.md`）。
- **多变体防听觉疲劳**：高频触发音效（枪声、脚步、挥砍、马蹄）建议制作 3–4 条轻度差异变体，运行端避免相邻重复并限制随机音高幅度（固定接触点整段音频不随机 pitch）。

## 2. UE5 后台导入清单示例 (`import_spec.json`)

```json
{
  "attenuations": {
    "melee_3d": {
      "destination_path": "/Game/Audio/Shared",
      "name": "ATT_Melee_Default",
      "attenuate": true,
      "spatialize": true,
      "inner_radius": 150.0,
      "falloff_distance": 2400.0
    }
  },
  "concurrencies": {
    "melee_limit": {
      "destination_path": "/Game/Audio/Shared",
      "name": "CON_Melee_Default",
      "max_count": 6,
      "limit_to_owner": true,
      "resolution_rule": "STOP_OLDEST"
    }
  },
  "sounds": [
    {
      "wav_path": "SourceAssets/<Feature>/<Batch>/Masters/SW_ShadowStep_Dash_01.wav",
      "destination_path": "/Game/Skills/ShadowStep/Audio",
      "asset_name": "SW_ShadowStep_Dash_01",
      "looping": false,
      "volume": 1.0,
      "compression_quality": 85,
      "loading_behavior": "FORCE_INLINE",
      "attenuation": "melee_3d",
      "concurrency": "melee_limit",
      "force_reimport": true,
      "source_provenance": "SourceAssets/<Feature>/<Batch>/provenance.json"
    }
  ]
}
```

执行后台导入（不打开 UE 编辑器界面，自动遵守 `Local\CodexUeMcp-Port-8000` 互斥锁）：
```powershell
powershell -File Tools/AudioPipeline/run_ue_import.ps1 `
  -SpecPath SourceAssets/<Feature>/<Batch>/import_spec.json `
  -ReceiptPath F:/FPSGAMEData/ArtProduction/<Feature>/<Batch>/audio_import_receipt.json
```

### 导入与加载行为约定
- 短单发 SFX（≤3s）：`FORCE_INLINE`（零流式起音延迟）。
- 中长 SFX / 环境循环（3–20s）：`RETAIN_ON_LOAD`（首块驻留、尾段流式）。
- 长 BGM（>20s）：`LOAD_ON_DEMAND`。
- 覆盖自有旧资产时开启 `"force_reimport": true`，避免导入器静默跳过旧 SoundWave（但绝不开启在非本任务拥有的共享资产上）。
- 若涉及新增 C++ 强引用或 `ConstructorHelpers` 绑定，**先完成 SoundWave 导入并保存，再编译 `FPSGAMEEditor`**，避免 CDO 构造期产生 miss 警告。
