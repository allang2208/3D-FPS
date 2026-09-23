# PKM fire (imported from the original gamedev prototype)

用户指定：把原 `game-dev` 原型里的 PKM 开火声导入当前 UE5 工程，替换现在 PKM 用的开火声。
之后又做了两轮：先修"阶段不连续"，再提升质感。

## 来源

- 源文件：`E:/无尽轮回/长期备份/2026-7-13-1/game-dev/assets/sounds/weapons/pkm_half_sec.wav`
- 原型内唯一用途就是 PKM 的开火声，六处引用一致（`data/audio-config.json`、`src/config/gun-ammo.js`、
  `src/config/weapon-fx-config.js`、`src/world/defense-system.js`、
  `src/ui/equip-data-manager.js` 的 `PKM_ITEM.fireSound`、`src/entities/player/update.js`）。
  过热/蒸汽音是另一个文件 `pkm_ammo_steam_mixed.wav`，不参与开火声。
- 逐字节原样保留为 `S_PKM_Fire.raw.wav`（SHA-256 见 `provenance.json`）。
- 权利：沿用原型仓库的原始录音权利，未建立公开再分发许可；仅本机工程内使用。

## 源文件的实测问题（这是加工的起因）

| 项 | 实测 |
| --- | --- |
| 容器 / 编码 | RIFF WAVE，PCM 16-bit |
| 声道 / 采样率 | 1 / 44100 Hz |
| 容器时长 | 0.5000 s |
| **实际有声段** | **仅 64 ms（50.0 – 114.3 ms）** |
| 前导静音 | 50 ms 数字静音 |
| 收尾 | 从约 −12 dBFS **直接砍到数字零**（硬截断） |
| 有声段 RMS | −6.46 dBFS（AKM 参考为 −15.48 dBFS） |
| 频段倾斜 | 40–315 Hz 仅 18.9%，630–5000 Hz 高达 55.0%（AKM 为 59.9% / 16.7%） |
| 波形峰值时点 | 10 ms（AKM 为 20 ms），能量集中在一个早尖峰 |

三个后果：前导静音让每发延后 50 ms；没有衰减尾，650 发/分（92.3 ms）的间隔里留 27 ms 硬静音，
听感一顿一顿；硬截断本身是爆音。而"整文件 RMS"被静音稀释，掩盖了它其实比参考亮而薄。

## 加工链（`author_audio.py`，可复现、结果确定）

1. 按静音边界裁掉前导静音与硬截断，保留完整瞬态；不动音高与时长。
2. 修正 EQ：从 PKM 原始倾斜朝 AKM 参考移动 60%（保留 PKM 自身性格）。
   40–80 Hz 不动——那在参考里是房间隆隆而不是枪声。曲线见 `authoring.json` 的 `corrective_eq`。
3. 重建 85 ms 尾音：主爆音自身分四段零相位滤波，低频长鸣（τ 110 ms）、中频中等、机械细节快收，
   复现 AKM"低频在主体段绽放"的特征；按拼接处 RMS 对齐后再乘尾部增益并交叉淡化 12 ms。
4. 瞬态塑形：35 ms 之后的主体轻微下沉 10%，主峰软化 30%，让重音更突出。
5. 峰值归一到 0.6025，与 AKM 参考一致；5 ms/8 ms 收尾淡化。

输出：0.150 s、单声道 44.1 kHz、峰值 0.6025、RMS 0.1778、crest 10.6 dB。

## 加工后的实测

| 指标 | 加工前 | 加工后 | AKM 参考 |
| --- | --- | --- | --- |
| 有声段连续 | 27 ms 硬静音 | **最长低电平 0.5 ms** | 0.25 ms |
| 与 AKM 的频段占比最大偏差 | 20.0 pp | **7.9 pp**（多数 ≤3 pp） | — |
| 40–315 Hz 占比 | 18.9% | 53.4% | 59.9% |
| 630–5000 Hz 占比 | 55.0% | 22.5% | 16.7% |
| −6 dB 时点 | 30 ms | 50 ms | 30 ms |
| 峰值时点 | 10 ms | 10 ms | 20 ms |
| crest | 10.6 dB | 10.6 dB | 15.5 dB |

## 工具

- `analyze_tone.py`：与 AKM 的频段占比/电平对比（诊断与验收用）。
- `analyze_timing.py`：按 attack(0–15 ms) / body(15 ms+) 切片看频谱如何随时间变化。
- `sweep_tail.py`：尾音衰减时间常数的参数扫描（连续性那一轮）。
- `sweep_tone.py`：EQ 强度 × 尾部增益 × 尾部长度扫描，按"朝参考走一半"的目标评分（质感那一轮）。
- `import_audio.py`：UE 内导入并保存为 `/Game/Weapons/PKMLowpoly20260922/Audio/S_PKM_Fire`。
- `stop_pie.py`：仅那一次停 PIE 用（该引擎构建没有 `UnrealEditorSubsystem.editor_request_end_play`）。

## 未处理 / 已知边界

- **没有试听，也没有实机验收**（用户规则：默认不主动测试）。频段占比、包络与电平都是离线实测，
  主观质感与响度仍由用户判断。
- 源为单声道 44.1 kHz，按引擎默认重采样；未做立体声化。AKM 参考是双声道，因此 PKM 没有它的
  那点立体声宽度——如果需要，可以在尾音段加轻微扩散，但这会偏离"只用原录音"的原则。
- crest 仍低于 AKM 参考（10.6 对 15.5 dB）：PKM 原始爆音本身持续时间短而能量密度高，
  这是它的性格；若要更接近参考的尖峰感，需要压缩/瞬态设计，当前未做。
